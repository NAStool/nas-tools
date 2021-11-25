# 定时在DSM中执行命令进行联通营业厅签到
import os
from datetime import datetime
import log
import settings
from functions import system_exec_command
from message.send import sendmsg


def run_unicomsignin():
    try:
        unicomsignin()
    except Exception as err:
        log.error("【RUN】执行定时任务unicomsignin出错：" + str(err))
        sendmsg("【NASTOOL】执行定时任务unicomsignin出错！", str(err))


def unicomsignin():
    start_time = datetime.now()
    log.info("【UNICOM-SIGN】连接成功！")
    tasks = eval(settings.get("unicom.unicom_tasks"))
    appid = settings.get("unicom.unicom_appid")
    succ_text = ""
    fail_text = ""
    succ_flag = True
    for task in tasks:
        cmd = settings.get("scheduler.unicomsignin_cmd")
        user = task.split(":")[0]
        password = task.split(":")[1]
        cmd = cmd.replace("$USER", user).replace("$PASSWORD", password).replace("$APPID", appid)
        log.info("【UNICOM-SIGN】开始执行命令：" + cmd)
        # 获取命令结果
        result_err, result_out = system_exec_command(cmd, 600)
        if result_err:
            log.error("【UNICOM-SIGN】错误信息：" + result_err)
        if result_out:
            log.info("【UNICOM-SIGN】执行结果：" + result_out)
        if result_err != "":
            succ_flag = False
            if fail_text == "":
                fail_text = fail_text + result_err
            else:
                fail_text = fail_text + "\n\n" + result_err
        if result_out != "":
            if succ_text == "":
                succ_text = succ_text + result_out
            else:
                succ_text = succ_text + "\n\n" + result_out

        end_time = datetime.now()
        if not succ_flag:
            sendmsg("【HiUnicom】每日签到出错！",
                    "错误：" + fail_text)
        else:
            sendmsg("【HiUnicom】每日签到", "手机号：" + user +
                    "\n\n耗时：" + str((end_time - start_time).seconds) + " 秒")


if __name__ == "__main__":
    run_unicomsignin()
