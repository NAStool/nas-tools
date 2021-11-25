import argparse
import os
from time import sleep
import log
import settings
from functions import system_exec_command
from message.send import sendmsg
from web import run as webhook
from monitor import run as monitor
from scheduler import run as scheduler
from multiprocessing import Process


if __name__ == "__main__":
    # 参数
    parser = argparse.ArgumentParser(description='Nas Media Library Management Tool')
    parser.add_argument('-c', '--config', dest='config_file', default='config/config.ini',
                        help='Config File Path (default: config/config.ini)')

    args = parser.parse_args()
    os.environ['NASTOOL_CONFIG'] = args.config_file
    log.info("【RUN】配置文件地址：" + os.environ['NASTOOL_CONFIG'])
    if not os.path.exists(os.environ['NASTOOL_CONFIG']):
        log.error("【RUN】配置文件不存在！")
        quit()
    # 环境准备
    envloop = 0
    automount_flag = settings.get("automount.automount_flag") == "ON" or False
    if automount_flag:
        env_media, env_photo, env_pt, env_resiliosync = False, False, False, False
        while True:
            log.info("【RUN】开始装载目录...")
            # media
            media_config = settings.get("automount.media")
            if not media_config:
                env_media = True
            elif not env_media:
                media_config = media_config.split(";")
                if not os.path.exists(media_config[1]):
                    os.makedirs(media_config[1])
                media_cmd = "mount.cifs -o username=" + media_config[2] + ",password=\"" + media_config[3] + \
                            "\",uid=0,gid=0,iocharset=utf8 " + media_config[0] + " " + media_config[1]
                log.info("【RUN】开始执行命令：" + media_cmd)
                result_err, result_out = system_exec_command(media_cmd, 10)
                if result_err:
                    log.error("【RUN】错误信息：" + result_err)
                if result_out:
                    log.info("【RUN】执行结果：" + result_out)
                if not result_err and not result_out:
                    env_media = True
            # photo
            photo_config = settings.get("automount.photo")
            if not photo_config:
                env_photo = True
            elif not env_photo:
                photo_config = photo_config.split(";")
                if not os.path.exists(photo_config[1]):
                    os.makedirs(photo_config[1])
                photo_cmd = "mount.cifs -o username=" + photo_config[2] + ",password=\"" + photo_config[3] + \
                            "\",uid=0,gid=0,iocharset=utf8 " + photo_config[0] + " " + photo_config[1]
                log.info("【RUN】开始执行命令：" + photo_cmd)
                result_err, result_out = system_exec_command(photo_cmd, 10)
                if result_err:
                    log.error("【RUN】错误信息：" + result_err)
                if result_out:
                    log.info("【RUN】执行结果：" + result_out)
                if not result_err and not result_out:
                    env_photo = True
            # pt
            pt_config = settings.get("automount.pt")
            if not pt_config:
                env_pt = True
            elif not env_pt:
                pt_config = pt_config.split(";")
                if not os.path.exists(pt_config[1]):
                    os.makedirs(pt_config[1])
                pt_cmd = "mount.cifs -o username=" + pt_config[2] + ",password=\"" + pt_config[3] + \
                         "\",uid=0,gid=0,iocharset=utf8 " + pt_config[0] + " " + pt_config[1]
                log.info("【RUN】开始执行命令：" + pt_cmd)
                result_err, result_out = system_exec_command(pt_cmd, 10)
                if result_err:
                    log.error("【RUN】错误信息：" + result_err)
                if result_out:
                    log.info("【RUN】执行结果：" + result_out)
                if not result_err and not result_out:
                    env_pt = True
            # relisiosync
            relisiosync_config = settings.get("automount.relisiosync")
            if not relisiosync_config:
                env_resiliosync = True
            elif not env_resiliosync:
                relisiosync_config = relisiosync_config.split(";")
                if not os.path.exists(relisiosync_config[1]):
                    os.makedirs(relisiosync_config[1])
                relisiosync_cmd = "mount.cifs -o username=" + relisiosync_config[2] + ",password=\"" + \
                                  relisiosync_config[3] + "\",uid=0,gid=0,iocharset=utf8 " + \
                                  relisiosync_config[0] + " " + relisiosync_config[1]
                log.info("【RUN】开始执行命令：" + relisiosync_cmd)
                result_err, result_out = system_exec_command(relisiosync_cmd, 10)
                if result_err:
                    log.error("【RUN】错误信息：" + result_err)
                if result_out:
                    log.info("【RUN】执行结果：" + result_out)
                if not result_err and not result_out:
                    env_resiliosync = True
            # 启动进程
            if env_media and env_photo and env_pt and env_resiliosync:
                log.info("【RUN】目录装载完成！")
                break
            elif envloop > 10:
                log.info("【RUN】已达最大重试次数，跳过...")
                sendmsg("【NASTOOL】NASTOOL启动失败，环境未就绪！")
                break
            else:
                log.error("【RUN】环境未就绪，等待1分钟后重试...")
                envloop = envloop + 1
                sleep(60)
    # 启动进程
    log.info("【RUN】开始启动进程...")
    Process(target=monitor.run_monitor, args=()).start()
    Process(target=scheduler.run_scheduler, args=()).start()
    Process(target=webhook.run_webhook, args=()).start()
