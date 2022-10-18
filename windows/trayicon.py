import os
import sys
import webbrowser

import wx
import wx.adv


class Balloon(wx.adv.TaskBarIcon):
    ICON = os.path.dirname(__file__).replace("windows", "") + "nas-tools.ico"

    def __init__(self, homepage, log_path):
        wx.adv.TaskBarIcon.__init__(self)
        self.SetIcon(wx.Icon(self.ICON))
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarLeftDClick)
        self.homepage = homepage
        self.log_path = log_path

    # Menu数据
    def setMenuItemData(self):
        return ("Log", self.Onlog), ("Close", self.OnClose)

    # 创建菜单
    def CreatePopupMenu(self):
        menu = wx.Menu()
        for itemName, itemHandler in self.setMenuItemData():
            if not itemName:  # itemName为空就添加分隔符
                menu.AppendSeparator()
                continue
            menuItem = wx.MenuItem(None, wx.ID_ANY, text=itemName, kind=wx.ITEM_NORMAL)  # 创建菜单项
            menu.Append(menuItem)  # 将菜单项添加到菜单
            self.Bind(wx.EVT_MENU, itemHandler, menuItem)
        return menu

    def OnTaskBarLeftDClick(self, event):
        webbrowser.open(self.homepage)

    def Onlog(self, event):
        os.startfile(self.log_path)

    @staticmethod
    def OnClose(event):
        exe_name = os.path.basename(sys.executable)
        os.system('taskkill /F /IM ' + exe_name)


class trayicon(wx.Frame):
    def __init__(self, homepage, log_path):
        app = wx.App()
        wx.Frame.__init__(self, None)
        self.taskBarIcon = Balloon(homepage, log_path)
        webbrowser.open(homepage)
        self.Hide()
        app.MainLoop()
