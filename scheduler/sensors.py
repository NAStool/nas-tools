# sensors监测温度
import re
from datetime import datetime
import socket
import log
import settings
from functions import system_exec_command
from message.send import sendmsg
import globalvar as gv


def run_sensors():
    try:
        sensors()
    except Exception as err:
        log.error("【RUN】执行任务sensors出错：" + str(err))
        sendmsg("【NASTOOL】执行任务sensors出错！", str(err))


def get_temperature():
    temp = 0
    cmd = settings.get("scheduler.sensors_cmd")
    log.debug("【SENSORS】开始执行命令：" + cmd)
    # 获取命令结果
    start_time = datetime.now()
    result_err, result_out = system_exec_command(cmd, 5)
    end_time = datetime.now()
    if result_err == "timeout":
        log.error("【sensors】命令执行超时！耗时：" + str((end_time - start_time).seconds) + " 秒")
    elif result_err != "":
        log.error("【sensors】命令执行失败！错误信息：" + result_err)
    else:
        try:
            temp = re.search(r"\+\d{1,3}\.\d+\s?[C℃]", result_out, re.IGNORECASE).group(0).replace("+", "").replace("C", "").replace("℃", "").strip()
        except AttributeError:
            temp = 0
        if temp == 0:
            log.error("【SENSORS】命令执行失败,未获取到温度数值：\n" + result_out)
        else:
            log.info("【SENSORS】CPU当前温度为：" + str(temp))
            return temp
    return temp


def sensors():
    hostname = socket.gethostname()
    sensors_temperature_alert = float(settings.get("scheduler.sensors_temperature_alert"))
    sensors_alert_times = int(settings.get("scheduler.sensors_alert_times"))
    temp = get_temperature()
    if temp != 0:
        if float(temp) > sensors_temperature_alert:
            pretemp = gv.get_value("SENSORS_TEMPERATURE_COUNT")
            if pretemp:
                pretemp = pretemp + 1
                gv.set_value("SENSORS_TEMPERATURE_COUNT", pretemp)
            else:
                pretemp = 1
                gv.set_value("SENSORS_TEMPERATURE_COUNT", pretemp)
            if pretemp >= sensors_alert_times:
                sendmsg("【SENSORS】CPU温度高报警", hostname + " CPU当前温度 " + str(temp) + " ℃, 已连续 " +
                        str(sensors_alert_times) + " 个周期超过 " + str(sensors_temperature_alert) + " ℃")
                gv.set_value("SENSORS_TEMPERATURE_COUNT", 0)
        else:
            gv.set_value("SENSORS_TEMPERATURE_COUNT", 0)


if __name__ == "__main__":
    run_sensors()
