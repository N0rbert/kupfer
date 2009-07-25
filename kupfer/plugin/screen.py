import os
import gio

from kupfer.objects import Leaf, Action, Source, PicklingHelperMixin
from kupfer import utils

__kupfer_name__ = _("GNU Screen")
__kupfer_sources__ = ("ScreenSessionsSource", )
__description__ = _("Active GNU Screen sessions")
__version__ = ""
__author__ = "Ulrik Sverdrup <ulrik.sverdrup@gmail.com>"


def screen_sessions_infos():
	"""
	Yield tuples of pid, name, time, status
	for running screen sessions
	"""
	pipe = os.popen("screen -list")
	output = pipe.read()
	for line in output.splitlines():
		fields = line.split("\t")
		if len(fields) == 4:
			empty, pidname, time, status = fields
			pid, name = pidname.split(".", 1)
			time = time.strip("()")
			status = status.strip("()")
			yield (pid, name, time, status)

class ScreenSession (Leaf):
	"""Represented object is the session pid as string"""
	def get_actions(self):
		return (AttachScreen(),)

	def get_description(self):
		for pid, name, time, status in screen_sessions_infos():
			if self.object == pid:
				break
		else:
			return "%s (%s)" % (self.name, self.object)
		# Handle localization of status
		status_dict = {
			"Attached": _("Attached"),
			"Detached": _("Detached"),
		}
		status = status_dict.get(status, status)
		return (_("%(status)s session %(name)s (%(pid)s) created %(time)s") %
				{"status": status, "name": name, "pid": pid, "time": time})

	def get_icon_name(self):
		return "gnome-window-manager"

class ScreenSessionsSource (Source, PicklingHelperMixin):
	"""Source for GNU Screen sessions"""
	def __init__(self):
		super(ScreenSessionsSource, self).__init__(_("Screen sessions"))
		self.unpickle_finish()

	def pickle_prepare(self):
		self.monitor = None

	def unpickle_finish(self):
		"""Set up a directory watch on Screen's socket dir"""
		self.screen_dir = (os.getenv("SCREENDIR") or
				"/var/run/screen/S-%s" % os.getlogin())
		gfile = gio.File(self.screen_dir)
		exists = gfile.query_exists()
		if not exists:
			self.screen_dir = None
			self.output_debug("Screen socket dir or SCREENDIR not found")
			return
		self.monitor = gfile.monitor_directory(gio.FILE_MONITOR_NONE, None)
		self.monitor.connect("changed", self._screen_socket_changed)

	def _screen_socket_changed(self, monitor, file1, file2, evt_type):
		# (changed attributes need no update, only new files)
		if evt_type in (gio.FILE_MONITOR_EVENT_CREATED,
				gio.FILE_MONITOR_EVENT_DELETED):
			self.mark_for_update()

	def get_items(self):
		if not self.screen_dir:
			return
		for pid, name, time, status in screen_sessions_infos():
			yield ScreenSession(pid, name)

	def get_description(self):
		return _("Active GNU Screen sessions")
	def get_icon_name(self):
		return "terminal"
	def provides(self):
		yield ScreenSession

class AttachScreen (Action):
	"""
	"""
	def __init__(self):
		name = _("Attach")
		super(AttachScreen, self).__init__(name)
	def activate(self, leaf):
		pid = leaf.object
		action = "screen -x -R %s" % pid
		utils.launch_commandline(action, name=_("GNU Screen"),
			in_terminal=True)
