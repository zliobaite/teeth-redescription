import wx
### from wx import ALIGN_BOTTOM, ALIGN_CENTER, ALIGN_CENTER_HORIZONTAL, ALIGN_LEFT, ALIGN_RIGHT, ALL, BOTTOM, C2S_HTML_SYNTAX, CENTER, EXPAND, HORIZONTAL, RIGHT, TOP, VERTICAL, YES_DEFAULT, YES_NO
### from wx import BoxSizer, Button,  CheckBox, Choice, Colour, ColourPickerCtrl, Dialog, GridSizer, MessageDialog, NewId, Notebook, Panel, StaticLine, StaticText, TextCtrl
### from wx import EVT_BUTTON, EVT_CHECKBOX, EVT_CHOICE, EVT_NOTEBOOK_PAGE_CHANGED, EVT_NOTEBOOK_PAGE_CHANGING, EVT_TEXT
### from wx import ID_ANY, ID_CANCEL, ID_NO

import pdb

### USAGE this class provides a wx Modal dialog to modify a dictionary of preferences managed with the PreferenceManager
## It is launched with the following command:
##    # def OnPreferencesDialog(self, event):
##    #     d = PreferencesDialog(main_frame, pref_handle)
##    #     d.ShowModal()
##    #     d.Destroy()
## where pref_handle provide access to the preference manager and a way to update the preference dictionary
## via the following three methods:
## pref_handle.updatePreferencesDict(vdict)
## pref_handle.getPreferences()
## pref_handle.getPreferencesManager()


class PreferencesDialog(wx.Dialog):
	"""
	Creates a preferences dialog to change the settings
	"""

	button_types = [{"name":"cancel", "label":"Cancel", "funct": "self.onCancel"},
			 {"name":"reset", "label":"Reset", "funct": "self.onReset"},
			 {"name":"rtod", "label":"ResetToDefaults", "funct": "self.onResetToDefaults"},
			 {"name":"apply", "label":"Apply", "funct": "self.onApply"},
			 {"name":"ok", "label":"OK", "funct": "self.onOK"}]
	 
	def __init__(self, parent, pref_handle):
		"""
		Initialize the config dialog
		"""
		wx.Dialog.__init__(self, parent, wx.ID_ANY, 'Preferences') #, size=(550, 300))
		self.nb = wx.Notebook(self, wx.ID_ANY)

		self.pref_handle = pref_handle
		self.controls_map = {}
		self.objects_map = {}
		self.tabs = []

		self.cancel_change = False # Tracks if we should cancel a page change
		
		for section in self.pref_handle.getPreferencesManager().subsections:
			if section.get("name") in ["Network", "Split"]:
				continue
			sec_id = wx.NewId()
			self.tabs.append(sec_id)
			self.controls_map[sec_id] = {"button": {}, "range": {},
						     "open": {}, "single_options": {}, "multiple_options": {}, "color_pick": {}}

			conf = wx.Panel(self.nb, -1)
			top_sizer = wx.BoxSizer(wx.VERTICAL)
			self.dispGUI(section, sec_id, conf, top_sizer)
			self.makeButtons(sec_id, conf, top_sizer)
			conf.SetSizer(top_sizer)
			top_sizer.Fit(conf)

			self.setSecValuesFromDict(sec_id, self.pref_handle.getPreferences())
			self.controls_map[sec_id]["button"]["reset"].Disable()
			self.controls_map[sec_id]["button"]["apply"].Disable()
			
			for txtctrl in self.controls_map[sec_id]["open"].itervalues():
				self.Bind(wx.EVT_TEXT, self.changeHappened, txtctrl)
			for txtctrl in self.controls_map[sec_id]["range"].itervalues():
				self.Bind(wx.EVT_TEXT, self.changeHappened, txtctrl)
			for choix in self.controls_map[sec_id]["single_options"].itervalues():
				self.Bind(wx.EVT_CHOICE, self.changeHappened, choix)
			for chkset in self.controls_map[sec_id]["multiple_options"].itervalues():
				for chkbox in chkset.itervalues():
					self.Bind(wx.EVT_CHECKBOX, self.changeHappened, chkbox)

			self.nb.AddPage(conf, section.get("name"))
		self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.onPageChanging)
		self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onPageChanged)
		
		self.Centre()
		self.SetSize((700, 700))

	
	def dispGUI(self, parameters, sec_id, frame, top_sizer):

		for ty in ["open", "range"]:
		########## ADD TEXT PARAMETERS
                    if len(parameters[ty]) > 0: 
			text_sizer = wx.GridSizer(rows=len(parameters[ty]), cols=2, hgap=5, vgap=5)
			for item_id in parameters[ty]:

				item = self.pref_handle.getPreferencesManager().getItem(item_id)
				ctrl_id = wx.NewId()
				label = wx.StaticText(frame, wx.ID_ANY, item.getLabel()+":")
				self.controls_map[sec_id][ty][item_id] = wx.TextCtrl(frame, ctrl_id, "")
				self.objects_map[ctrl_id]= (sec_id, ty, item_id)
				text_sizer.Add(label, 0, wx.ALIGN_RIGHT)
				text_sizer.Add(self.controls_map[sec_id][ty][item_id], 0, wx.EXPAND)

			top_sizer.Add(text_sizer, 0, wx.EXPAND|wx.ALL, 5)

		########## ADD SINGLE OPTIONS PARAMETERS
		#so_sizer = wx.BoxSizer(wx.HORIZONTAL)
                if len(parameters["single_options"]) > 0: 
                    so_sizer = wx.GridSizer(rows=len(parameters["single_options"]), cols=2, hgap=5, vgap=5)
                    for item_id in parameters["single_options"]:

			item = self.pref_handle.getPreferencesManager().getItem(item_id)
			ctrl_id = wx.NewId()
			label = wx.StaticText(frame, wx.ID_ANY, item.getLabel()+":")
			self.controls_map[sec_id]["single_options"][item_id] = wx.Choice(frame, ctrl_id)
			self.controls_map[sec_id]["single_options"][item_id].AppendItems(strings=item.getOptionsText())
			self.objects_map[ctrl_id]= (sec_id, "single_options", item_id)
			so_sizer.Add(label, 0, wx.ALIGN_RIGHT)
			so_sizer.Add(self.controls_map[sec_id]["single_options"][item_id], 0)

                    top_sizer.Add(so_sizer, 0,  wx.EXPAND|wx.ALL, 5)

		########## ADD MULTIPLE OPTIONS PARAMETERS
                if len(parameters["multiple_options"]) > 0: 
                    mo_sizer = wx.GridSizer(rows=len(parameters["multiple_options"]), cols=2, hgap=5, vgap=5)
                    for item_id in parameters["multiple_options"]:
			item = self.pref_handle.getPreferencesManager().getItem(item_id)
			
			#mo_sizer_t = wx.BoxSizer(wx.HORIZONTAL)
			label = wx.StaticText(frame, wx.ID_ANY, item.getLabel()+":")
			#mo_sizer_t.Add(label, 0, wx.ALIGN_LEFT)
			mo_sizer.Add(label, 0, wx.ALIGN_RIGHT)
			mo_sizer_v = wx.BoxSizer(wx.HORIZONTAL)
			self.controls_map[sec_id]["multiple_options"][item_id] = {}
			for option_key, option_label in enumerate(item.getOptionsText()):
				ctrl_id = wx.NewId()
				self.controls_map[sec_id]["multiple_options"][item_id][option_key] = wx.CheckBox(frame, ctrl_id, option_label, style=wx.ALIGN_RIGHT)
				self.objects_map[ctrl_id]= (sec_id, "multiple_options", item_id, option_key)
				mo_sizer_v.Add(self.controls_map[sec_id]["multiple_options"][item_id][option_key], 0)

			# top_sizer.Add(mo_sizer_t, 0, wx.EXPAND|wx.ALL, 5)
			# top_sizer.Add(mo_sizer_v, 0, wx.EXPAND|wx.ALL, 5)
			mo_sizer.Add(mo_sizer_v, 0, wx.EXPAND)
                    top_sizer.Add(mo_sizer, 0, wx.EXPAND|wx.ALL, 5)

		########## ADD COLOR PICK PARAMETERS
                if len(parameters["color_pick"]) > 0: 
                    mo_sizer = wx.GridSizer(rows=len(parameters["color_pick"]), cols=2, hgap=5, vgap=5)
                    for item_id in parameters["color_pick"]:
			item = self.pref_handle.getPreferencesManager().getItem(item_id)

			ctrl_id = wx.NewId()
			label = wx.StaticText(frame, wx.ID_ANY, item.getLabel()+":")
			mo_sizer.Add(label, 0, wx.ALIGN_RIGHT)
			self.controls_map[sec_id]["color_pick"][item_id] = wx.ColourPickerCtrl(frame, ctrl_id, style=wx.ALIGN_RIGHT)
			self.objects_map[ctrl_id]= (sec_id, "color_pick", item_id)
			mo_sizer.Add(self.controls_map[sec_id]["color_pick"][item_id], 0)

                    top_sizer.Add(mo_sizer, 0, wx.EXPAND|wx.ALL, 5)


		for i,k in enumerate(parameters["subsections"]):

			########## ADD SECTION TITLE
			title_sizer = wx.BoxSizer(wx.HORIZONTAL)
			if i > 0:
				top_sizer.Add(wx.StaticLine(frame), 0, wx.EXPAND|wx.ALL, 5)
			title = wx.StaticText(frame, wx.ID_ANY, "--- %s ---" % k.get("name", ""))
			title_sizer.Add(title, 0, wx.ALIGN_CENTER)

			top_sizer.Add(title_sizer, 0, wx.CENTER)

			sec_sizer= wx.BoxSizer(wx.VERTICAL)
			self.dispGUI(k, sec_id, frame, sec_sizer)
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

	def onPageChanging(self, event):
		sec_id = self.tabs[event.GetOldSelection()]
		if self.controls_map[sec_id]["button"]["apply"].IsEnabled():
			### TODO:: FOR NOW SIMPLY APPLY WITHOUT ASKING FOR CONFIRMATION
			# save_dlg = wx.MessageDialog(self.toolFrame, 'Do you want to apply changes before changing tab, otherwise they will be lost?', caption="Warning!", style=wx.YES_NO|wx.YES_DEFAULT)
			# if save_dlg.ShowModal() != wx.ID_NO:
			# 	return
			# save_dlg.Destroy()

			dlg = ApplyResetCancelDialog(parent=self, title='Unapplied changes', msg='Do you want to apply all changes or reset the values before proceeding?');
			res = dlg.ShowModal()
			dlg.Destroy()
			if res == 1:
				self._apply(sec_id)
			elif res == 2:
				self._reset(sec_id)
			else:
				self.cancel_change = True # This tell onPageChanged to revert
							
			#vdict = self.getSecValuesDict(sec_id)
			#self.pref_handle.updatePreferencesDict(vdict)
			#self.setSecValuesFromDict(sec_id, self.pref_handle.getPreferences())
			#self.controls_map[sec_id]["button"]["reset"].Disable()
			#self.controls_map[sec_id]["button"]["apply"].Disable()

	def onPageChanged(self, event):
		if self.cancel_change:
			self.nb.ChangeSelection(event.GetOldSelection())
		self.cancel_change = False

	def onCancel(self, event):
		self.EndModal(0)

	def onReset(self, event):
		if event.GetId() in self.objects_map.keys():
			sec_id = self.objects_map[event.GetId()][0]
			self._reset(sec_id)
			#self.setSecValuesFromDict(sec_id, self.pref_handle.getPreferences())
			#self.controls_map[sec_id]["button"]["reset"].Disable()
			#self.controls_map[sec_id]["button"]["apply"].Disable()

	def _reset(self, sec_id):
		self.setSecValuesFromDict(sec_id, self.pref_handle.getPreferences())
		self.controls_map[sec_id]["button"]["reset"].Disable()
		self.controls_map[sec_id]["button"]["apply"].Disable()

	def onResetToDefaults(self, event):
		if event.GetId() in self.objects_map.keys():
			sec_id = self.objects_map[event.GetId()][0]
			self.setSecValuesFromDict(sec_id, self.pref_handle.getPreferencesManager().getDefaultTriplets())

	def onApply(self, event):
		if event.GetId() in self.objects_map.keys():
			sec_id = self.objects_map[event.GetId()][0]
			self._apply(sec_id)
			#vdict = self.getSecValuesDict(sec_id)
			#self.pref_handle.updatePreferencesDict(vdict)
			#self.setSecValuesFromDict(sec_id, self.pref_handle.getPreferences())
			#self.controls_map[sec_id]["button"]["reset"].Disable()
			#self.controls_map[sec_id]["button"]["apply"].Disable()

	def _apply(self, sec_id):
		vdict = self.getSecValuesDict(sec_id)
		self.pref_handle.updatePreferencesDict(vdict)
		self.setSecValuesFromDict(sec_id, self.pref_handle.getPreferences())
		self.controls_map[sec_id]["button"]["reset"].Disable()
		self.controls_map[sec_id]["button"]["apply"].Disable()
	
	def onOK(self, event):
		if event.GetId() in self.objects_map.keys():
			sec_id = self.objects_map[event.GetId()][0]
			vdict = self.getSecValuesDict(sec_id)
			self.pref_handle.updatePreferencesDict(vdict)
			self.setSecValuesFromDict(sec_id, self.pref_handle.getPreferences())
			self.controls_map[sec_id]["button"]["reset"].Disable()
			self.controls_map[sec_id]["button"]["apply"].Disable()
		self.onClose()

	def changeHappened(self, event):
		if event.GetId() in self.objects_map.keys():
			sec_id = self.objects_map[event.GetId()][0]
			self.controls_map[sec_id]["button"]["reset"].Enable()
			self.controls_map[sec_id]["button"]["apply"].Enable()
		
	def onClose(self):
		self.EndModal(0)

	def setSecValuesFromDict(self, sec_id, vdict):
		for ty in ["open", "range"]:
			for item_id, ctrl_txt in self.controls_map[sec_id][ty].items():
				ctrl_txt.SetValue(vdict[item_id]["text"])

		for item_id, ctrl_single in self.controls_map[sec_id]["single_options"].items():
			ctrl_single.SetSelection(vdict[item_id]["value"])

		for item_id, ctrl_multiple in self.controls_map[sec_id]["multiple_options"].items():
			for check_id, check_box in ctrl_multiple.items():
				check_box.SetValue(check_id in vdict[item_id]["value"])

		for item_id, colour_txt in self.controls_map[sec_id]["color_pick"].items():
			colour_txt.SetColour(wx.Colour(*vdict[item_id]["value"]))


	def getSecValuesDict(self, sec_id):
		vdict = {}
		for ty in ["open", "range"]:
			for item_id, ctrl_txt in self.controls_map[sec_id][ty].items():
				pit = self.pref_handle.getPreferencesManager().getItem(item_id)
				tmp = pit.getParamTriplet(ctrl_txt.GetValue())
				if tmp is not None:
					vdict[item_id] = tmp
				else:
					vdict[item_id] = pit.getDefaultTriplet()

		for item_id, ctrl_single in self.controls_map[sec_id]["single_options"].items():
				pit = self.pref_handle.getPreferencesManager().getItem(item_id)
				tmp = pit.getParamTriplet(ctrl_single.GetSelection(), True)
				if tmp is not None:
					vdict[item_id] = tmp
				else:
					vdict[item_id] = pit.getDefaultTriplet()

		for item_id, ctrl_multiple in self.controls_map[sec_id]["multiple_options"].items():
			tmp_opts = []
			tmp_ok = True
			pit = self.pref_handle.getPreferencesManager().getItem(item_id)
			for check_id, check_box in ctrl_multiple.items():
				if check_box.GetValue():
					tmp = pit.getParamTriplet(check_id, True)
					if tmp is not None:
						tmp_opts.append(tmp)
					else:
						tmp_ok = False
			if tmp_ok:
				vdict[item_id] = {}
				if len(tmp_opts) > 0:
					for k in tmp_opts[0].keys():
						vdict[item_id][k] = []
						for t in tmp_opts:
							vdict[item_id][k].append(t[k])
				else:
					vdict[item_id] = pit.getEmptyTriplet()
			else:
				vdict[item_id] = pit.getDefaultTriplet()

		for item_id, ctrl_txt in self.controls_map[sec_id]["color_pick"].items():
			pit = self.pref_handle.getPreferencesManager().getItem(item_id)
			tmp = pit.getParamTriplet(ctrl_txt.GetColour().GetAsString(wx.C2S_HTML_SYNTAX))
			if tmp is not None:
				vdict[item_id] = tmp
			else:
				vdict[item_id] = pit.getDefaultTriplet()

		return vdict

class ApplyResetCancelDialog(wx.Dialog):
	"""Shows a dialog with three buttons: Apply, Reset, and Cancel.
	Returns 1 for apply, 2 for reset, and -1 for cancel"""
	def __init__(self, parent, title="", msg=""):
		super(ApplyResetCancelDialog, self).__init__(parent=parent, title=title, size=(300, 150))

		top_sizer = wx.BoxSizer(wx.VERTICAL)

		txt = wx.StaticText(self, label=msg)
		txt.Wrap(180)
		#txt = self.CreateTextSizer(msg)

		btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

		applyBtn = wx.Button(self, id=wx.ID_ANY, label="Apply")
		resetBtn = wx.Button(self, id=wx.ID_ANY, label="Reset")
		cancelBtn = wx.Button(self, id=wx.ID_CANCEL, label="Cancel")

		btn_sizer.Add(cancelBtn, flag=wx.ALIGN_LEFT|wx.RIGHT, border=20)
		btn_sizer.Add(resetBtn, flag=wx.ALIGN_RIGHT)
		btn_sizer.Add(applyBtn, flag=wx.ALIGN_RIGHT)
		
		top_sizer.Add(txt, flag=wx.ALL|wx.ALIGN_CENTER, border=20)
		top_sizer.Add(btn_sizer, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=5)

		self.SetSizer(top_sizer)

		applyBtn.Bind(wx.EVT_BUTTON, self.onApply)
		resetBtn.Bind(wx.EVT_BUTTON, self.onReset)
		cancelBtn.Bind(wx.EVT_BUTTON, self.onCancel)

	def onApply(self, e):
		self.EndModal(1)

	def onReset(self, e):
		self.EndModal(2)

	def onCancel(self, e):
		self.EndModal(-1)
		
