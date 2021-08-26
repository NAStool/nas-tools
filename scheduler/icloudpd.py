# 定时在QNAP中执行命令同步icloud照片到NAS
from datetime import datetime
import log
import settings
from functions import system_exec_command
from message.send import sendmsg

logger = log.Logger("scheduler").logger


def run_icloudpd():
    start_time = datetime.now()
    cmd = settings.get("scheduler.icloudpd_cmd")

    logger.info("开始执行命令：" + cmd)
    # 获取命令结果
    result_err, result_out = system_exec_command(cmd, 600)
    if result_err:
        logger.error("错误信息：" + result_err)
    if result_out:
        logger.info("执行结果：" + result_out)

    end_time = datetime.now()
    if result_err != "":
        sendmsg("【iCloudPd】命令执行失败！", "错误信息：" + result_err)
    elif result_out.find("All photos have been downloaded!") == -1:
        sendmsg("【iCloudPd】处理失败！", "请输入两步认证授权码")
    else:
        sendmsg("【iCloudPd】照片同步完成",
                "耗时：" + str((end_time - start_time).seconds) + " 秒" +
                "\n\n成功：" + str(result_out.count("Downloading /")) +
                "\n\n已存在：" + str(result_out.count("already exists")))


if __name__ == "__main__":
    run_icloudpd()
