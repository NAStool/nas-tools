import wx
import wx.adv
import sys
import webbrowser
import os


class Balloon(wx.adv.TaskBarIcon):
    ICON = os.path.dirname(__file__).replace("windows", "") + "nas-tools.ico"

    def __init__(self, homepage_port, log_path):
        wx.adv.TaskBarIcon.__init__(self)
        self.SetIcon(wx.Icon(self.ICON))
        self.homepage_port = homepage_port
        self.log_path = log_path

    # Menu数据
    def setMenuItemData(self):
        return ("Home page", self.Onhomepage), ("Log", self.Onlog), ("Close", self.OnClose)

    # 创建菜单
    def CreatePopupMenu(self):
        menu = wx.Menu()
        for itemName, itemHandler in self.setMenuItemData():
            if not itemName:  # itemName为空就添加分隔符
                menu.AppendSeparator()
                continue
            menuItem = wx.MenuItem(None, wx.ID_ANY, text=itemName, kind=wx.ITEM_NORMAL)  # 创建菜单项
            menu.AppendItem(menuItem)  # 将菜单项添加到菜单
            self.Bind(wx.EVT_MENU, itemHandler, menuItem)
        return menu

    def Onhomepage(self, event):
        webbrowser.open("http://localhost:" + str(self.homepage_port))

    def Onlog(self, event):
        os.startfile(self.log_path)

    def OnClose(self, event):
        exe_name = os.path.basename(sys.executable)
        os.system('taskkill /F /IM ' + exe_name)


class trayicon(wx.Frame):
    def __init__(self, homepage_port, log_path):
        app = wx.App()
        wx.Frame.__init__(self, None)
        self.taskBarIcon = Balloon(homepage_port, log_path)
        self.Hide()
        app.MainLoop()
