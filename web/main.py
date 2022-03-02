import _thread
from flask import Flask, request, json, render_template, make_response, redirect
import log
from monitor.media_sync import sync_all
from pt.qbittorrent import Qbittorrent
from pt.transmission import Transmission
from scheduler.autoremove_torrents import AutoRemoveTorrents
from scheduler.pt_signin import PTSignin
from scheduler.pt_transfer import PTTransfer
from scheduler.rss_download import RSSDownloader
from version import APP_VERSION
from web.emby.discord import report_to_discord
from web.emby.emby_event import EmbyEvent
from message.send import Message
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

from config import WECHAT_MENU, get_config, PT_TRANSFER_INTERVAL, save_config
from web.wechat.WXBizMsgCrypt3 import WXBizMsgCrypt
import xml.etree.cElementTree as ETree


class FlaskApp:
    __app = None
    __web_port = None
    __ssl_cert = None
    __ssl_key = None

    message = None

    def __init__(self):
        self.message = Message()
        self.__app = create_flask_app()
        config = get_config()
        if config.get('app'):
            self.__web_port = config['app'].get('web_port')
            self.__ssl_cert = config['app'].get('ssl_cert')
            self.__ssl_key = config['app'].get('ssl_key')

    def run_service(self):
        try:
            if not self.__app:
                return

            if self.__ssl_cert:
                self.__app.run(
                    host='0.0.0.0',
                    port=self.__web_port,
                    debug=False,
                    use_reloader=False,
                    ssl_context=(self.__ssl_cert, self.__ssl_key)
                )
            else:
                self.__app.run(
                    host='0.0.0.0',
                    port=self.__web_port,
                    debug=False,
                    use_reloader=False
                )
        except Exception as err:
            log.error("【RUN】启动web服务失败：%s" % str(err))


def create_flask_app():
    config = get_config()
    app_cfg = config.get('app')
    if not app_cfg:
        return None
    else:
        if app_cfg.get('simple_mode'):
            # 精简模式不启用WEBUI
            return None
        elif not app_cfg.get('web_port'):
            return None
        elif not app_cfg.get('login_user'):
            return None
        elif not app_cfg.get('login_password'):
            return None

    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = False
    auth = HTTPBasicAuth()
    users = {str(config['app'].get('login_user')): generate_password_hash(config['app'].get('login_password'))}

    @auth.verify_password
    def verify_password(username, password):
        if username in users and \
                check_password_hash(users.get(username), str(password)):
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
        Message().sendmsg("【DDNS】IP地址变化", content)
        return '0'

    # 主页面
    @app.before_request
    def before_request():
        if request.url.startswith('http://'):
            ssl_cert = config['app'].get('ssl_cert')
            if ssl_cert:
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)

    @app.route('/', methods=['POST', 'GET'])
    @auth.login_required
    def main():
        # 读取定时服务配置
        scheduler_cfg_list = []
        if config.get('pt'):
            pt_check_interval = config['pt'].get('pt_check_interval')
            if pt_check_interval:
                tim_rssdownload = str(round(pt_check_interval / 60)) + "分"
                rss_state = 'ON'
            else:
                tim_rssdownload = ""
                rss_state = 'OFF'
            scheduler_cfg_list.append(
                {'name': 'RSS下载', 'time': tim_rssdownload, 'state': rss_state, 'id': 'rssdownload'})

            pt_monitor = config['pt'].get('pt_monitor')
            if pt_monitor:
                tim_pttransfer = str(round(PT_TRANSFER_INTERVAL / 60)) + "分"
                sta_pttransfer = 'ON'
            else:
                tim_pttransfer = ""
                sta_pttransfer = 'OFF'
            scheduler_cfg_list.append(
                {'name': 'PT文件转移', 'time': tim_pttransfer, 'state': sta_pttransfer, 'id': 'pttransfer'})

            pt_seeding_config_time = config['pt'].get('pt_seeding_time')
            if pt_seeding_config_time:
                pt_seeding_time = str(round(pt_seeding_config_time / 3600)) + "小时"
                sta_autoremovetorrents = 'ON'
                scheduler_cfg_list.append(
                    {'name': 'PT删种', 'time': pt_seeding_time, 'state': sta_autoremovetorrents,
                     'id': 'autoremovetorrents'})

            tim_ptsignin = config['pt'].get('ptsignin_cron')
            if tim_ptsignin:
                sta_ptsignin = 'ON'
                scheduler_cfg_list.append(
                    {'name': 'PT自动签到', 'time': tim_ptsignin, 'state': sta_ptsignin, 'id': 'ptsignin'})

        if config.get('sync'):
            sync_path = config['sync'].get('sync_path')
            if sync_path:
                sta_sync = 'ON'
                scheduler_cfg_list.append({'name': '资源同步',
                                           'time': '实时监控',
                                           'state': sta_sync,
                                           'id': 'sync'})

        # 读取RSS配置
        rss_cfg_list = []
        if config.get('pt'):
            rss_jobs = config['pt'].get('sites')
            if rss_jobs:
                for rss_job, job_info in rss_jobs.items():
                    res_type = job_info.get('res_type')
                    if res_type:
                        if not isinstance(res_type, list):
                            res_type = [res_type]
                    else:
                        res_type = []

                    job_cfg = {'job': rss_job,
                               'url': job_info.get('rssurl'),
                               'signin_url': job_info.get('signin_url'),
                               'cookie': job_info.get('cookie'),
                               'res_type': ','.join('%s' % key for key in res_type)}
                    # 存入配置列表
                    rss_cfg_list.append(job_cfg)

        # 读取RSS关键字
        movie_key_list = []
        if config.get('pt'):
            movie_keys = config['pt'].get('movie_keys')
            if movie_keys:
                if not isinstance(movie_keys, list):
                    movie_key_list = [movie_keys]
                else:
                    movie_key_list = movie_keys

        tv_key_list = []
        if config.get('pt'):
            tv_keys = config['pt'].get('tv_keys')
            if tv_keys:
                if not isinstance(tv_keys, list):
                    tv_key_list = [tv_keys]
                else:
                    tv_key_list = tv_keys

        return render_template("main.html",
                               app_version=APP_VERSION,
                               page="key",
                               scheduler_cfg_list=scheduler_cfg_list,
                               rss_cfg_list=rss_cfg_list,
                               movie_key_list=','.join('%s' % key for key in movie_key_list),
                               tv_key_list=','.join('%s' % key for key in tv_key_list)
                               )

    # 事件响应
    @app.route('/do', methods=['POST'])
    def do():
        cmd = request.form.get("cmd")
        data = json.loads(request.form.get("data"))
        if cmd:
            if cmd == "sch":
                sch_item = data["item"]
                if sch_item == "btn_autoremovetorrents":
                    AutoRemoveTorrents().run_schedule()
                if sch_item == "btn_pttransfer":
                    PTTransfer().run_schedule()
                if sch_item == "btn_ptsignin":
                    PTSignin().run_schedule()
                if sch_item == "btn_sync":
                    sync_all()
                if sch_item == "btn_rssdownload":
                    RSSDownloader().run_schedule()
                return {"retmsg": "执行完成！", "item": sch_item}

            if cmd == "rss":
                new_sites = {}
                for key, value in data.items():
                    if key.find('@') != -1:
                        pt_site = key.split('@')[0]
                        pt_site_item = key.split('@')[1]
                    else:
                        continue
                    if value.find(',') != -1:
                        if value.endswith(','):
                            value = value[0, -1]
                        value = value.split(',')
                    # 查看对应的site是否存在值
                    have_site = new_sites.get(pt_site)
                    if have_site:
                        # site存在，则加值
                        new_sites[pt_site][pt_site_item] = value
                    else:
                        # site不存在，则建site
                        new_sites[pt_site] = {pt_site_item: value}
                # 賛换掉
                if config['pt'].get('sites'):
                    config['pt']['sites'].update(new_sites)
                else:
                    config['pt']['sites'] = new_sites
                # 保存
                save_config(config)
                return {"retcode": 0}

            if cmd == "key":
                movie_keys = data["movie_keys"]
                # 电影关键字
                if movie_keys.find(',') != -1:
                    if movie_keys.endswith(','):
                        movie_keys = movie_keys[0, -1]
                    movie_keys = movie_keys.split(',')
                config['pt']['movie_keys'] = movie_keys
                # 电视剧关键字
                tv_keys = data["tv_keys"]
                if tv_keys.find(',') != -1:
                    if tv_keys.endswith(','):
                        tv_keys = tv_keys[0, -1]
                    tv_keys = tv_keys.split(',')
                config['pt']['tv_keys'] = tv_keys
                # 保存
                save_config(config)
                return {"retcode": 0}

    # 响应企业微信消息
    @app.route('/wechat', methods=['GET', 'POST'])
    def wechat():
        sToken = config['message'].get('wechat', {}).get('Token')
        sEncodingAESKey = config['message'].get('wechat', {}).get('EncodingAESKey')
        sCorpID = config['message'].get('wechat', {}).get('corpid')
        if not sToken or not sEncodingAESKey or not sCorpID:
            return
        wxcpt = WXBizMsgCrypt(sToken, sEncodingAESKey, sCorpID)
        sVerifyMsgSig = request.args.get("msg_signature")
        sVerifyTimeStamp = request.args.get("timestamp")
        sVerifyNonce = request.args.get("nonce")

        if request.method == 'GET':
            sVerifyEchoStr = request.args.get("echostr")
            log.info("收到微信验证请求: echostr= %s" % sVerifyEchoStr)
            ret, sEchoStr = wxcpt.VerifyURL(sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce, sVerifyEchoStr)
            if ret != 0:
                log.error("微信请求验证失败 VerifyURL ret: %s" % str(ret))
            # 验证URL成功，将sEchoStr返回给企业号
            return sEchoStr
        else:
            sReqData = request.data
            log.info("收到微信消息：" + str(sReqData))
            ret, sMsg = wxcpt.DecryptMsg(sReqData, sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce)
            if ret != 0:
                log.error("解密微信消息失败 DecryptMsg ret：%s" % str(ret))
            xml_tree = ETree.fromstring(sMsg)
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
                log.error("发生错误：%s" % str(err))
                return make_response("", 200)
            # 处理消息内容
            if content == "/ptr":
                _thread.start_new_thread(AutoRemoveTorrents().run_schedule, ())
            if content == "/ptt":
                _thread.start_new_thread(PTTransfer().run_schedule, ())
            if content == "/pts":
                _thread.start_new_thread(PTSignin().run_schedule, ())
            if content == "/rst":
                _thread.start_new_thread(sync_all, ())
            if content == "/rss":
                _thread.start_new_thread(RSSDownloader().run_schedule, ())
            else:
                if content.startswith("http://") or content.startswith("https://") or content.startswith("magnet:"):
                    # 添加种子任务
                    pt_client = config['pt'].get('pt_client')
                    if pt_client == "qbittorrent":
                        save_path = config['qbittorrent'].get('save_path')
                        if save_path:
                            try:
                                ret = Qbittorrent().add_qbittorrent_torrent(content, save_path)
                                if ret and ret.find("Ok") != -1:
                                    log.info("【WEB】添加qBittorrent任务：%s" % content)
                                    Message().sendmsg("添加qBittorrent下载任务成功！")
                            except Exception as e:
                                log.error("【WEB】添加qBittorrent任务出错：" + str(e))
                    elif pt_client == "transmission":
                        save_path = config['transmission'].get('save_path')
                        if save_path:
                            try:
                                ret = Transmission().add_transmission_torrent(content, save_path)
                                if ret:
                                    log.info("【WEB】添加transmission任务：%s" % content)
                                    Message().sendmsg("添加transmission下载任务成功！")
                            except Exception as e:
                                log.error("【WEB】添加transmission任务出错：" + str(e))
            return make_response(reponse_text, 200)

    return app
