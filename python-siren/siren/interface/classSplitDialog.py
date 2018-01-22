import wx
### from wx import ALIGN_BOTTOM, ALIGN_CENTER, ALIGN_CENTER_HORIZONTAL, ALIGN_RIGHT, ALL, ID_ANY, CENTER, EXPAND, HORIZONTAL, VERTICAL
### from wx import BoxSizer, Button, CheckBox, Choice, Dialog, GridSizer, NewId, Panel, StaticLine, StaticText
### from wx import EVT_BUTTON, EVT_CHECKBOX, EVT_CHOICE, EVT_CLOSE, EVT_TEXT   

import pdb
from classPreferencesDialog import PreferencesDialog

class SplitDialog(PreferencesDialog):
    """
    Creates a preferences dialog to setup a worker connection
    """
    SUCCESS_FC = "DARKGREEN"
    FAIL_FC = "RED"
    DEACTIVATED_LBL = "Deactivated"
    AUTOMATIC_LBL = "Automatic"
    
    button_types = [{"name":"cancel", "label":"Cancel", "funct": "self.onCancel"},
            {"name":"rtod", "label":"ResetToDefaults", "funct": "self.onResetToDefaults"},
            {"name":"prepare", "label":"Prepare", "funct": "self.onPrepare"},
            {"name":"save_col", "label":"SaveToColumn", "funct": "self.onSaveToC"},
            {"name":"apply", "label":"Apply", "funct": "self.onApply"}]

    def __init__(self, parent, pref_handle, tool):
        """
        Initialize the config dialog
        """
        wx.Dialog.__init__(self, parent, wx.ID_ANY, 'Splits setup') #, size=(550, 300))
        self.parent = parent
        self.pref_handle = pref_handle
        self.data_handle = pref_handle
        self.tool = tool
        self.info_box = None
        self.boxes_sizers = {}
        self.controls_map = {}
        self.objects_map = {}
        self.tabs = []

        self.sec_id = None
        self.no_problem = True
        
        self.cancel_change = False # Tracks if we should cancel a page change

        section_name = "Split"
        ti, section = self.pref_handle.getPreferencesManager().getSectionByName(section_name)
        self.splits_info = self.data_handle.getData().getFoldsInfo()
        self.cands_splits = self.data_handle.getData().findCandsFolds()
        self.source_cands = [self.DEACTIVATED_LBL, self.AUTOMATIC_LBL] + \
                    [self.data_handle.getData().cols[side][colid].getName() for (side, colid) in self.cands_splits]
        self.controls_map["add"] = {}

        if ti is not None:
            sec_id = wx.NewId()
            self.tabs.append(sec_id)
            self.controls_map[sec_id] = {"button": {}, "range": {},
                             "open": {}, "single_options": {}, "multiple_options": {}, "color_pick": {}}

            conf = self
            self.sec_id = sec_id
            # conf = wx.Panel(self.nb, -1)
            top_sizer = wx.BoxSizer(wx.VERTICAL)
            self.dispGUI(section, sec_id, conf, top_sizer)
            self.dispInfo(conf, top_sizer)
            self.makeButtons(sec_id, conf, top_sizer)
            self.getSplitsIDS()
            # pdb.set_trace()
            # print self.controls_map["add"]["learn"]
            self.makeAssignBoxes(conf, top_sizer)
            conf.SetSizer(top_sizer)
            top_sizer.Fit(conf)
            self.top_sizer = top_sizer
            self.conf = conf

            self.setSecValuesFromDict(sec_id, self.pref_handle.getPreferences())
            ### DEBUG
            self.controls_map[self.sec_id]["button"]["prepare"].Disable()
            self.controls_map[self.sec_id]["button"]["save_col"].Disable()
            
            for txtctrl in self.controls_map[sec_id]["open"].itervalues():
                self.Bind(wx.EVT_TEXT, self.changeHappened, txtctrl)
            for txtctrl in self.controls_map[sec_id]["range"].itervalues():
                self.Bind(wx.EVT_TEXT, self.changeHappened, txtctrl)
            for choix in self.controls_map[sec_id]["single_options"].itervalues():
                self.Bind(wx.EVT_CHOICE, self.changeHappened, choix)
            for chkset in self.controls_map[sec_id]["multiple_options"].itervalues():
                for chkbox in chkset.itervalues():
                    self.Bind(wx.EVT_CHECKBOX, self.changeHappened, chkbox)
        self.setSelectedSource()
        self.Centre()
        self.SetSize((700, -1))
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def dispInfo(self, frame, top_sizer):
        sec_id = "add"

        ### TITLE
        title_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(wx.StaticLine(frame), 0, wx.EXPAND|wx.ALL, 5)
        title = wx.StaticText(frame, wx.ID_ANY, "--- %s ---" % "Assignments")
        title_sizer.Add(title, 0, wx.ALIGN_CENTER)
        top_sizer.Add(title_sizer, 0, wx.CENTER)

        ### Sources
        so_sizer = wx.GridSizer(rows=1, cols=2, hgap=5, vgap=5)

        ctrl_id = wx.NewId()
        item_id = "source"
        label = wx.StaticText(frame, wx.ID_ANY, "Source:")
        self.controls_map[sec_id][item_id] = wx.Choice(frame, ctrl_id)
        self.controls_map[sec_id][item_id].AppendItems(strings=self.source_cands)
        self.objects_map[ctrl_id]= (sec_id, "single_options", item_id)
        self.Bind(wx.EVT_CHOICE, self.changeSource, self.controls_map[sec_id][item_id])

        so_sizer.Add(label, 0, wx.ALIGN_RIGHT)
        so_sizer.Add(self.controls_map[sec_id][item_id], 0)

        top_sizer.Add(so_sizer, 0,  wx.EXPAND|wx.ALL, 5)

        ### ASSIGNMENTS
        mo_sizer = wx.GridSizer(rows=2, cols=2, hgap=5, vgap=5)
        for (item_id, lbl) in [("learn", "Learn"), ("test", "Test")]:
                        
            label = wx.StaticText(frame, wx.ID_ANY, lbl+":")
            mo_sizer.Add(label, 0, wx.ALIGN_RIGHT)
            self.boxes_sizers[item_id] = wx.BoxSizer(wx.HORIZONTAL)
            self.controls_map[sec_id][item_id] = {}
            mo_sizer.Add(self.boxes_sizers[item_id], 0, wx.EXPAND)
        top_sizer.Add(mo_sizer, 0, wx.EXPAND|wx.ALL, 5)
        
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

    def getSplitsIDS(self):
        if self.splits_info is None:
            self.stored_splits_ids = []
        else:
            self.stored_splits_ids = sorted(self.splits_info["split_ids"].keys(), key=lambda x: self.splits_info["split_ids"][x])

    def onPrepare(self, event):
        self.getDataSplits()
        self.getSplitsIDS()
        self.destroyAssignBoxes(self, self.top_sizer)
        self.makeAssignBoxes(self, self.top_sizer)
        self.controls_map[self.sec_id]["button"]["prepare"].Disable()
        if self.data_handle.getData().hasAutoSplits():
            self.controls_map[self.sec_id]["button"]["save_col"].Enable()
        self.top_sizer.Fit(self.conf)
        self.Centre()
        self.SetSize((700, -1))

    def onApply(self, event):
        source_pos = self.controls_map["add"]["source"].GetCurrentSelection()
        if self.source_cands[source_pos] == self.DEACTIVATED_LBL:
            self.data_handle.getData().dropLT()
        else:
            ids = {}
            for lt in ["learn", "test"]:
                ids[lt] = [self.stored_splits_ids[bid] for bid, box in self.controls_map["add"][lt].items() if box.IsChecked()]
            self.data_handle.getData().assignLT(ids["learn"], ids["test"])
        self.tool.recomputeAll()
        self.EndModal(0)


    def makeAssignBoxes(self, frame, top_sizer, sec_id = "add"):
        splits = self.stored_splits_ids
        checked = [("learn", []), ("test", [])]
        if len(self.data_handle.getData().getLTsids()) > 0:
            ltsids = self.data_handle.getData().getLTsids()
            checked = [(lbl, [self.splits_info["split_ids"][kk] for kk in ltsids[lbl]]) for lbl in ["learn", "test"]]
        elif len(splits) == 1:
            checked = [("learn", [0]), ("test", [0])]
        elif len(splits) > 1:
            checked = [("learn", range(1,len(splits))), ("test", [0])]
        for (item_id, cck) in checked:
            for option_key, option_label in enumerate(splits):
                ctrl_id = wx.NewId()
                self.controls_map[sec_id][item_id][option_key] = wx.CheckBox(frame, ctrl_id, option_label, style=wx.ALIGN_RIGHT)
                self.controls_map[sec_id][item_id][option_key].SetValue(option_key in cck)
                self.objects_map[ctrl_id]= (sec_id, item_id, option_key)
                self.boxes_sizers[item_id].Add(self.controls_map[sec_id][item_id][option_key], 0) 
        if len(splits) > 0:
            self.controls_map[self.sec_id]["button"]["apply"].Enable()
        else:
            self.controls_map[self.sec_id]["button"]["apply"].Disable()

    def destroyAssignBoxes(self, frame, top_sizer, sec_id="add"):
        for item_id in ["test", "learn"]:
            self.boxes_sizers[item_id].Clear()
            keys = self.controls_map[sec_id][item_id].keys()
            for key in keys:
                self.controls_map[sec_id][item_id][key].Destroy()
                del self.controls_map[sec_id][item_id][key]

    def changeHappened(self, event):
        source_pos = self.controls_map["add"]["source"].GetCurrentSelection()
        if self.source_cands[source_pos] == self.AUTOMATIC_LBL:
            self.controls_map[self.sec_id]["button"]["prepare"].Enable()
        # if event.GetId() in self.objects_map.keys():
        #     sec_id = self.objects_map[event.GetId()][0]
        #     self.controls_map[sec_id]["button"]["rtod"].Enable()

    def changeSource(self, event):
        if self.controls_map["add"]["source"].GetSelection() != 0:
            self.controls_map[self.sec_id]["button"]["prepare"].Enable()        
        else:
            self.controls_map[self.sec_id]["button"]["prepare"].Disable()
            
    def onClose(self, event=None):
        self.EndModal(0)
            
    def onCancel(self, event):
        self.EndModal(0)

    def getDataSplits(self):
        source_pos = self.controls_map["add"]["source"].GetCurrentSelection()
        if self.source_cands[source_pos] == self.DEACTIVATED_LBL:
            pass
        elif self.source_cands[source_pos] == self.AUTOMATIC_LBL:
            vdict = self.getSecValuesDict(self.sec_id)
            self.pref_handle.updatePreferencesDict(vdict)
            self.data_handle.getData().getSplit(self.pref_handle.getPreference("nb_folds"),
                                self.pref_handle.getPreference("coo_dim"),
                                self.pref_handle.getPreference("grain"))
        else:
            (side, colid) = self.cands_splits[source_pos-2]
            self.data_handle.getData().extractFolds(side, colid)
        self.splits_info = self.data_handle.getData().getFoldsInfo()
        self.setSelectedSource()
        
    def setSelectedSource(self):
        map_source = dict([(v,k) for (k,v) in enumerate(self.source_cands)])
        if self.splits_info is None:
            source_name = self.DEACTIVATED_LBL
        elif self.splits_info["source"] != "data":
            source_name = self.AUTOMATIC_LBL
        else:
            source_name = self.splits_info["parameters"]["colname"]
        source_pos = map_source.get(source_name, -1)
        self.controls_map["add"]["source"].Select(source_pos)

    def onSaveToC(self, event=None):
        if self.data_handle.getData().hasAutoSplits():
            self.data_handle.getData().addFoldsCol()
            self.controls_map[self.sec_id]["button"]["save_col"].Disable()
            self.tool.reloadVars()
