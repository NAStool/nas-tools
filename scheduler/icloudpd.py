# 定时在QNAP中执行命令同步icloud照片到NAS
from datetime import datetime
import log
import settings
from functions import system_exec_command
from message.send import sendmsg


def run_icloudpd():
    try:
        icloudpd()
    except Exception as err:
        log.error("【RUN】执行定时任务icloudpd出错：" + str(err))
        sendmsg("【NASTOOL】执行定时任务icloudpd出错！", str(err))


def icloudpd():
    start_time = datetime.now()
    cmd = settings.get("scheduler.icloudpd_cmd")

    log.info("【ICLOUDPD】开始执行命令：" + cmd)
    # 获取命令结果
    result_err, result_out = system_exec_command(cmd, 600)
    if result_err:
        log.error("【ICLOUDPD】错误信息：" + result_err)
    if result_out:
        log.debug("【ICLOUDPD】执行结果：" + result_out)

    end_time = datetime.now()
    if result_err == "timeout":
        sendmsg("【iCloudPd】命令执行超时，可能需要输入授权码！", "耗时：" + str((end_time - start_time).seconds) + " 秒")
    elif result_err != "":
        sendmsg("【iCloudPd】命令执行失败！", "错误信息：" + result_err)
    elif result_out.find("All photos have been downloaded!") == -1:
        sendmsg("【iCloudPd】处理失败！", result_out)
    else:
        sendmsg("【iCloudPd】照片同步完成",
                "耗时：" + str((end_time - start_time).seconds) + " 秒" +
                "\n\n成功：" + str(result_out.count("Downloading /")) +
                "\n\n已存在：" + str(result_out.count("already exists")))


if __name__ == "__main__":
    run_icloudpd()
