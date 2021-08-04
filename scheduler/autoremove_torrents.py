# 定时在DSM中执行命令清理qbittorrent的种子
import log
import settings
from functions import system_exec_command
from message.send import sendmsg

logger = log.Logger("scheduler").logger


def run_autoremovetorrents():
    cmd = settings.get("scheduler.autoremovetorrents_cmd")
    logger.info("开始执行命令：" + cmd)
    # 获取命令结果
    result_err, result_out = system_exec_command(cmd, 60)
    if result_err:
        logger.error("错误信息：" + result_err)
    if result_out:
        logger.info("执行结果：" + result_out)

    if result_err != "":
        if result_err.find(" Login successfully") == -1:
            sendmsg("【AutoRemoveTorrents】命令执行失败！", "错误信息：" + result_err)


if __name__ == "__main__":
    run_autoremovetorrents()
