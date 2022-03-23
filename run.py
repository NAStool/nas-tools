import os
import log
from config import get_config
from utils.check_config import check_simple_config, check_config
from version import APP_VERSION
from web import run as web
from monitor import run as monitor
from scheduler import run as scheduler
from multiprocessing import Process


if __name__ == "__main__":
    # 参数
    os.environ['TZ'] = 'Asia/Shanghai'
    print("【RUN】配置文件地址：%s" % os.environ.get('NASTOOL_CONFIG'))
    print('【RUN】NASTool 当前版本号：%s' % APP_VERSION)
    # 检查配置文件
    cfg = get_config()
    simple_mode = cfg.get('app', {}).get('simple_mode')
    if simple_mode:
        # 纯硬链接模式
        print("【RUN】当前运行模式：精简模式，无RSS、WEBUI等功能")
        # 检查硬链接配置
        if not check_simple_config(cfg):
            quit()
    else:
        print("【RUN】当前运行模式：全功能模式")
        # 检查正常模式配置文件完整性
        if not check_config(cfg):
            quit()
    # 启动进程
    log.info("【RUN】开始启动进程...")
    Process(target=monitor.run_monitor, args=()).start()
    Process(target=scheduler.run_scheduler, args=()).start()
    Process(target=web.run_web, args=()).start()
