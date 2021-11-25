from flask import Flask, request, json, render_template

import settings
import log
from functions import system_exec_command, mysql_query
from monitor.movie_trailer import movie_trailer_all
from monitor.resiliosync import resiliosync_all
from rmt.qbittorrent import login_qbittorrent
from scheduler.autoremove_torrents import run_autoremovetorrents
from scheduler.hot_trailer import run_hottrailers
from scheduler.icloudpd import run_icloudpd
from scheduler.pt_signin import run_ptsignin
from scheduler.qb_transfer import run_qbtransfer
from scheduler.rss_download import run_rssdownload
from scheduler.smzdm_signin import run_smzdmsignin
from scheduler.unicom_signin import run_unicomsignin
from web.emby.discord import report_to_discord
from web.emby.emby_event import EmbyEvent
from message.send import sendmsg
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash


def create_app():
    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = False
    auth = HTTPBasicAuth()
    users = {
        "admin": generate_password_hash(settings.get("root.login_password"))
    }

    @auth.verify_password
    def verify_password(username, password):
        if username in users and \
                check_password_hash(users.get(username), password):
            return username

    # Emby消息通知
    @app.route('/emby', methods=['POST', 'GET'])
    def emby():
        if request.method == 'POST':
            request_json = json.loads(request.form.get('data', {}))
        else:
            server_name = request.args.get("server_name")
            user_name = request.args.get("user_name")
            device_name = request.args.get("device_name")
            ip = request.args.get("ip")
            flag = request.args.get("flag")
            request_json = {"Event": "user.login",
                            "User": {"user_name": user_name, "device_name": device_name, "device_ip": ip},
                            "Server": {"server_name": server_name},
                            "Status": flag
                            }
        # log.debug("输入报文：" + str(request_json))
        event = EmbyEvent(request_json)
        report_to_discord(event)
        return 'Success'

    # DDNS消息通知
    @app.route('/ddns', methods=['POST'])
    def ddns():
        request_json = json.loads(request.data, {})
        log.debug("【DDNS】输入报文：" + str(request_json))
        text = request_json['text']
        content = text['content']
        sendmsg("【DDNS】IP地址变化", content)
        return '0'

    # 主页面
    @app.route('/', methods=['POST', 'GET'])
    @auth.login_required
    def main():
        # 读取定时服务配置
        tim_autoremovetorrents = settings.get("scheduler.autoremovetorrents_interval")
        sta_autoremovetorrents = settings.get("scheduler.autoremovetorrents_flag")
        tim_qbtransfer = settings.get("scheduler.qbtransfer_interval")
        sta_qbtransfer = settings.get("scheduler.qbtransfer_flag")
        tim_icloudpd = settings.get("scheduler.icloudpd_interval")
        sta_icloudpd = settings.get("scheduler.icloudpd_flag")
        tim_hottrailers = settings.get("scheduler.hottrailer_cron")
        sta_hottrailers = settings.get("scheduler.hottrailer_flag")
        tim_ptsignin = settings.get("scheduler.ptsignin_cron")
        sta_ptsignin = settings.get("scheduler.ptsignin_flag")
        tim_smzdmsignin = settings.get("scheduler.smzdmsignin_cron")
        sta_smzdmsignin = settings.get("scheduler.smzdmsignin_flag")
        tim_unicomsignin = settings.get("scheduler.unicomsignin_cron")
        sta_unicomsignin = settings.get("scheduler.unicomsignin_flag")
        sta_movietrailer = settings.get("monitor.movie_flag")
        sta_resiliosync = settings.get("monitor.resiliosync_flag")
        tim_rssdownload = settings.get("scheduler.rssdownload_interval")
        sta_rssdownload = settings.get("scheduler.rssdownload_flag")

        # 读取日志配置
        logtype = settings.get("root.logtype")

        return render_template("main.html",
                               page="rmt",
                               tim_autoremovetorrents=tim_autoremovetorrents,
                               sta_autoremovetorrents=sta_autoremovetorrents,
                               tim_qbtransfer=tim_qbtransfer,
                               sta_qbtransfer=sta_qbtransfer,
                               tim_icloudpd=tim_icloudpd,
                               sta_icloudpd=sta_icloudpd,
                               tim_hottrailers=tim_hottrailers,
                               sta_hottrailers=sta_hottrailers,
                               tim_ptsignin=tim_ptsignin,
                               sta_ptsignin=sta_ptsignin,
                               tim_smzdmsignin=tim_smzdmsignin,
                               sta_smzdmsignin=sta_smzdmsignin,
                               tim_unicomsignin=tim_unicomsignin,
                               sta_unicomsignin=sta_unicomsignin,
                               sta_movietrailer=sta_movietrailer,
                               sta_resiliosync=sta_resiliosync,
                               tim_rssdownload=tim_rssdownload,
                               sta_rssdownload=sta_rssdownload,
                               log_type=logtype
                               )

    # 事件响应
    @app.route('/do', methods=['POST'])
    def do():
        cmd = request.form.get("cmd")
        data = json.loads(request.form.get("data"))
        if cmd:
            if cmd == "rmt":
                p_name = data["name"]
                p_year = data["year"]
                p_path = data["path"]
                if p_path:
                    v_path = p_path.split("|")[0]
                    v_hash = p_path.split("|")[1]
                else:
                    v_path = ""
                    v_hash = ""
                rootpath = settings.get("root.rootpath")
                cmdstr = "bash " + rootpath + "/bin/rmt.sh" + " \"" + p_name + "\" \"" + v_path + "\" \"" + v_hash + "\" \"" + p_year + "\""
                log.info("【WEB】执行命令：" + cmdstr)
                std_err, std_out = system_exec_command(cmdstr, 1800)
                # 读取qBittorrent列表
                qbt = login_qbittorrent()
                torrents = qbt.torrents_info()
                trans_qbpath = settings.get("rmt.rmt_qbpath")
                trans_containerpath = settings.get("rmt.rmt_containerpath")
                path_list = []
                for torrent in torrents:
                    log.info(torrent.name + "：" + torrent.state)
                    if torrent.state == "uploading" or torrent.state == "stalledUP":
                        true_path = torrent.content_path.replace(str(trans_qbpath), str(trans_containerpath))
                        path_list.append(true_path + "|" + torrent.hash)
                qbt.auth_log_out()
                return {"rmt_stderr": std_err, "rmt_stdout": std_out, "rmt_paths": path_list}

            if cmd == "rmt_qry":
                # 读取qBittorrent列表
                qbt = login_qbittorrent()
                torrents = qbt.torrents_info()
                trans_qbpath = settings.get("rmt.rmt_qbpath")
                trans_containerpath = settings.get("rmt.rmt_containerpath")
                path_list = []
                for torrent in torrents:
                    log.info(torrent.name + "：" + torrent.state)
                    if torrent.state == "uploading" or torrent.state == "stalledUP":
                        true_path = torrent.content_path.replace(str(trans_qbpath), str(trans_containerpath))
                        path_list.append(true_path + "|" + torrent.hash)
                qbt.auth_log_out()
                return {"rmt_paths": path_list}

            if cmd == "msg":
                title = data["title"]
                text = data["text"]
                retcode, retmsg = "", ""
                if title or text:
                    retcode, retmsg = sendmsg(title, text)
                return {"msg_code": retcode, "msg_msg": retmsg}

            if cmd == "set_qry":
                # 读取配置文件
                cfg = open(settings.get_config_path(), mode="r", encoding="utf8")
                config_str = cfg.read()
                cfg.close()
                return {"config_str": config_str}

            if cmd == "set":
                editer_str = data["editer_str"]
                if editer_str:
                    cfg = open(settings.get_config_path(), mode="w", encoding="utf8")
                    cfg.write(editer_str)
                    cfg.flush()
                    cfg.close()
                return {"retcode": 0}

            if cmd == "log_qry":
                log_list = mysql_query("SELECT id,type,name,text,time FROM system_log ORDER BY time DESC LIMIT 100")
                return {"log_list": log_list}

            if cmd == "sch":
                sch_item = data["item"]
                if sch_item == "sch_btn_autoremovetorrents":
                    run_autoremovetorrents()
                if sch_item == "sch_btn_qbtransfer":
                    run_qbtransfer()
                if sch_item == "sch_btn_icloudpd":
                    run_icloudpd()
                if sch_item == "sch_btn_hottrailers":
                    run_hottrailers()
                if sch_item == "sch_btn_ptsignin":
                    run_ptsignin()
                if sch_item == "sch_btn_smzdmsignin":
                    run_smzdmsignin()
                if sch_item == "sch_btn_unicomsignin":
                    run_unicomsignin()
                if sch_item == "sch_btn_movietrailer":
                    movie_trailer_all()
                if sch_item == "sch_btn_resiliosync":
                    resiliosync_all()
                if sch_item == "sch_btn_rssdownload":
                    run_rssdownload()
                return {"retmsg": "执行完成！", "item": sch_item}

    return app
