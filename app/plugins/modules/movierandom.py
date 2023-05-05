import random
from datetime import datetime
from threading import Event

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from jinja2 import Template

import log
from app.conf import ModuleConf
from app.helper import RssHelper
from app.media import Media
from app.mediaserver import MediaServer
from app.plugins.modules._base import _IPluginModule
from app.subscribe import Subscribe
from app.utils.types import SearchType, RssType, MediaType
from config import Config


class MovieRandom(_IPluginModule):
    # 插件名称
    module_name = "电影随机订阅"
    # 插件描述
    module_desc = "随机获取一部未入库的电影，自动添加订阅。"
    # 插件图标
    module_icon = "random.png"
    # 主题色
    module_color = "#0000FF"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "thsrite"
    # 作者主页
    author_url = "https://github.com/thsrite"
    # 插件配置项ID前缀
    module_config_prefix = "movierandom_"
    # 加载顺序
    module_order = 18
    # 可使用的用户级别
    auth_level = 2

    # 退出事件
    _event = Event()
    # 私有属性
    mediaserver = None
    rsshelper = None
    subscribe = None
    _scheduler = None
    _enable = False
    _onlyonce = False
    _cron = None
    _language = None
    _genres = None
    _vote = None
    _date = None

    @staticmethod
    def get_fields():
        language_options = ModuleConf.DISCOVER_FILTER_CONF.get("tmdb_movie").get("with_original_language").get(
            "options")
        genres_options = ModuleConf.DISCOVER_FILTER_CONF.get("tmdb_movie").get("with_genres").get("options")
        # tmdb电影类型
        genres = {m.get('name'): m.get('name') for m in genres_options}
        # tmdb电影语言
        language = {m.get('name'): m.get('name') for m in language_options}
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '开启电影随机订阅',
                            'required': "",
                            'tooltip': '开启后，定时随机订阅一部电影。',
                            'type': 'switch',
                            'id': 'enable',
                        },
                        {
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次（点击此对话框的确定按钮后即会运行，周期未设置也会运行），关闭后将仅按照随机周期运行（同时上次触发运行的任务如果在运行中也会停止）',
                            'type': 'switch',
                            'id': 'onlyonce',
                        },
                    ],
                    [
                        {
                            'title': '随机周期',
                            'required': "required",
                            'tooltip': '电影随机订阅的时间周期，支持5位cron表达式。',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'cron',
                                    'placeholder': '0 0 0 ? *',
                                }
                            ]
                        },
                        {
                            'title': '上映时间',
                            'required': "",
                            'tooltip': '电影上映时间，大于该时间的会被订阅',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'date',
                                    'placeholder': '2022',
                                }
                            ]
                        },
                        {
                            'title': '电影评分',
                            'required': "",
                            'tooltip': '最低评分，大于等于该评分的会被订阅（最大10）',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'vote',
                                    'placeholder': '8',
                                }
                            ]
                        },
                    ],
                    [
                        {
                            'title': '电影类型',
                            'required': "",
                            'type': 'select',
                            'content': [
                                {
                                    'id': 'genres',
                                    'options': genres,
                                    'default': '全部'
                                },
                            ]
                        },
                        {
                            'title': '电影语言',
                            'required': "",
                            'type': 'select',
                            'content': [
                                {
                                    'id': 'language',
                                    'options': language,
                                    'default': '全部'
                                },
                            ]
                        },
                    ]
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
                   {% for Item in MovieRandomHistory %}
                     <tr id="movie_random_history_{{ Item.id }}">
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
                                href='javascript:MovieRandom_delete_history("{{ Item.id }}")'>
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
        return "随机历史", Template(template).render(HistoryCount=len(results),
                                                     MovieRandomHistory=results), None

    @staticmethod
    def get_script():
        """
        删除随机电影历史记录的JS脚本
        """
        return """
          // 删除随机电影历史记录
          function MovieRandom_delete_history(id){
            ajax_post("run_plugin_method", {"plugin_id": 'MovieRandom', 'method': 'delete_random_history', 'tmdb_id': id}, function (ret) {
              $("#movie_random_history_" + id).remove();
            });

          }
        """

    def init_config(self, config: dict = None):
        self.mediaserver = MediaServer()
        self.subscribe = Subscribe()
        self.rsshelper = RssHelper()
        if config:
            self._enable = config.get("enable")
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            self._language = config.get("language")
            self._genres = config.get("genres")
            self._vote = config.get("vote")
            self._date = config.get("date")

        # 停止现有任务
        self.stop_service()

        # 启动定时任务 & 立即运行一次
        if self.get_state() or self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            if self._cron:
                self.info(f"电影随机服务启动，周期：{self._cron}")
                self._scheduler.add_job(self.__random,
                                        CronTrigger.from_crontab(self._cron))
            if self._onlyonce:
                self.info(f"电影随机服务启动，立即运行一次")
                self._scheduler.add_job(self.__random, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())))
                # 关闭一次性开关
                self._onlyonce = False
                self.update_config({
                    "enable": self._enable,
                    "onlyonce": self._onlyonce,
                    "cron": self._cron,
                    "language": self._language,
                    "genres": self._genres,
                    "vote": self._vote,
                    "date": self._date,
                })
            if self._scheduler.get_jobs():
                # 启动服务
                self._scheduler.print_jobs()
                self._scheduler.start()

    def __random(self):
        """
        随机获取一部tmdb电影下载
        """
        params = {}
        if self._date:
            params['primary_release_date.gte'] = f"{self._date}-01-01"
        if self._vote:
            params['vote_average.gte'] = self._vote
        if self._language:
            language_options = ModuleConf.DISCOVER_FILTER_CONF.get("tmdb_movie").get("with_original_language").get(
                "options")
            for m in language_options:
                if m.get('name') == self._language:
                    params['with_original_language'] = m.get('value')
                    break
        if self._genres:
            genres_options = ModuleConf.DISCOVER_FILTER_CONF.get("tmdb_movie").get("with_genres").get("options")
            for m in genres_options:
                if m.get('name') == self._genres:
                    params['with_genres'] = m.get('value')
                    break

        # 查询选择条件下所有页数
        random_max_page = Media().get_tmdb_discover_movies_pages(params=params)
        if random_max_page == 0:
            log.error("当前所选条件下未获取到电影数据，停止随机订阅")
            return

        log.info(f"当前所选条件下获取到电影数据 {random_max_page} 页，开始随机订阅")

        # ['page must be less than or equal to 500']
        if random_max_page > 500:
            random_max_page = 500

        movie_list = []
        retry_time = 0
        try_page = []
        while not movie_list and retry_time < 5:
            page = random.randint(0, random_max_page - 1)

            # 已经试过的页数重新random
            while page in try_page:
                page = random.randint(0, random_max_page - 1)

            # 根据请求参数随机获取一页电影
            movie_list = self.__get_discover(page=page,
                                             params=params)
            self.info(
                f"正在尝试第 {retry_time + 1} 次获取，获取到随机页数 {page} 电影数据 {len(movie_list)} 条，最多尝试5次")
            retry_time = retry_time + 1
            try_page.append(page)

        if not movie_list:
            self.error("已达最大尝试次数，当前条件下未随机到电影")
            return

        # 随机出媒体库不存在的视频
        media_info = self.__random_check(movie_list)
        if not media_info:
            self.warn("本次未随机出满足条件的电影")
            return

        title = media_info.get('title')
        year = media_info.get('year')
        tmdb_id = media_info.get('id')
        unique_flag = f"movierandom: {title} (DB:{tmdb_id})"
        log.info(
            f"电影 {title}-{year}（tmdbid:{tmdb_id}）未入库，开始订阅")

        # 检查是否已订阅过
        if self.subscribe.check_history(
                type_str="MOV",
                name=title,
                year=year,
                season=None):
            self.info(
                f"{title} 已订阅过")
            self.__update_history(media=media_info, state="RSS")
            return
        # 添加处理历史
        self.rsshelper.simple_insert_rss_torrents(title=unique_flag, enclosure=None)
        # 添加订阅
        code, msg, rss_media = self.subscribe.add_rss_subscribe(
            mtype=MediaType.MOVIE,
            name=title,
            year=year,
            season=None,
            channel=RssType.Auto,
            in_from=SearchType.PLUGIN
        )
        if not rss_media or code != 0:
            self.warn("%s 添加订阅失败：%s" % (title, msg))
            # 订阅已存在
            if code == 9:
                self.__update_history(media=media_info, state="RSS")
        else:
            self.info("%s 添加订阅成功" % title)
            # 插入为已RSS状态
            self.__update_history(media=media_info, state="RSS")

    def __random_check(self, movie_list):
        """
        随机一个电影
        检查媒体服务器是否存在
        """
        # 随机一个电影
        media_info = random.choice(movie_list)

        title = media_info.get('title')
        year = media_info.get('year')
        tmdb_id = media_info.get('id')
        unique_flag = f"movierandom: {title} (DB:{tmdb_id})"
        # 检查是否已处理过
        if self.rsshelper.is_rssd_by_simple(torrent_name=unique_flag, enclosure=None):
            self.info(f"已处理过：{title} （tmdbid：{tmdb_id}）")
            return

        log.info(f"随机出电影 {title} {year} tmdbid:{tmdb_id}")
        # 删除该电影，防止再次random到
        movie_list.remove(media_info)

        # 检查媒体服务器是否存在
        item_id = self.mediaserver.check_item_exists(mtype=MediaType.MOVIE,
                                                     title=title,
                                                     year=year,
                                                     tmdbid=tmdb_id)
        if item_id:
            self.info(f"媒体服务器已存在：{title}")
            self.__update_history(media=media_info, state="DOWNLOADED")
            if len(movie_list) == 0:
                return None
            self.__random_check(movie_list)
        return media_info

    def delete_random_history(self, tmdb_id):
        """
        删除同步历史
        """
        return self.delete_history(key=tmdb_id)

    def __update_history(self, media, state):
        """
        插入历史记录
        """
        value = {
            "id": media.get('tmdbid'),
            "name": media.get('title'),
            "year": media.get('year'),
            "type": media.get('media_type'),
            "rating": media.get('vote')[0] if media.get('vote') else None,
            "image": media.get('image'),
            "state": state,
            "add_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if self.get_history(key=media.get('tmdbid')):
            self.update_history(key=media.get('tmdbid'), value=value)
        else:
            self.history(key=media.get('tmdbid'), value=value)

    @staticmethod
    def __get_discover(page, params):
        return Media().get_tmdb_discover(mtype=MediaType.MOVIE,
                                         page=page,
                                         params=params)

    def get_state(self):
        return self._enable \
            and self._cron

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
