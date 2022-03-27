import os
import threading
import log
from config import Config
from monitor.run import run_monitor
from scheduler.run import run_scheduler
from utils.check_config import check_config
from version import APP_VERSION
from web.app import FlaskApp

if __name__ == "__main__":
    # 参数
    os.environ['TZ'] = 'Asia/Shanghai'
    print("配置文件地址：%s" % os.environ.get('NASTOOL_CONFIG'))
    print('NASTool 当前版本号：%s' % APP_VERSION)
    # 检查配置文件
    cfg = Config()
    if not check_config(cfg):
        quit()
    # 启动进程
    log.info("开始启动进程...")

    # 启动定时服务
    scheduler = threading.Thread(target=run_scheduler)
    scheduler.setDaemon(False)
    scheduler.start()

    # 启动监控服务
    monitor = threading.Thread(target=run_monitor)
    monitor.setDaemon(False)
    monitor.start()

    # 启动主WEB服务
    FlaskApp().run_service()
