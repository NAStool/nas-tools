import os
from time import sleep

import log
import settings
from functions import system_exec_command
from web import run as webhook
from monitor import run as monitor
from scheduler import run as scheduler
from multiprocessing import Process

logger = log.Logger("scheduler").logger

if __name__ == "__main__":
    # 环境准备
    env_media, env_photo, env_pt, env_resiliosync = False, False, False, False
    automount_flag = settings.get("automount.automount_flag") == "ON" or False
    while True:
        if automount_flag:
            logger.info("开始装载目录...")
            # media
            media_config = settings.get("automount.media")
            if media_config and not env_media:
                media_config = media_config.split(";")
                if not os.path.exists(media_config[1]):
                    os.makedirs(media_config[1])
                media_cmd = "mount.cifs -o username=" + media_config[2] + ",password=\"" + media_config[3] + \
                            "\",uid=0,gid=0,iocharset=utf8 " + media_config[0] + " " + media_config[1]
                logger.info("开始执行命令：" + media_cmd)
                result_err, result_out = system_exec_command(media_cmd, 10)
                if result_err:
                    logger.error("错误信息：" + result_err)
                else:
                    env_media = True
                if result_out:
                    logger.info("执行结果：" + result_out)
            else:
                env_media = True
            # photo
            photo_config = settings.get("automount.photo")
            if photo_config and not env_photo:
                photo_config = photo_config.split(";")
                if not os.path.exists(photo_config[1]):
                    os.makedirs(photo_config[1])
                photo_cmd = "mount.cifs -o username=" + photo_config[2] + ",password=\"" + photo_config[3] + \
                            "\",uid=0,gid=0,iocharset=utf8 " + photo_config[0] + " " + photo_config[1]
                logger.info("开始执行命令：" + photo_cmd)
                result_err, result_out = system_exec_command(photo_cmd, 10)
                if result_err:
                    logger.error("错误信息：" + result_err)
                else:
                    env_photo = True
                if result_out:
                    logger.info("执行结果：" + result_out)
            else:
                env_photo = True
            # pt
            pt_config = settings.get("automount.pt")
            if pt_config and not env_pt:
                pt_config = pt_config.split(";")
                if not os.path.exists(pt_config[1]):
                    os.makedirs(pt_config[1])
                pt_cmd = "mount.cifs -o username=" + pt_config[2] + ",password=\"" + pt_config[3] + \
                         "\",uid=0,gid=0,iocharset=utf8 " + pt_config[0] + " " + pt_config[1]
                logger.info("开始执行命令：" + pt_cmd)
                result_err, result_out = system_exec_command(pt_cmd, 10)
                if result_err:
                    logger.error("错误信息：" + result_err)
                else:
                    env_pt = True
                if result_out:
                    logger.info("执行结果：" + result_out)
            else:
                env_pt = True
            # relisiosync
            relisiosync_config = settings.get("automount.relisiosync")
            if relisiosync_config and not env_resiliosync:
                relisiosync_config = relisiosync_config.split(";")
                if not os.path.exists(relisiosync_config[1]):
                    os.makedirs(relisiosync_config[1])
                relisiosync_cmd = "mount.cifs -o username=" + relisiosync_config[2] + ",password=\"" + \
                                  relisiosync_config[3] + "\",uid=0,gid=0,iocharset=utf8 " + \
                                  relisiosync_config[0] + " " + relisiosync_config[1]
                logger.info("开始执行命令：" + relisiosync_cmd)
                result_err, result_out = system_exec_command(relisiosync_cmd, 10)
                if result_err:
                    logger.error("错误信息：" + result_err)
                else:
                    env_resiliosync = True
                if result_out:
                    logger.info("执行结果：" + result_out)
            else:
                env_resiliosync = True
            logger.info("目录装载完成！")
        else:
            env_media, env_photo, env_pt, env_resiliosync = True, True, True, True
        # 启动进程
        if env_media and env_photo and env_pt and env_resiliosync:
            logger.info("开始启动进程...")
            Process(target=monitor.run_monitor, args=()).start()
            Process(target=scheduler.run_scheduler, args=()).start()
            Process(target=webhook.run_webhook, args=()).start()
            logger.info("进程启动完成！")
            break
        else:
            logger.error("环境未就绪，等待1分钟后重试...")
            sleep(60)
