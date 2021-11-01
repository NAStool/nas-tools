# sensors监测温度
import re
from datetime import datetime
import socket
import log
import settings
from functions import system_exec_command
from message.send import sendmsg
import globalvar as gl


logger = log.Logger("scheduler").logger


def run_sensors():
    start_time = datetime.now()
    cmd = settings.get("scheduler.sensors_cmd")
    hostname = socket.gethostname()
    sensors_temperature_alert = float(settings.get("scheduler.sensors_temperature_alert"))
    sensors_alert_times = int(settings.get("scheduler.sensors_alert_times"))

    logger.debug("开始执行命令：" + cmd)
    # 获取命令结果
    result_err, result_out = system_exec_command(cmd, 5)

    end_time = datetime.now()
    if result_err == "timeout":
        sendmsg("【sensors】命令执行超时！", "耗时：" + str((end_time - start_time).seconds) + " 秒")
    elif result_err != "":
        sendmsg("【sensors】命令执行失败！", "错误信息：" + result_err)
    else:
        try:
            temp = re.search(r"\+\d{1,3}\.\d+°C", result_out, re.IGNORECASE).group(0).replace("+", "").replace("°C", "").strip()
        except AttributeError:
            temp = None
        if not temp:
            logger.error("【sensors】命令执行失败,未获取到温度数值：\n" + result_out)
            return
        else:
            logger.debug("CPU当前温度为：" + str(temp))
        if float(temp) > sensors_temperature_alert:
            pretemp = gl.get_value("SENSORS_TEMPERATURE_COUNT")
            if pretemp:
                pretemp = pretemp + 1
                gl.set_value("SENSORS_TEMPERATURE_COUNT", pretemp)
            else:
                pretemp = 1
                gl.set_value("SENSORS_TEMPERATURE_COUNT", pretemp)
            if pretemp >= sensors_alert_times:
                sendmsg("【sensors】CPU温度高报警", hostname + " CPU当前温度 " + str(temp) + " ℃, 已连续 " +
                        str(sensors_alert_times) + " 个周期超过 " + str(sensors_temperature_alert) + " ℃")
                gl.set_value("SENSORS_TEMPERATURE_COUNT", 0)


if __name__ == "__main__":
    run_sensors()
