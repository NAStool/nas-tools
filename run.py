import os
import re
from subprocess import call

import requests
from requests import RequestException

import log
from config import get_config, check_config, check_simple_config
from version import APP_VERSION
from web import run as web
from monitor import run as monitor
from scheduler import run as scheduler
from multiprocessing import Process


if __name__ == "__main__":
    # 参数
    os.environ['TZ'] = 'Asia/Shanghai'
    print("【RUN】配置文件地址：%s" % os.environ['NASTOOL_CONFIG'])
    print('【RUN】NASTool 当前版本号：%s' % APP_VERSION)
    # 尝试检查最新版本号
    try:
        rets = requests.get(url='https://github.com/jxxghp/nas-tools/raw/master/version.py', timeout=10).text
        if rets:
            latest_ver = re.search(r"=\s*'([v0-9.]+)'", rets, re.IGNORECASE)
            if latest_ver:
                latest_ver = latest_ver.group(1)
                if latest_ver:
                    old_vernum = int(APP_VERSION.replace("v", "").replace(".", ""))
                    new_vernum = int(latest_ver.replace("v", "").replace(".", ""))
                    if new_vernum > old_vernum:
                        print('【RUN】NASTool 有新的版本 %s，请进行升级！项目地址：https://github.com/jxxghp/nas-tools' % str(latest_ver))
    except RequestException as err:
        print('【RUN】无法访问在线地址获取最新版本号信息')
    # 检查配置文件
    cfg = get_config()
    simple_mode = cfg['app'].get('simple_mode')
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
    Process(target=web.run_web(), args=()).start()
