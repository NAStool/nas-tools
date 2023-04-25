import random
from datetime import datetime
from threading import Event, Lock
from time import sleep

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from jinja2 import Template

from app.downloader import Downloader
from app.media import DouBan
from app.media.meta import MetaInfo
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.searcher import Searcher
from app.subscribe import Subscribe
from app.utils import ExceptionUtils
from app.utils.types import SearchType, RssType, EventType, MediaType
from config import Config
from web.backend.web_utils import WebUtils

lock = Lock()


class DoubanSync(_IPluginModule):
    # 插件名称
    module_name = "豆瓣同步"
    # 插件描述
    module_desc = "同步豆瓣在看、想看、看过记录，自动添加订阅或搜索下载。"
    # 插件图标
    module_icon = "douban.png"
    # 主题色
    module_color = "#05B711"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "doubansync_"
    # 加载顺序
    module_order = 17
    # 可使用的用户级别
    auth_level = 2

    # 退出事件
    _event = Event()
    # 私有属性
    douban = None
    searcher = None
    downloader = None
    subscribe = None
    _enable = False
    _onlyonce = False
    _interval = False
    _auto_search = False
    _auto_rss = False
    _users = []
    _days = 0
    _types = []
    _cookie = None
    _scheduler = None

    def init_config(self, config: dict = None):
        self.douban = DouBan()
        self.searcher = Searcher()
        self.downloader = Downloader()
        self.subscribe = Subscribe()
        if config:
            self._enable = config.get("enable")
            self._onlyonce = config.get("onlyonce")
            self._interval = config.get("interval")
            if self._interval and str(self._interval).isdigit():
                self._interval = int(self._interval)
            else:
                self._interval = 0
            self._auto_search = config.get("auto_search")
            self._auto_rss = config.get("auto_rss")
            self._cookie = config.get("cookie")
            self._users = config.get("users") or []
            if self._users:
                if isinstance(self._users, str):
                    self._users = self._users.split(',')
            self._days = config.get("days")
            if self._days and str(self._days).isdigit():
                self._days = int(self._days)
            else:
                self._days = 0
            self._types = config.get("types") or []
            if self._types:
                if isinstance(self._types, str):
                    self._types = self._types.split(',')

        # 停止现有任务
        self.stop_service()

        # 启动服务
        if self.get_state() or self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            if self._interval:
                self.info(f"订阅服务启动，周期：{self._interval} 小时，类型：{self._types}，用户：{self._users}")
                self._scheduler.add_job(self.sync, 'interval',
                                        hours=self._interval)

            if self._onlyonce:
                self.info(f"同步服务启动，立即运行一次")
                self._scheduler.add_job(self.sync, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())))
                # 关闭一次性开关
                self._onlyonce = False
                self.update_config({
                    "onlyonce": self._onlyonce,
                    "enable": self._enable,
                    "interval": self._interval,
                    "auto_search": self._auto_search,
                    "auto_rss": self._auto_rss,
                    "cookie": self._cookie,
                    "users": self._users,
                    "days": self._days,
                    "types": self._types
                })
            if self._scheduler.get_jobs():
                # 启动服务
                self._scheduler.print_jobs()
                self._scheduler.start()

    def get_state(self):
        return self._enable \
            and self._interval \
            and self._users \
            and self._types

    @staticmethod
    def get_fields():
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '开启豆瓣同步',
                            'required': "",
                            'tooltip': '开启后，定时同步豆瓣在看、想看、看过记录，有新内容时自动添加订阅或者搜索下载',
                            'type': 'switch',
                            'id': 'enable',
                        }
                    ],
                    [
                        {
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次（点击此对话框的确定按钮后即会运行，周期未设置也会运行），关闭后将仅按照刮削周期运行（同时上次触发运行的任务如果在运行中也会停止）',
                            'type': 'switch',
                            'id': 'onlyonce',
                        }
                    ],
                    [
                        {
                            'title': '豆瓣用户ID',
                            'required': "required",
                            'tooltip': '需要同步数据的豆瓣用户ID，在豆瓣个人主页地址栏/people/后面的数字；如有多个豆瓣用户ID，使用英文逗号,分隔',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'users',
                                    'placeholder': '用户1,用户2,用户3',
                                }
                            ]
                        },
                        {
                            'title': '同步数据类型',
                            'required': "required",
                            'tooltip': '同步哪些类型的收藏数据：do 在看，wish 想看，collect 看过，用英文逗号,分隔配置',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'types',
                                    'placeholder': 'do,wish,collect',
                                }
                            ]
                        }
                    ],
                    [
                        {
                            'title': '同步范围（天）',
                            'required': "required",
                            'tooltip': '同步多少天内的记录，0表示同步全部',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'days',
                                    'placeholder': '30',
                                }
                            ]
                        },
                        {
                            'title': '同步间隔（小时）',
                            'required': "required",
                            'tooltip': '间隔多久同步一次豆瓣数据，为了避免被豆瓣封禁IP，应尽可能拉长间隔时间',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'interval',
                                    'placeholder': '6',
                                }
                            ]
                        }
                    ],
                    [
                        {
                            'title': '豆瓣Cookie',
                            'required': '',
                            'tooltip': '受豆瓣限制，部分电影需要配置Cookie才能同步到数据；通过浏览器抓取',
                            'type': 'textarea',
                            'content':
                                {
                                    'id': 'cookie',
                                    'placeholder': '',
                                    'rows': 5
                                }
                        }
                    ],
                    [
                        {
                            'title': '自动搜索下载',
                            'required': "",
                            'tooltip': '开启后豆瓣同步的数据会自动进行站点聚合搜索下载',
                            'type': 'switch',
                            'id': 'auto_search',
                        },
                        {
                            'title': '自动添加订阅',
                            'required': "",
                            'tooltip': '开启后未进行搜索下载的或搜索下载不完整的将加入订阅',
                            'type': 'switch',
                            'id': 'auto_rss',
                        }
                    ],
                ]
            }
        ]

    def get_page(self):
        """
        插件的额外页面，返回页面标题和页面内容
        :return: 标题，页面内容，确定按钮响应函数
        """
        results = self.get_history()
        template = """
          <div class="table-responsive table-modal-body">
            <table class="table table-vcenter card-table table-hover table-striped">
              <thead>
              <tr>
                <th></th>
                <th>标题</th>
                <th>类型</th>
                <th>状态</th>
                <th>添加时间</th>
                <th></th>
              </tr>
              </thead>
              <tbody>
              {% if HistoryCount > 0 %}
                {% for Item in DoubanHistory %}
                  <tr id="douban_history_{{ Item.id }}">
                    <td class="w-5">
                      <img class="rounded w-5" src="{{ Item.image }}"
                           onerror="this.src='../static/img/no-image.png'" alt=""
                           style="min-width: 50px"/>
                    </td>
                    <td>
                      <div>{{ Item.name }} ({{ Item.year }})</div>
                      {% if Item.rating %}
                        <div class="text-muted text-nowrap">
                        评份：{{ Item.rating }}
                        </div>
                      {% endif %}
                    </td>
                    <td>
                      {{ Item.type }}
                    </td>
                    <td>
                      {% if Item.state == 'DOWNLOADED' %}
                        <span class="badge bg-green">已下载</span>
                      {% elif Item.state == 'RSS' %}
                        <span class="badge bg-blue">已订阅</span>
                      {% elif Item.state == 'NEW' %}
                        <span class="badge bg-blue">新增</span>
                      {% else %}
                        <span class="badge bg-orange">处理中</span>
                      {% endif %}
                    </td>
                    <td>
                      <small>{{ Item.add_time or '' }}</small>
                    </td>
                    <td>
                      <div class="dropdown">
                        <a href="#" class="btn-action" data-bs-toggle="dropdown"
                           aria-expanded="false">
                          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-dots-vertical {{ class }}"
                               width="24" height="24" viewBox="0 0 24 24"
                               stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                            <circle cx="12" cy="12" r="1"></circle>
                            <circle cx="12" cy="19" r="1"></circle>
                            <circle cx="12" cy="5" r="1"></circle>
                          </svg>
                        </a>
                        <div class="dropdown-menu dropdown-menu-end">
                          <a class="dropdown-item text-danger"
                             href='javascript:DoubanSync_delete_douban_history("{{ Item.id }}")'>
                            删除
                          </a>
                        </div>
                      </div>
                    </td>
                  </tr>
                {% endfor %}
              {% else %}
                <tr>
                  <td colspan="6" align="center">没有数据</td>
                </tr>
              {% endif %}
              </tbody>
            </table>
          </div>
        """
        return "同步历史", Template(template).render(HistoryCount=len(results),
                                                     DoubanHistory=results), None

    @staticmethod
    def get_script():
        """
        删除豆瓣历史记录的JS脚本
        """
        return """
          // 删除豆瓣历史记录
          function DoubanSync_delete_douban_history(id){
            ajax_post("run_plugin_method", {"plugin_id": 'DoubanSync', 'method': 'delete_sync_history', 'douban_id': id}, function (ret) {
              $("#douban_history_" + id).remove();
            });
        
          }
        """

    @staticmethod
    def get_command():
        """
        定义远程控制命令
        :return: 命令关键字、事件、描述、附带数据
        """
        return {
            "cmd": "/db",
            "event": EventType.DoubanSync,
            "desc": "豆瓣同步",
            "data": {}
        }

    def stop_service(self):
        """
        停止服务
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._event.set()
                    self._scheduler.shutdown()
                    self._event.clear()
                self._scheduler = None
        except Exception as e:
            print(str(e))

    def delete_sync_history(self, douban_id):
        """
        删除同步历史
        """
        return self.delete_history(key=douban_id)

    @EventHandler.register(EventType.DoubanSync)
    def sync(self, event=None):
        """
        同步豆瓣数据
        """
        if not self._interval:
            self.info("豆瓣配置：同步间隔未配置或配置不正确")
            return
        with lock:
            self.info("开始同步豆瓣数据...")
            # 拉取豆瓣数据
            medias = self.__get_all_douban_movies()
            # 开始搜索
            for media in medias:
                if not media or not media.get_name():
                    continue
                try:
                    # 查询数据库状态
                    history = self.get_history(media.douban_id)
                    if not history or history.get("state") == "NEW":
                        if self._auto_search:
                            # 需要搜索
                            media_info = WebUtils.get_mediainfo_from_id(mtype=media.type,
                                                                        mediaid=f"DB:{media.douban_id}",
                                                                        wait=True)
                            # 不需要自动加订阅，则直接搜索
                            if not media_info or not media_info.tmdb_info:
                                self.warn("%s 未查询到媒体信息" % media.get_name())
                                continue
                            # 检查是否存在，电视剧返回不存在的集清单
                            exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info)
                            # 已经存在
                            if exist_flag:
                                # 更新为已下载状态
                                self.info("%s 已存在" % media_info.title)
                                self.__update_history(media=media_info, state="DOWNLOADED")
                                continue
                            if not self._auto_rss:
                                # 开始搜索
                                search_result, no_exists, search_count, download_count = self.searcher.search_one_media(
                                    media_info=media_info,
                                    in_from=SearchType.DB,
                                    no_exists=no_exists,
                                    user_name=media_info.user_name)
                                if search_result:
                                    # 下载全了更新为已下载，没下载全的下次同步再次搜索
                                    self.__update_history(media=media_info, state="DOWNLOADED")
                            else:
                                # 需要加订阅，则由订阅去搜索
                                self.info(
                                    "%s %s 更新到%s订阅中..." % (media_info.title,
                                                                 media_info.year,
                                                                 media_info.type.value))
                                code, msg, _ = self.subscribe.add_rss_subscribe(mtype=media_info.type,
                                                                                name=media_info.title,
                                                                                year=media_info.year,
                                                                                channel=RssType.Auto,
                                                                                mediaid=f"DB:{media_info.douban_id}",
                                                                                in_from=SearchType.DB)
                                if code != 0:
                                    self.error("%s 添加订阅失败：%s" % (media_info.title, msg))
                                    # 订阅已存在
                                    if code == 9:
                                        self.__update_history(media=media_info, state="RSS")
                                else:
                                    # 插入为已RSS状态
                                    self.__update_history(media=media_info, state="RSS")
                        else:
                            # 不需要搜索
                            if self._auto_rss:
                                # 加入订阅，使状态为R
                                self.info("%s %s 更新到%s订阅中..." % (
                                    media.get_name(), media.year, media.type.value))
                                code, msg, _ = self.subscribe.add_rss_subscribe(mtype=media.type,
                                                                                name=media.get_name(),
                                                                                year=media.year,
                                                                                mediaid=f"DB:{media.douban_id}",
                                                                                channel=RssType.Auto,
                                                                                state="R",
                                                                                in_from=SearchType.DB)
                                if code != 0:
                                    self.error("%s 添加订阅失败：%s" % (media.get_name(), msg))
                                    # 订阅已存在
                                    if code == 9:
                                        self.__update_history(media=media, state="RSS")
                                else:
                                    # 插入为已RSS状态
                                    self.__update_history(media=media, state="RSS")
                            elif not history:
                                self.info("%s %s 更新到%s列表中..." % (
                                    media.get_name(), media.year, media.type.value))
                                self.__update_history(media=media, state="NEW")

                    else:
                        self.info(f"{media.douban_id} {media.get_name()} {media.year} 已处理过")
                except Exception as err:
                    self.error(f"{media.douban_id} {media.get_name()} {media.year} 处理失败：{str(err)}")
                    ExceptionUtils.exception_traceback(err)
                    continue
            self.info("豆瓣数据同步完成")

    def __update_history(self, media, state):
        """
        插入历史记录
        """
        value = {
            "id": media.douban_id,
            "name": media.title or media.get_name(),
            "year": media.year,
            "type": media.type.value,
            "rating": media.vote_average,
            "image": media.get_poster_image(),
            "state": state,
            "add_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if self.get_history(key=media.douban_id):
            self.update_history(key=media.douban_id, value=value)
        else:
            self.history(key=media.douban_id, value=value)

    def __get_all_douban_movies(self):
        """
        获取每一个用户的每一个类型的豆瓣标记
        :return: 搜索到的媒体信息列表（不含TMDB信息）
        """
        if not self._interval \
                or not self._users \
                or not self._types:
            self.error("豆瓣插件未配置或配置不正确")
            return []
        # 返回媒体列表
        media_list = []
        # 豆瓣ID列表
        douban_ids = {}
        # 每页条数
        perpage_number = 15
        # 每一个用户
        for user in self._users:
            if not user:
                continue
            # 查询用户名称
            user_name = ""
            userinfo = self.douban.get_user_info(userid=user)
            if userinfo:
                user_name = userinfo.get("name")
            # 每一个类型成功数量
            user_succnum = 0
            for mtype in self._types:
                if not mtype:
                    continue
                self.info(f"开始获取 {user_name or user} 的 {mtype} 数据...")
                # 开始序号
                start_number = 0
                # 类型成功数量
                user_type_succnum = 0
                # 每一页
                while True:
                    # 页数
                    page_number = int(start_number / perpage_number + 1)
                    # 当前页成功数量
                    sucess_urlnum = 0
                    # 是否继续下一页
                    continue_next_page = True
                    self.debug(f"开始解析第 {page_number} 页数据...")
                    try:
                        items = self.douban.get_douban_wish(dtype=mtype, userid=user, start=start_number, wait=True)
                        if not items:
                            self.warn(f"第 {page_number} 页未获取到数据")
                            break
                        # 解析豆瓣ID
                        for item in items:
                            # 时间范围
                            date = item.get("date")
                            if not date:
                                continue_next_page = False
                                break
                            else:
                                mark_date = datetime.strptime(date, '%Y-%m-%d')
                                if self._days and not (datetime.now() - mark_date).days < int(self._days):
                                    continue_next_page = False
                                    break
                            doubanid = item.get("id")
                            if str(doubanid).isdigit():
                                self.info("解析到媒体：%s" % doubanid)
                                if doubanid not in douban_ids:
                                    douban_ids[doubanid] = {
                                        "user_name": user_name
                                    }
                                sucess_urlnum += 1
                                user_type_succnum += 1
                                user_succnum += 1
                        self.debug(
                            f"{user_name or user} 第 {page_number} 页解析完成，共获取到 {sucess_urlnum} 个媒体")
                    except Exception as err:
                        ExceptionUtils.exception_traceback(err)
                        self.error(f"{user_name or user} 第 {page_number} 页解析出错：%s" % str(err))
                        break
                    # 继续下一页
                    if continue_next_page:
                        start_number += perpage_number
                    else:
                        break
                # 当前类型解析结束
                self.debug(f"用户 {user_name or user} 的 {mtype} 解析完成，共获取到 {user_type_succnum} 个媒体")
            self.info(f"用户 {user_name or user} 解析完成，共获取到 {user_succnum} 个媒体")
        self.info(f"所有用户解析完成，共获取到 {len(douban_ids)} 个媒体")
        # 查询豆瓣详情
        for doubanid, info in douban_ids.items():
            douban_info = self.douban.get_douban_detail(doubanid=doubanid, wait=True)
            # 组装媒体信息
            if not douban_info:
                self.warn("%s 未正确获取豆瓣详细信息，尝试使用网页获取" % doubanid)
                douban_info = self.douban.get_media_detail_from_web(doubanid)
                if not douban_info:
                    self.warn("%s 无权限访问，需要配置豆瓣Cookie" % doubanid)
                    # 随机休眠
                    sleep(round(random.uniform(1, 5), 1))
                    continue
            media_type = MediaType.TV if douban_info.get("episodes_count") else MediaType.MOVIE
            self.info("%s：%s %s".strip() % (media_type.value, douban_info.get("title"), douban_info.get("year")))
            meta_info = MetaInfo(title="%s %s" % (douban_info.get("title"), douban_info.get("year") or ""))
            meta_info.douban_id = doubanid
            meta_info.type = media_type
            meta_info.overview = douban_info.get("intro")
            meta_info.poster_path = douban_info.get("cover_url")
            rating = douban_info.get("rating", {}) or {}
            meta_info.vote_average = rating.get("value") or ""
            meta_info.imdb_id = douban_info.get("imdbid")
            meta_info.user_name = info.get("user_name")
            if meta_info not in media_list:
                media_list.append(meta_info)
            # 随机休眠
            sleep(round(random.uniform(1, 5), 1))
        return media_list
