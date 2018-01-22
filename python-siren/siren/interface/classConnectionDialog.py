import wx
### from wx import ALIGN_BOTTOM, ALIGN_CENTER_HORIZONTAL, ALL, EXPAND, HORIZONTAL, VERTICAL
### from wx import EVT_BUTTON, EVT_CHECKBOX, EVT_CHOICE, EVT_CLOSE, EVT_TEXT, ID_ANY
### from wx import BoxSizer, Button, NewId, Panel, StaticText
import pdb
from classPreferencesDialog import PreferencesDialog, ApplyResetCancelDialog

### USAGE this class provides a wx Modal dialog to modify a dictionary of preferences managed with the PreferenceManager
## It is launched with the following command:
##    # def OnConnectionDialog(self, event):
##    #     d = ConnectionDialog(main_frame, pref_handle)
##    #     d.ShowModal()
##    #     d.Destroy()


class ConnectionDialog(PreferencesDialog):
	"""
	Creates a preferences dialog to setup a worker connection
	"""
	SUCCESS_FC = "DARKGREEN"
	FAIL_FC = "RED"

	button_types = [{"name":"test", "label":"Check", "funct": "self.onTest"},
			{"name":"cancel", "label":"Cancel", "funct": "self.onCancel"},
			 {"name":"reset", "label":"ResetToCurrent", "funct": "self.onReset"},
			 {"name":"rtod", "label":"ResetToDefaults", "funct": "self.onResetToDefaults"},
			 {"name":"ok", "label":"OK", "funct": "self.onOK"}]

	def __init__(self, parent, pref_handle, wp_handle):
		"""
		Initialize the config dialog
		"""
		wx.Dialog.__init__(self, parent, wx.ID_ANY, 'Worker setup') #, size=(550, 300))
		self.parent = parent
		self.pref_handle = pref_handle
		self.info_box = None
		self.controls_map = {}
		self.objects_map = {}
		self.tabs = []
		self.wp_handle = wp_handle
		self.sec_id = None
		self.no_problem = True
		
		self.cancel_change = False # Tracks if we should cancel a page change

		section_name = "Network"
		ti, section = self.pref_handle.getPreferencesManager().getSectionByName(section_name)
		if ti is not None:
			sec_id = wx.NewId()
			self.tabs.append(sec_id)
			self.controls_map[sec_id] = {"button": {}, "range": {},
						     "open": {}, "single_options": {}, "multiple_options": {}, "color_pick": {}}

			conf = self
			# conf = wx.Panel(self.nb, -1)
			top_sizer = wx.BoxSizer(wx.VERTICAL)
			self.dispGUI(section, sec_id, conf, top_sizer)
			self.dispInfo(conf, top_sizer)
			self.makeButtons(sec_id, conf, top_sizer)
			conf.SetSizer(top_sizer)
			top_sizer.Fit(conf)

			self.setSecValuesFromDict(sec_id, self.pref_handle.getPreferences())
			msg, color = self.receiveInfo(self.wp_handle.getWP().getDetailedInfos())
			self.updateInfo(self.wp_handle.getWP().infoStr()+msg, color)
			self.controls_map[sec_id]["button"]["reset"].Disable()
			
			for txtctrl in self.controls_map[sec_id]["open"].itervalues():
				self.Bind(wx.EVT_TEXT, self.changeHappened, txtctrl)
			for txtctrl in self.controls_map[sec_id]["range"].itervalues():
				self.Bind(wx.EVT_TEXT, self.changeHappened, txtctrl)
			for choix in self.controls_map[sec_id]["single_options"].itervalues():
				self.Bind(wx.EVT_CHOICE, self.changeHappened, choix)
			for chkset in self.controls_map[sec_id]["multiple_options"].itervalues():
				for chkbox in chkset.itervalues():
					self.Bind(wx.EVT_CHECKBOX, self.changeHappened, chkbox)
			self.sec_id = sec_id
		self.Centre()
		self.SetSize((700, -1))
		self.Bind(wx.EVT_CLOSE, self.onClose)

	def dispInfo(self, frame, top_sizer):

		sec_sizer= wx.BoxSizer(wx.VERTICAL)

		########## ADD INFO BOX
		text_sizer = wx.BoxSizer(wx.HORIZONTAL)

		ctrl_id = wx.NewId()
		self.info_box = wx.StaticText(frame, wx.NewId(), "")
		self.box_color = self.info_box.GetForegroundColour()
		text_sizer.Add(self.info_box, 0, wx.EXPAND|wx.ALL, 5)
		sec_sizer.Add(text_sizer, 0, wx.EXPAND|wx.ALL, 5)
		top_sizer.Add(sec_sizer, 0,  wx.EXPAND|wx.ALL, 5)


	def makeButtons(self, sec_id, frame, top_sizer):
		btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

		for button in self.button_types:
			btnId = wx.NewId()
			btn = wx.Button(frame, btnId, button["label"])
			frame.Bind(wx.EVT_BUTTON, eval(button["funct"]), btn)
			btn_sizer.Add(btn, 0)
			self.controls_map[sec_id]["button"][button["name"]] = btn
			self.objects_map[btnId] = (sec_id, "button", button["name"])

		top_sizer.Add(btn_sizer, 0, wx.ALIGN_BOTTOM|wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)

	def updateInfo(self, text, color=None):
		if color is None:
			color = self.box_color
		self.info_box.SetForegroundColour(color)
		self.info_box.SetLabel(text)


	def onTest(self, e):
		# self.controls_map[self.sec_id]["open"]['workserver_authkey'].SetValue("sesame")
		# self.controls_map[self.sec_id]["open"]['workserver_ip'].SetValue("127.0.0.1")
		(ip, portnum, authkey) = self.getIPK()
		if (ip, portnum, authkey) !=  self.wp_handle.getWP().getParameters():
			self.controls_map[self.sec_id]["button"]["reset"].Enable()
		tmpwp = self.wp_handle.setupWorkPlant(ip, portnum, authkey)
		try:
			msg, color = self.receiveInfo(tmpwp.getDetailedInfos())
			self.updateInfo(tmpwp.infoStr()+msg, color)
		except Exception as e:	
			self.no_problem = False
			self.updateInfo("Failed, check the parameters and try again (%s)" % e, ConnectionDialog.FAIL_FC)
		

	def _apply(self, sec_id):
		(ip, portnum, authkey) = self.getIPK()
		if (ip, portnum, authkey) !=  self.wp_handle.getWP().getParameters():
			self.controls_map[self.sec_id]["button"]["reset"].Enable()
			if self.wp_handle.getWP().nbWorkers() > 0:
				dlg = ApplyResetCancelDialog(parent=self, title='Stop Workers', msg='Applying changes requires stopping active workers!');
				res = dlg.ShowModal()
				dlg.Destroy()
			else:
				res = 1
		else:
			res = 3
				
		if res == 1:
			self.setupWP(ip, portnum, authkey)
		elif res == 2:
			self.fillCurrent()
		else:
			self.cancel_change = True # This tell onPageChanged to revert

	def receiveInfo(self, info):
		msg = ""
		parts = info.strip().split('\t')
		if len(parts) > 0 and parts[0]== "OK":
			color = ConnectionDialog.SUCCESS_FC
			if len(parts) > 1:
				msg = ", " + parts[-1] + "."
			self.no_problem = True
		else:
			self.no_problem = False
			color = ConnectionDialog.FAIL_FC
		return msg, color

	def setupWP(self, ip, portnum, authkey):
		try:
			if self.wp_handle.getWP().nbWorkers() > 0:
				print "Closing down"
				self.wp_handle.getWP().closeDown(self.parent)
			self.wp_handle.setWP(self.wp_handle.setupWorkPlant(ip, portnum, authkey))
			msg, color = self.receiveInfo(self.wp_handle.getWP().getDetailedInfos())
			self.updateInfo(self.wp_handle.getWP().infoStr()+msg, color)
		except ValueError as e: #Exception as e:	
			self.no_problem = False
			self.updateInfo("Failed, check the parameters and try again\n(%s)" % e, ConnectionDialog.FAIL_FC)

	def fillCurrent(self):
		for (k,v) in self.wp_handle.getWP().getParametersD().items():
			self.controls_map[self.sec_id]["open"][k].SetValue(str(v))
		self.controls_map[self.sec_id]["button"]["reset"].Disable()
		self._apply(self.sec_id)

	def changeHappened(self, event):
		pass

	def getIPK(self):
		vdict = self.getSecValuesDict(self.sec_id)
		self.pref_handle.updatePreferencesDict(vdict)
		return (self.pref_handle.getPreference("workserver_ip"), self.pref_handle.getPreference("workserver_port"), self.pref_handle.getPreference("workserver_authkey"))

	def onOK(self, event):
		self.onApply(event)
		if self.no_problem:
			self.EndModal(0)

	def onClose(self, event=None):
		self.fillCurrent()
		self.EndModal(0)
			
	def onReset(self, event):
		self.fillCurrent()
