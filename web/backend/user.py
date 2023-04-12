from flask_login import UserMixin
from werkzeug.security import check_password_hash

from app.helper import DbHelper
from config import Config
from app.conf import ModuleConf


class User(UserMixin):
	"""
    用户
    """
	dbhelper = None
	admin_users = []
	level = 2
	admin = 1

	def __init__(self, user=None):
		self.dbhelper = DbHelper()
		if user:
			self.id = user.get('id')
			self.username = user.get('name')
			self.password_hash = user.get('password')
			self.pris = user.get('pris')
		self.admin_users = [{
			"id": 0,
			"name": Config().get_config('app').get('login_user'),
			"password": Config().get_config('app').get('login_password')[6:],
			"pris": "我的媒体库,资源搜索,探索,站点管理,订阅管理,下载管理,媒体整理,服务,系统设置"
		}]

	def verify_password(self, password):
		"""
        验证密码
        """
		if self.password_hash is None:
			return False
		return check_password_hash(self.password_hash, password)

	def get_id(self):
		"""
        获取用户ID
        """
		return self.id

	def get(self, user_id):
		"""
        根据用户ID获取用户实体，为 login_user 方法提供支持
        """
		if user_id is None:
			return None
		for user in self.admin_users:
			if user.get('id') == user_id:
				return User(user)
		for user in self.dbhelper.get_users():
			if not user:
				continue
			if user.ID == user_id:
				return User({"id": user.ID, "name": user.NAME, "password": user.PASSWORD, "pris": user.PRIS})
		return None

	def get_user(self, user_name):
		"""
        根据用户名获取用户对像
        """
		for user in self.admin_users:
			if user.get("name") == user_name:
				return User(user)
		for user in self.dbhelper.get_users():
			if user.NAME == user_name:
				return User({"id": user.ID, "name": user.NAME, "password": user.PASSWORD, "pris": user.PRIS})
		return None

	def get_services(self):
		SchedulerTasks = {}
		# RSS订阅
		svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-cloud-download" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                 <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                 <path d="M19 18a3.5 3.5 0 0 0 0 -7h-1a5 4.5 0 0 0 -11 -2a4.6 4.4 0 0 0 -2.1 8.4"></path>
                 <line x1="12" y1="13" x2="12" y2="22"></line>
                 <polyline points="9 19 12 22 15 19"></polyline>
            </svg>
        '''
		SchedulerTasks['rssdownload'] = {'name': 'RSS订阅', 'time': None, 'state': None, 'id': 'rssdownload',
										 'svg': svg,
										 'color': "blue"}

		svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-search" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                <circle cx="10" cy="10" r="7"></circle>
                <line x1="21" y1="21" x2="15" y2="15"></line>
            </svg>
        '''

		SchedulerTasks['subscribe_search_all'] = {'name': '订阅搜索', 'time': None, 'state': None,
												  'id': 'subscribe_search_all',
												  'svg': svg,
												  'color': "blue"}
		# 下载文件转移
		svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-replace" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
             <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
             <rect x="3" y="3" width="6" height="6" rx="1"></rect>
             <rect x="15" y="15" width="6" height="6" rx="1"></rect>
             <path d="M21 11v-3a2 2 0 0 0 -2 -2h-6l3 3m0 -6l-3 3"></path>
             <path d="M3 13v3a2 2 0 0 0 2 2h6l-3 -3m0 6l3 -3"></path>
        </svg>
        '''
		SchedulerTasks['pttransfer'] = {'name': '下载文件转移', 'time': None, 'state': None, 'id': 'pttransfer',
										'svg': svg,
										'color': "green"}
		# 删种
		svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-trash" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                 <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                 <line x1="4" y1="7" x2="20" y2="7"></line>
                 <line x1="10" y1="11" x2="10" y2="17"></line>
                 <line x1="14" y1="11" x2="14" y2="17"></line>
                 <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"></path>
                 <path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"></path>
            </svg>
            '''
		SchedulerTasks['autoremovetorrents'] = {'name': '自动删种', 'state': None,
												'id': 'autoremovetorrents', 'svg': svg, 'color': "twitter"}

		# 自动签到
		svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-user-check" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                 <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                 <circle cx="9" cy="7" r="4"></circle>
                 <path d="M3 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"></path>
                 <path d="M16 11l2 2l4 -4"></path>
            </svg>
            '''
		SchedulerTasks['ptsignin'] = {'name': '站点签到', 'time': None, 'state': None, 'id': 'ptsignin', 'svg': svg,
									  'color': "facebook"}

		# 目录同步
		svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-refresh" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4"></path>
                <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4"></path>
        </svg>
        '''
		SchedulerTasks['sync'] = {'name': '目录同步', 'time': '实时监控', 'state': None, 'id': 'sync', 'svg': svg,
								  'color': "orange"}

		# 清理文件整理缓存
		svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-eraser" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M19 20h-10.5l-4.21 -4.3a1 1 0 0 1 0 -1.41l10 -10a1 1 0 0 1 1.41 0l5 5a1 1 0 0 1 0 1.41l-9.2 9.3"></path>
            <path d="M18 13.3l-6.3 -6.3"></path>
        </svg>
        '''
		SchedulerTasks['blacklist'] = {'name': '清理转移缓存', 'time': '手动', 'state': 'OFF', 'id': 'blacklist',
									   'svg': svg, 'color': 'red'}

		# 清理RSS缓存
		svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-eraser" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
               <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
               <path d="M19 20h-10.5l-4.21 -4.3a1 1 0 0 1 0 -1.41l10 -10a1 1 0 0 1 1.41 0l5 5a1 1 0 0 1 0 1.41l-9.2 9.3"></path>
               <path d="M18 13.3l-6.3 -6.3"></path>
            </svg>
            '''
		SchedulerTasks['rsshistory'] = {'name': '清理RSS缓存', 'time': '手动', 'state': 'OFF', 'id': 'rsshistory',
										'svg': svg, 'color': 'purple'}

		# 名称识别测试
		svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-alphabet-greek" width="40" height="40" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
        <path d="M10 10v7"></path>
        <rect x="5" y="10" width="5" height="7" rx="2"></rect>
        <path d="M14 20v-11a2 2 0 0 1 2 -2h1a2 2 0 0 1 2 2v1a2 2 0 0 1 -2 2a2 2 0 0 1 2 2v1a2 2 0 0 1 -2 2"></path>
        </svg>
        '''
		SchedulerTasks['nametest'] = {'name': '名称识别测试', 'time': '', 'state': 'OFF', 'id': 'nametest', 'svg': svg,
									  'color': 'lime'}

		# 过滤规则测试
		svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-adjustments-horizontal" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
        <circle cx="14" cy="6" r="2"></circle>
        <line x1="4" y1="6" x2="12" y2="6"></line>
        <line x1="16" y1="6" x2="20" y2="6"></line>
        <circle cx="8" cy="12" r="2"></circle>
        <line x1="4" y1="12" x2="6" y2="12"></line>
        <line x1="10" y1="12" x2="20" y2="12"></line>
        <circle cx="17" cy="18" r="2"></circle>
        <line x1="4" y1="18" x2="15" y2="18"></line>
        <line x1="19" y1="18" x2="20" y2="18"></line>
        </svg>
        '''
		SchedulerTasks['ruletest'] = {'name': '过滤规则测试', 'time': '', 'state': 'OFF', 'id': 'ruletest', 'svg': svg,
									  'color': 'yellow'}

		# 备份
		svg = '''
        <svg t="1660720525544" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="1559" width="16" height="16">
        <path d="M646 1024H100A100 100 0 0 1 0 924V258a100 100 0 0 1 100-100h546a100 100 0 0 1 100 100v31a40 40 0 1 1-80 0v-31a20 20 0 0 0-20-20H100a20 20 0 0 0-20 20v666a20 20 0 0 0 20 20h546a20 20 0 0 0 20-20V713a40 40 0 0 1 80 0v211a100 100 0 0 1-100 100z" fill="#ffffff" p-id="1560"></path>
        <path d="M924 866H806a40 40 0 0 1 0-80h118a20 20 0 0 0 20-20V100a20 20 0 0 0-20-20H378a20 20 0 0 0-20 20v8a40 40 0 0 1-80 0v-8A100 100 0 0 1 378 0h546a100 100 0 0 1 100 100v666a100 100 0 0 1-100 100z" fill="#ffffff" p-id="1561"></path>
        <path d="M469 887a40 40 0 0 1-27-10L152 618a40 40 0 0 1 1-60l290-248a40 40 0 0 1 66 30v128a367 367 0 0 0 241-128l94-111a40 40 0 0 1 70 35l-26 109a430 430 0 0 1-379 332v142a40 40 0 0 1-40 40zM240 589l189 169v-91a40 40 0 0 1 40-40c144 0 269-85 323-214a447 447 0 0 1-323 137 40 40 0 0 1-40-40v-83z" fill="#ffffff" p-id="1562"></path>
        </svg>
        '''
		SchedulerTasks['backup'] = {'name': '备份&恢复', 'time': '', 'state': 'OFF', 'id': 'backup', 'svg': svg,
									'color': 'green'}

		# 网络连通性测试
		svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-network" width="40" height="40" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <circle cx="12" cy="9" r="6"></circle>
            <path d="M12 3c1.333 .333 2 2.333 2 6s-.667 5.667 -2 6"></path>
            <path d="M12 3c-1.333 .333 -2 2.333 -2 6s.667 5.667 2 6"></path>
            <path d="M6 9h12"></path>
            <path d="M3 19h7"></path>
            <path d="M14 19h7"></path>
            <circle cx="12" cy="19" r="2"></circle>
            <path d="M12 15v2"></path>
        </svg>
        '''
		targets = ModuleConf.NETTEST_TARGETS
		SchedulerTasks['nettest'] = {'name': '网络连通性测试', 'time': '', 'state': 'OFF', 'id': 'nettest', 'svg': svg,
									 'color': 'cyan',
									 "targets": targets}

		return SchedulerTasks

	@staticmethod
	def check_user(_site, _params):
		"""
        校验用户
        """
		return True, "校验成功"

	def get_authsites(self):
		"""
        获取授权站点信息
        """
		return {}

	def get_usermenus(self):
		"""
        获取用户的可用菜单
        """
		return [
			{
				'name': "我的媒体库",
				'page': "index",
				'icon': """
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-home" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><polyline points="5 12 3 12 12 3 21 12 19 12"></polyline><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7"></path><path d="M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6"></path></svg>
    """,
			},
			{
				'name': "探索",
				'list': [
					{
						'name': "榜单推荐",
						'page': "ranking",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/align-box-bottom-center.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-align-box-bottom-center" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M4 4m0 2a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2z"></path>
            <path d="M9 15v2"></path>
            <path d="M12 11v6"></path>
            <path d="M15 13v4"></path>
          </svg>
        """,
					},
					{
						'name': "豆瓣电影",
						'page': "douban_movie",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/movie.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-movie" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M4 4m0 2a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2z"></path>
            <path d="M8 4l0 16"></path>
            <path d="M16 4l0 16"></path>
            <path d="M4 8l4 0"></path>
            <path d="M4 16l4 0"></path>
            <path d="M4 12l16 0"></path>
            <path d="M16 8l4 0"></path>
            <path d="M16 16l4 0"></path>
          </svg>
        """,
					},
					{
						'name': "豆瓣电视剧",
						'page': "douban_tv",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/device-tv.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-device-tv" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M3 7m0 2a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v9a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2z"></path>
            <path d="M16 3l-4 4l-4 -4"></path>
          </svg>
        """,
					},
					{
						'name': "TMDB电影",
						'page': "tmdb_movie",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/movie.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-movie" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M4 4m0 2a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2z"></path>
            <path d="M8 4l0 16"></path>
            <path d="M16 4l0 16"></path>
            <path d="M4 8l4 0"></path>
            <path d="M4 16l4 0"></path>
            <path d="M4 12l16 0"></path>
            <path d="M16 8l4 0"></path>
            <path d="M16 16l4 0"></path>
          </svg>
        """,
					},
					{
						'name': "TMDB电视剧",
						'page': "tmdb_tv",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/device-tv.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-device-tv" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M3 7m0 2a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v9a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2z"></path>
            <path d="M16 3l-4 4l-4 -4"></path>
          </svg>
        """,
					},
					{
						'name': "BANGUMI",
						'page': "bangumi",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/device-tv-old.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-device-tv-old" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
             <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
             <path d="M3 7m0 2a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v9a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2z"></path>
             <path d="M16 3l-4 4l-4 -4"></path>
             <path d="M15 7v13"></path>
             <path d="M18 15v.01"></path>
             <path d="M18 12v.01"></path>
          </svg>
        """,
					},
				],
			},
			{
				'name': "资源搜索",
				'page': "search",
				'icon': """
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-search" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><circle cx="10" cy="10" r="7"></circle><line x1="21" y1="21" x2="15" y2="15"></line></svg>
    """,
			},
			{
				'name': "站点管理",
				'list': [
					{
						'name': "站点维护",
						'page': "site",
						'icon': """
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-server-2" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><rect x="3" y="4" width="18" height="8" rx="3"></rect><rect x="3" y="12" width="18" height="8" rx="3"></rect><line x1="7" y1="8" x2="7" y2="8.01"></line><line x1="7" y1="16" x2="7" y2="16.01"></line><path d="M11 8h6"></path><path d="M11 16h6"></path></svg>
        """,
					},
					{
						'name': "数据统计",
						'page': "statistics",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/chart-pie.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-chart-pie" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
             <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
             <path d="M10 3.2a9 9 0 1 0 10.8 10.8a1 1 0 0 0 -1 -1h-6.8a2 2 0 0 1 -2 -2v-7a.9 .9 0 0 0 -1 -.8"></path>
             <path d="M15 3.5a9 9 0 0 1 5.5 5.5h-4.5a1 1 0 0 1 -1 -1v-4.5"></path>
          </svg>
        """,
					},
					{
						'name': "刷流任务",
						'page': "brushtask",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/checklist.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-checklist" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M9.615 20h-2.615a2 2 0 0 1 -2 -2v-12a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8"></path>
            <path d="M14 19l2 2l4 -4"></path>
            <path d="M9 8h4"></path>
            <path d="M9 12h2"></path>
          </svg>
        """,
					},
					{
						'name': "站点资源",
						'page': "sitelist",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/cloud-computing.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-cloud-computing" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M6.657 16c-2.572 0 -4.657 -2.007 -4.657 -4.483c0 -2.475 2.085 -4.482 4.657 -4.482c.393 -1.762 1.794 -3.2 3.675 -3.773c1.88 -.572 3.956 -.193 5.444 1c1.488 1.19 2.162 3.007 1.77 4.769h.99c1.913 0 3.464 1.56 3.464 3.486c0 1.927 -1.551 3.487 -3.465 3.487h-11.878"></path>
            <path d="M12 16v5"></path>
            <path d="M16 16v4a1 1 0 0 0 1 1h4"></path>
            <path d="M8 16v4a1 1 0 0 1 -1 1h-4"></path>
          </svg>
        """,
					},
				],
			},
			{
				'name': "订阅管理",
				'list': [
					{
						'name': "电影订阅",
						'page': "movie_rss",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/movie.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-movie" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M4 4m0 2a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2z"></path>
            <path d="M8 4l0 16"></path>
            <path d="M16 4l0 16"></path>
            <path d="M4 8l4 0"></path>
            <path d="M4 16l4 0"></path>
            <path d="M4 12l16 0"></path>
            <path d="M16 8l4 0"></path>
            <path d="M16 16l4 0"></path>
          </svg>
        """,
					},
					{
						'name': "电视剧订阅",
						'page': "tv_rss",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/device-tv.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-device-tv" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M3 7m0 2a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v9a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2z"></path>
            <path d="M16 3l-4 4l-4 -4"></path>
          </svg>
        """,
					},
					{
						'name': "自定义订阅",
						'page': "user_rss",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/file-rss.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-file-rss" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
            <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z"></path>
            <path d="M12 17a3 3 0 0 0 -3 -3"></path>
            <path d="M15 17a6 6 0 0 0 -6 -6"></path>
            <path d="M9 17h.01"></path>
          </svg>
        """,
					},
					{
						'name': "订阅日历",
						'page': "rss_calendar",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/calendar.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-calendar" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M4 5m0 2a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2z"></path>
            <path d="M16 3l0 4"></path>
            <path d="M8 3l0 4"></path>
            <path d="M4 11l16 0"></path>
            <path d="M11 15l1 0"></path>
            <path d="M12 15l0 3"></path>
          </svg>
        """,
					},
				],
			},
			{
				'name': "下载管理",
				'list': [
					{
						'name': "正在下载",
						'page': "downloading",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/loader.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-loader" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M12 6l0 -3"></path>
            <path d="M16.25 7.75l2.15 -2.15"></path>
            <path d="M18 12l3 0"></path>
            <path d="M16.25 16.25l2.15 2.15"></path>
            <path d="M12 18l0 3"></path>
            <path d="M7.75 16.25l-2.15 2.15"></path>
            <path d="M6 12l-3 0"></path>
            <path d="M7.75 7.75l-2.15 -2.15"></path>
          </svg>
        """,
					},
					{
						'name': "近期下载",
						'page': "downloaded",
						'icon': """
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-download" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"></path><polyline points="7 11 12 16 17 11"></polyline><line x1="12" y1="4" x2="12" y2="16"></line></svg>
        """,
					},
					{
						'name': "自动删种",
						'page': "torrent_remove",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/download-off.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-download-off" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 1.83 -1.19"></path>
            <path d="M7 11l5 5l2 -2m2 -2l1 -1"></path>
            <path d="M12 4v4m0 4v4"></path>
            <path d="M3 3l18 18"></path>
          </svg>
        """,
					},
				],
			},
			{
				'name': "媒体整理",
				'list': [
					{
						'name': "文件管理",
						'page': "mediafile",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/file-pencil.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-file-pencil" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M14 3v4a1 1 0 0 0 1 1h4"></path>
            <path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z"></path>
            <path d="M10 18l5 -5a1.414 1.414 0 0 0 -2 -2l-5 5v2h2z"></path>
          </svg>
        """,
					},
					{
						'name': "手动识别",
						'page': "unidentification",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/accessible.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-accessible" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"></path>
            <path d="M10 16.5l2 -3l2 3m-2 -3v-2l3 -1m-6 0l3 1"></path>
            <circle cx="12" cy="7.5" r=".5" fill="currentColor"></circle>
          </svg>
        """,
					},
					{
						'name': "历史记录",
						'page': "history",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/history.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-history" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M12 8l0 4l2 2"></path>
            <path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5"></path>
          </svg>
        """,
					},
					{
						'name': "TMDB缓存",
						'page': "tmdbcache",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/brand-headlessui.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-brand-headlessui" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M6.744 4.325l7.82 -1.267a4.456 4.456 0 0 1 5.111 3.686l1.267 7.82a4.456 4.456 0 0 1 -3.686 5.111l-7.82 1.267a4.456 4.456 0 0 1 -5.111 -3.686l-1.267 -7.82a4.456 4.456 0 0 1 3.686 -5.111z"></path>
            <path d="M7.252 7.704l7.897 -1.28a1 1 0 0 1 1.147 .828l.36 2.223l-9.562 3.51l-.67 -4.134a1 1 0 0 1 .828 -1.147z"></path>
          </svg>
        """,
					},
				],
			},
			{
				'name': "服务",
				'page': "service",
				'icon': """
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-layout-2" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><rect x="4" y="4" width="6" height="5" rx="2"></rect><rect x="4" y="13" width="6" height="7" rx="2"></rect><rect x="14" y="4" width="6" height="7" rx="2"></rect><rect x="14" y="15" width="6" height="5" rx="2"></rect></svg>
    """,
			},
			{
				'name': "系统设置",
				'also': "设置",
				'list': [
					{
						'name': "基础设置",
						'page': "basic",
						'icon': """
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-settings" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><path d="M10.325 4.317c.426 -1.756 2.924 -1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543 -.94 3.31 .826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756 .426 1.756 2.924 0 3.35a1.724 1.724 0 0 0 -1.066 2.573c.94 1.543 -.826 3.31 -2.37 2.37a1.724 1.724 0 0 0 -2.572 1.065c-.426 1.756 -2.924 1.756 -3.35 0a1.724 1.724 0 0 0 -2.573 -1.066c-1.543 .94 -3.31 -.826 -2.37 -2.37a1.724 1.724 0 0 0 -1.065 -2.572c-1.756 -.426 -1.756 -2.924 0 -3.35a1.724 1.724 0 0 0 1.066 -2.573c-.94 -1.543 .826 -3.31 2.37 -2.37c1 .608 2.296 .07 2.572 -1.065z"></path><circle cx="12" cy="12" r="3"></circle></svg>
        """,
					},
					{
						'name': "媒体库",
						'page': "library",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/stereo-glasses.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-stereo-glasses" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M8 3h-2l-3 9"></path>
            <path d="M16 3h2l3 9"></path>
            <path d="M3 12v7a1 1 0 0 0 1 1h4.586a1 1 0 0 0 .707 -.293l2 -2a1 1 0 0 1 1.414 0l2 2a1 1 0 0 0 .707 .293h4.586a1 1 0 0 0 1 -1v-7h-18z"></path>
            <path d="M7 16h1"></path>
            <path d="M16 16h1"></path>
          </svg>
        """,
					},
					{
						'name': "目录同步",
						'page': "directorysync",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/refresh.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-refresh" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4"></path>
            <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4"></path>
          </svg>
        """,
					},
					{
						'name': "消息通知",
						'page': "notification",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/bell.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-bell" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M10 5a2 2 0 0 1 4 0a7 7 0 0 1 4 6v3a4 4 0 0 0 2 3h-16a4 4 0 0 0 2 -3v-3a7 7 0 0 1 4 -6"></path>
            <path d="M9 17v1a3 3 0 0 0 6 0v-1"></path>
          </svg>
        """,
					},
					{
						'name': "过滤规则",
						'page': "filterrule",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/filter.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-filter" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M5.5 5h13a1 1 0 0 1 .5 1.5l-5 5.5l0 7l-4 -3l0 -4l-5 -5.5a1 1 0 0 1 .5 -1.5"></path>
          </svg>
        """,
					},
					{
						'name': "自定义识别词",
						'page': "customwords",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/a-b.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-a-b" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M3 16v-5.5a2.5 2.5 0 0 1 5 0v5.5m0 -4h-5"></path>
            <path d="M12 6l0 12"></path>
            <path d="M16 16v-8h3a2 2 0 0 1 0 4h-3m3 0a2 2 0 0 1 0 4h-3"></path>
          </svg>
        """,
					},
					{
						'name': "索引器",
						'page': "indexer",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/list-search.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-list-search" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M15 15m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0"></path>
            <path d="M18.5 18.5l2.5 2.5"></path>
            <path d="M4 6h16"></path>
            <path d="M4 12h4"></path>
            <path d="M4 18h4"></path>
          </svg>
        """,
					},
					{
						'name': "下载器",
						'page': "downloader",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/download.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-download" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"></path>
            <path d="M7 11l5 5l5 -5"></path>
            <path d="M12 4l0 12"></path>
          </svg>
        """,
					},
					{
						'name': "媒体服务器",
						'page': "mediaserver",
						'icon': """
          <!-- https://tabler-icons.io/static/tabler-icons/icons-png/server-cog.png -->
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-server-cog" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M3 4m0 3a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v2a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3z"></path>
            <path d="M12 20h-6a3 3 0 0 1 -3 -3v-2a3 3 0 0 1 3 -3h10.5"></path>
            <path d="M18 18m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"></path>
            <path d="M18 14.5v1.5"></path>
            <path d="M18 20v1.5"></path>
            <path d="M21.032 16.25l-1.299 .75"></path>
            <path d="M16.27 19l-1.3 .75"></path>
            <path d="M14.97 16.25l1.3 .75"></path>
            <path d="M19.733 19l1.3 .75"></path>
            <path d="M7 8v.01"></path>
            <path d="M7 16v.01"></path>
          </svg>
        """,
					},
					{
						'name': "插件",
						'page': "plugin",
						'icon': """
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-brand-codesandbox" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                                 <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                                 <path d="M20 7.5v9l-4 2.25l-4 2.25l-4 -2.25l-4 -2.25v-9l4 -2.25l4 -2.25l4 2.25z"></path>
                                 <path d="M12 12l4 -2.25l4 -2.25"></path>
                                 <path d="M12 12l0 9"></path>
                                 <path d="M12 12l-4 -2.25l-4 -2.25"></path>
                                 <path d="M20 12l-4 2v4.75"></path>
                                 <path d="M4 12l4 2l0 4.75"></path>
                                 <path d="M8 5.25l4 2.25l4 -2.25"></path>
                              </svg>
        """,
					},
				],
			},
		]
