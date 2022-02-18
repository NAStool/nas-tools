import _thread
from flask import Flask, request, json, render_template, make_response, redirect
import log
from monitor.movie_trailer import movie_trailer_all
from monitor.resiliosync import resiliosync_all
from rmt.media import transfer_directory
from rmt.qbittorrent import login_qbittorrent, get_qbittorrent_tasks, set_torrent_status, transfer_qbittorrent_task
from scheduler.autoremove_torrents import run_autoremovetorrents
from scheduler.hot_trailer import run_hottrailers
from scheduler.pt_signin import run_ptsignin
from scheduler.qb_transfer import run_qbtransfer
from scheduler.rss_download import run_rssdownload, add_qbittorrent_torrent
from web.emby.discord import report_to_discord
from web.emby.emby_event import EmbyEvent
from message.send import sendmsg
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

from config import WECHAT_MENU, get_config, AUTO_REMOVE_TORRENTS_INTERVAL, QBITTORRENT_TRANSFER_INTERVAL, \
    HOT_TRAILER_INTERVAL, save_config, get_config_path
from web.wechat.WXBizMsgCrypt3 import WXBizMsgCrypt
import xml.etree.cElementTree as ET


def create_app():
    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = False
    auth = HTTPBasicAuth()
    config = get_config()
    users = {
        config['app']['login_user']: generate_password_hash(config['app']['login_password'])
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
    @app.before_request
    def before_request():
        if request.url.startswith('http://'):
            ssl_cert = config['app']['ssl_cert']
            if ssl_cert:
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)

    @app.route('/', methods=['POST', 'GET'])
    @auth.login_required
    def main():
        # 读取定时服务配置
        scheduler_cfg_list = []
        tim_rssdownload = str(round(config['pt']['pt_check_interval']/60)) + "分"
        rss_state = 'OFF'
        if tim_rssdownload:
            rss_state = 'ON'
        scheduler_cfg_list.append(
            {'name': 'RSS下载', 'time': tim_rssdownload, 'state': rss_state, 'id': 'rssdownload'})

        pt_seeding_time = str(round(config['pt']['pt_seeding_time']/3600)) + "小时"
        sta_autoremovetorrents = 'OFF'
        if pt_seeding_time:
            sta_autoremovetorrents = 'ON'
        scheduler_cfg_list.append(
            {'name': 'qBittorrent删种', 'time': pt_seeding_time, 'state': sta_autoremovetorrents,
             'id': 'autoremovetorrents'})

        tim_qbtransfer = str(round(QBITTORRENT_TRANSFER_INTERVAL/60)) + "分"
        scheduler_cfg_list.append(
            {'name': 'qBittorrent转移', 'time': tim_qbtransfer, 'state': 'ON', 'id': 'qbtransfer'})

        resiliosync_path = config['media']['resiliosync_path']
        sta_resiliosync = 'OFF'
        if resiliosync_path:
            sta_resiliosync = 'ON'
        scheduler_cfg_list.append(
            {'name': 'ResilioSync同步', 'time': '实时监控', 'state': sta_resiliosync, 'id': 'resiliosync'})

        tim_hottrailers = str(round(HOT_TRAILER_INTERVAL/3600)) + "小时"
        hottrailer_path = config['media']['hottrailer_path']
        sta_hottrailers = 'OFF'
        if hottrailer_path:
            sta_hottrailers = 'ON'
        scheduler_cfg_list.append(
            {'name': '热门预告', 'time': tim_hottrailers, 'state': sta_hottrailers, 'id': 'hottrailers'})

        sta_movietrailer = 'ON'
        scheduler_cfg_list.append({'name': '预告片下载', 'time': '实时监控', 'state': sta_movietrailer, 'id': 'movietrailer'})

        tim_ptsignin = config['pt']['ptsignin_cron']
        sta_ptsignin = 'OFF'
        if tim_ptsignin:
            sta_ptsignin = 'ON'
        scheduler_cfg_list.append({'name': 'PT签到', 'time': tim_ptsignin, 'state': sta_ptsignin, 'id': 'ptsignin'})

        # 读取RSS配置
        # 读取配置
        rss_cfg_list = []
        rss_jobs = config['pt']['sites']
        for rss_job, job_info in rss_jobs.items():
            # 读取子配置
            job_cfg = {'job': rss_job, 'url': job_info['rssurl'], 'movie_type': job_info['movie_type'],
                       'movie_re': job_info['movie_re'], 'tv_re': job_info['tv_re'],
                       'signin_url': job_info['signin_url'], 'cookie': job_info['cookie']}
            # 存入配置列表
            rss_cfg_list.append(job_cfg)

        return render_template("main.html",
                               page="rss",
                               scheduler_cfg_list=scheduler_cfg_list,
                               rss_cfg_list=rss_cfg_list
                               )

    # 事件响应
    @app.route('/do', methods=['POST'])
    def do():
        cmd = request.form.get("cmd")
        data = json.loads(request.form.get("data"))
        if cmd:
            if cmd == "rmt_qry":
                # 读取qBittorrent列表
                return {"rmt_paths": get_qbittorrent_tasks()}

            if cmd == "rmt":
                p_name = data["name"]
                p_year = data["year"]
                p_path = data["path"]
                p_type = data["type"]
                p_season = data["season"]
                if p_path and p_name:
                    v_path = p_path.split("|")[0]
                    v_hash = p_path.split("|")[1]
                    done_flag = transfer_directory(in_from="qBittorrent", in_name=p_name, in_title=p_name,
                                                   in_path=v_path,
                                                   in_year=p_year, in_type=p_type, in_season=p_season)
                    if v_hash and done_flag:
                        set_torrent_status(v_hash)
                else:
                    run_qbtransfer()
                return {"rmt_stderr": "0", "rmt_stdout": "处理成功！", "rmt_paths": get_qbittorrent_tasks()}

            if cmd == "set_qry":
                # 读取配置文件
                cfg = open(get_config_path(), mode="r", encoding="utf8")
                config_str = cfg.read()
                cfg.close()
                return {"config_str": config_str}

            if cmd == "set":
                editer_str = data["editer_str"]
                if editer_str:
                    cfg = open(get_config_path(), mode="w", encoding="utf8")
                    cfg.write(editer_str)
                    cfg.flush()
                    cfg.close()
                return {"retcode": 0}

            if cmd == "sch":
                sch_item = data["item"]
                if sch_item == "btn_autoremovetorrents":
                    run_autoremovetorrents()
                if sch_item == "btn_qbtransfer":
                    run_qbtransfer()
                if sch_item == "btn_hottrailers":
                    run_hottrailers()
                if sch_item == "btn_ptsignin":
                    run_ptsignin()
                if sch_item == "btn_movietrailer":
                    movie_trailer_all()
                if sch_item == "btn_resiliosync":
                    resiliosync_all()
                if sch_item == "btn_rssdownload":
                    run_rssdownload()
                return {"retmsg": "执行完成！", "item": sch_item}

            if cmd == "rss":
                for key, value in data.items():
                    pt_site = key.split('@')[0]
                    pt_site_item = key.split('@')[1]
                    if value.startswith("[") and value.endswith("]"):
                        value = eval(value)
                    config['pt']['sites'][pt_site][pt_site_item] = value
                save_config(config)
                return {"retcode": 0}

    # 响应企业微信消息
    @app.route('/wechat', methods=['GET', 'POST'])
    def wechat():
        sToken = config['message']['wechat']['Token']
        sEncodingAESKey = config['message']['wechat']['EncodingAESKey']
        sCorpID = config['message']['wechat']['corpid']
        wxcpt = WXBizMsgCrypt(sToken, sEncodingAESKey, sCorpID)
        sVerifyMsgSig = request.args.get("msg_signature")
        sVerifyTimeStamp = request.args.get("timestamp")
        sVerifyNonce = request.args.get("nonce")

        if request.method == 'GET':
            sVerifyEchoStr = request.args.get("echostr")
            log.info("收到微信验证请求: echostr=" + sVerifyEchoStr)
            ret, sEchoStr = wxcpt.VerifyURL(sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce, sVerifyEchoStr)
            if ret != 0:
                log.error("微信请求验证失败 VerifyURL ret: " + str(ret))
            # 验证URL成功，将sEchoStr返回给企业号
            return sEchoStr
        else:
            sReqData = request.data
            log.info("收到微信消息：" + str(sReqData))
            ret, sMsg = wxcpt.DecryptMsg(sReqData, sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce)
            if ret != 0:
                log.error("解密微信消息失败 DecryptMsg ret：" + str(ret))
            xml_tree = ET.fromstring(sMsg)
            reponse_text = ""
            try:
                msg_type = xml_tree.find("MsgType").text
                if msg_type == "event":
                    event_key = xml_tree.find("EventKey").text
                    log.info("点击菜单：" + event_key)
                    content = WECHAT_MENU[event_key.split('#')[2]]
                else:
                    content = xml_tree.find("Content").text
                    log.info("消息内容：" + content)
                    reponse_text = content
            except Exception as err:
                log.error("发生错误：" + str(err))
                return make_response("", 200)
            # 处理消息内容
            if content == "/qbr":
                _thread.start_new_thread(run_autoremovetorrents, ())
            if content == "/qbt":
                _thread.start_new_thread(run_qbtransfer, ())
            if content == "/hotm":
                _thread.start_new_thread(run_hottrailers, ())
            if content == "/pts":
                _thread.start_new_thread(run_ptsignin, ())
            if content == "/mrt":
                _thread.start_new_thread(movie_trailer_all, ())
            if content == "/rst":
                _thread.start_new_thread(resiliosync_all, ())
            if content == "/rss":
                _thread.start_new_thread(run_rssdownload, ())
            else:
                if content.startswith("http://") or content.startswith("https://") or content.startswith("magnet:"):
                    # 添加种子任务
                    save_path = config['qbittorrent']['save_path']
                    if save_path:
                        try:
                            ret = add_qbittorrent_torrent(content, save_path)
                            if ret and ret.find("Ok") != -1:
                                log.info("【WEB】添加qBittorrent任务：" + content)
                                sendmsg("添加qBittorrent下载任务成功！")
                        except Exception as e:
                            log.error("【WEB】添加qBittorrent任务出错：" + str(e))
            return make_response(reponse_text, 200)

    return app
