import os
import signal
import sys
import threading
import warnings

import wx

import log
from config import Config
from pt.brushtask import BrushTask
from service.run import run_monitor, stop_monitor
from service.run import run_scheduler, stop_scheduler
from utils.check_config import check_config
from utils.functions import get_system, check_process
from utils.types import OsType
from version import APP_VERSION
from web.app import FlaskApp
from windows.trayicon import myFrame

warnings.filterwarnings('ignore')

# 初始化环境变量
is_windows_exe = getattr(sys, 'frozen', False) and (os.name == "nt")
if is_windows_exe:
    os.environ["NASTOOL_CONFIG"] = os.path.join(os.path.dirname(sys.executable), "config", "config.yaml")
    os.environ["NASTOOL_LOG"] = os.path.join(os.path.dirname(sys.executable), "config", "logs")


def sigal_handler(num, stack):
    if get_system() == OsType.LINUX and check_process("supervisord"):
        print(str(stack))
        log.warn('捕捉到退出信号：%s，开始退出...' % num)
        # 停止定时服务
        stop_scheduler()
        # 停止监控
        stop_monitor()
        # 退出主进程
        sys.exit()


if __name__ == "__main__":

    # 参数
    os.environ['TZ'] = 'Asia/Shanghai'
    log.console("配置文件地址：%s" % os.environ.get('NASTOOL_CONFIG'))
    log.console('NASTool 当前版本号：%s' % APP_VERSION)

    # 检查配置文件
    config = Config()
    if is_windows_exe:
        config.get_config('app')['logpath'] = os.environ.get('NASTOOL_LOG')
    if not check_config(config):
        sys.exit()

    # 启动进程
    log.console("开始启动进程...")

    # 退出事件
    signal.signal(signal.SIGINT, sigal_handler)
    signal.signal(signal.SIGTERM, sigal_handler)

    # 启动定时服务
    run_scheduler()

    # 启动监控服务
    run_monitor()

    # 启动刷流服务
    BrushTask()

    # 启动托盘
    if is_windows_exe:
        def tray_icon():
            homepage_port = config.get_config('app').get('web_port')
            log_path = os.environ.get("NASTOOL_LOG")
            app = wx.App()
            frame = myFrame(homepage_port, log_path)
            frame.Hide()
            app.MainLoop()


        p1 = threading.Thread(target=tray_icon, daemon=True)
        p1.start()

    # 启动主WEB服务
    FlaskApp().run_service()
