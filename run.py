import argparse
import os
from subprocess import call

import log
from config import get_config, check_config
from functions import get_host_name, get_host_ip
from message.send import sendmsg
from web import run as webhook
from monitor import run as monitor
from scheduler import run as scheduler
from multiprocessing import Process


if __name__ == "__main__":
    # 参数
    parser = argparse.ArgumentParser(description='Nas Media Library Management Tool')
    parser.add_argument('-c', '--config', dest='config_file', default='config/config.yaml',
                        help='Config File Path (default: config/config.yaml)')

    args = parser.parse_args()
    os.environ['TZ'] = 'Asia/Shanghai'
    os.environ['NASTOOL_CONFIG'] = args.config_file
    print("【RUN】配置文件地址：" + os.environ['NASTOOL_CONFIG'])
    if not os.path.exists(os.environ['NASTOOL_CONFIG']):
        call(["cp", os.path.join(os.path.dirname(os.path.realpath(__file__)), "config/config.yaml"), os.environ['NASTOOL_CONFIG']])
        print("【RUN】配置文件不存在，已将配置文件模板复制到配置目录，请修改后重新启动！")
        quit()
    # 检查配置文件
    cfg = get_config()
    if not check_config(cfg):
        quit()
    # 启动进程
    log.info("【RUN】开始启动进程...")
    Process(target=monitor.run_monitor, args=()).start()
    Process(target=scheduler.run_scheduler, args=()).start()
    Process(target=webhook.run_webhook, args=()).start()
    sendmsg("【NASTOOL】" + get_host_name() + "已启动", "IP地址：" + get_host_ip())
