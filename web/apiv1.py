from flask import Blueprint, request
from flask_restx import Api, reqparse, Resource

from app.sites import Sites
from app.utils import TokenCache
from config import Config
from web.action import WebAction
from web.backend.user import User
from web.security import require_auth, login_required, generate_access_token

apiv1_bp = Blueprint("apiv1",
                     __name__,
                     static_url_path='',
                     static_folder='./frontend/static/',
                     template_folder='./frontend/', )
Apiv1 = Api(apiv1_bp,
            version="1.0",
            title="NAStool Api",
            description="",
            doc="/",
            security='Bearer Auth',
            authorizations={"Bearer Auth": {"type": "apiKey", "name": "Authorization", "in": "header"}},
            )
# API分组
user = Apiv1.namespace('user', description='用户')
system = Apiv1.namespace('system', description='系统')
config = Apiv1.namespace('config', description='设置')
site = Apiv1.namespace('site', description='站点')
service = Apiv1.namespace('service', description='服务')
subscribe = Apiv1.namespace('subscribe', description='订阅')
rss = Apiv1.namespace('rss', description='RSS')
recommend = Apiv1.namespace('recommend', description='推荐')
search = Apiv1.namespace('search', description='搜索')
download = Apiv1.namespace('download', description='下载')
organization = Apiv1.namespace('organization', description='整理')
brushtask = Apiv1.namespace('brushtask', description='刷流')
media = Apiv1.namespace('media', description='媒体')
sync = Apiv1.namespace('sync', description='目录同步')
filterrule = Apiv1.namespace('filterrule', description='过滤规则')
words = Apiv1.namespace('words', description='识别词')


class ApiResource(Resource):
    """
    API 认证
    """
    method_decorators = [require_auth]


class ClientResource(Resource):
    """
    登录认证
    """
    method_decorators = [login_required]


@user.route('/login')
class UserLogin(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('username', type=str, help='用户名', location='form', required=True)
    parser.add_argument('password', type=str, help='密码', location='form', required=True)

    @user.doc(parser=parser)
    def post(self):
        """
        用户登录
        """
        args = self.parser.parse_args()
        username = args.get('username')
        password = args.get('password')
        if not username or not password:
            return {"code": 1, "success": False, "message": "用户名或密码错误"}
        user_info = User().get_user(username)
        if not user_info:
            return {"code": 1, "success": False, "message": "用户名或密码错误"}
        # 校验密码
        if not user_info.verify_password(password):
            return {"code": 1, "success": False, "message": "用户名或密码错误"}
        # 缓存Token
        token = generate_access_token(username)
        TokenCache.set(token, token)
        return {
            "code": 0,
            "success": True,
            "data": {
                "token": token,
                "apikey": Config().get_config("security").get("api_key"),
                "userinfo": {
                    "userid": user_info.id,
                    "username": user_info.username,
                    "userpris": str(user_info.pris).split(",")
                }
            }
        }


@user.route('/info')
class UserInfo(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('username', type=str, help='用户名', location='form', required=True)

    @user.doc(parser=parser)
    def post(self):
        """
        获取用户信息
        """
        args = self.parser.parse_args()
        username = args.get('username')
        user_info = User().get_user(username)
        if not user_info:
            return {"code": 1, "success": False, "message": "用户名不正确"}
        return {
            "code": 0,
            "success": True,
            "data": {
                "userid": user_info.id,
                "username": user_info.username,
                "userpris": str(user_info.pris).split(",")
            }
        }


@user.route('/manage')
class UserManage(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('oper', type=str, help='操作类型（add 新增、del删除）', location='form', required=True)
    parser.add_argument('name', type=str, help='用户名', location='form', required=True)
    parser.add_argument('pris', type=str, help='权限', location='form')

    @user.doc(parser=parser)
    def post(self):
        """
        用户管理
        """
        return WebAction().api_action(cmd='user_manager', data=self.parser.parse_args())


@service.route('/mediainfo')
class ServiceMediaInfo(ApiResource):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str, help='名称', location='args', required=True)

    @service.doc(parser=parser)
    def get(self):
        """
        识别媒体信息（密钥认证）
        """
        return WebAction().api_action(cmd='name_test', data=self.parser.parse_args())


@service.route('/name/test')
class ServiceNameTest(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str, help='名称', location='form', required=True)

    @service.doc(parser=parser)
    def post(self):
        """
        名称识别测试
        """
        return WebAction().api_action(cmd='name_test', data=self.parser.parse_args())


@service.route('/rule/test')
class ServiceRuleTest(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('title', type=str, help='名称', location='form', required=True)
    parser.add_argument('subtitle', type=str, help='描述', location='form')
    parser.add_argument('size', type=float, help='大小（GB）', location='form')

    @service.doc(parser=parser)
    def post(self):
        """
        过滤规则测试
        """
        return WebAction().api_action(cmd='rule_test', data=self.parser.parse_args())


@service.route('/network/test')
class ServiceNetworkTest(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('url', type=str, help='URL地址', location='form', required=True)

    @service.doc(parser=parser)
    def post(self):
        """
        网络连接性测试
        """
        return WebAction().api_action(cmd='net_test', data=self.parser.parse_args().get("url"))


@service.route('/run')
class ServiceRun(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('item', type=str, help='服务ID', location='form', required=True)

    @service.doc(parser=parser)
    def post(self):
        """
        运行服务
        """
        return WebAction().api_action(cmd='sch', data=self.parser.parse_args())


@site.route('/statistics')
class SiteStatistic(ApiResource):
    @staticmethod
    def get():
        """
        获取站点数据明细（密钥认证）
        """
        # 返回站点信息
        return {
            "code": 0,
            "success": True,
            "data": {
                "user_statistics": Sites().get_site_user_statistics(encoding="DICT")
            }
        }


@site.route('/sites')
class SiteSites(ApiResource):
    @staticmethod
    def get():
        """
        获取所有站点配置（密钥认证）
        """
        return {
            "code": 0,
            "success": True,
            "data": {
                "user_sites": Sites().get_sites()
            }
        }


@site.route('/update')
class SiteUpdate(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('site_name', type=str, help='站点名称', location='form', required=True)
    parser.add_argument('site_id', type=int, help='更新站点ID', location='form')
    parser.add_argument('site_pri', type=str, help='优先级', location='form')
    parser.add_argument('site_rssurl', type=str, help='RSS地址', location='form')
    parser.add_argument('site_signurl', type=str, help='站点地址', location='form')
    parser.add_argument('site_cookie', type=str, help='Cookie', location='form')
    parser.add_argument('site_note', type=str, help='站点属性', location='form')
    parser.add_argument('site_include', type=str, help='站点用途', location='form')

    @site.doc(parser=parser)
    def post(self):
        """
        新增/删除站点
        """
        return WebAction().api_action(cmd='update_site', data=self.parser.parse_args())


@site.route('/info')
class SiteInfo(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=int, help='站点ID', location='form', required=True)

    @site.doc(parser=parser)
    def post(self):
        """
        查询单个站点详情
        """
        return WebAction().api_action(cmd='get_site', data=self.parser.parse_args())


@site.route('/delete')
class SiteDelete(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=int, help='站点ID', location='form', required=True)

    @site.doc(parser=parser)
    def post(self):
        """
        删除站点
        """
        return WebAction().api_action(cmd='del_site', data=self.parser.parse_args())


@site.route('/statistics/activity')
class SiteStatisticsActivity(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str, help='站点名称', location='form', required=True)

    @site.doc(parser=parser)
    def post(self):
        """
        查询站点 上传、下载、做种数据
        """
        return WebAction().api_action(cmd='get_site_activity', data=self.parser.parse_args())


@site.route('/check')
class SiteCheck(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('url', type=str, help='站点地址', location='form', required=True)

    @site.doc(parser=parser)
    def post(self):
        """
        检查站点是否支持FREE、HR检测
        """
        return WebAction().api_action(cmd='check_site_attr', data=self.parser.parse_args())


@site.route('/statistics/history')
class SiteStatisticsHistory(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('days', type=int, help='时间范围（天）', location='form', required=True)

    @site.doc(parser=parser)
    def post(self):
        """
        查询所有站点历史数据
        """
        return WebAction().api_action(cmd='get_site_history', data=self.parser.parse_args())


@site.route('/statistics/seedinfo')
class SiteStatisticsSeedinfo(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str, help='站点名称', location='form', required=True)

    @site.doc(parser=parser)
    def post(self):
        """
        查询站点做种分布
        """
        return WebAction().api_action(cmd='get_site_seeding_info', data=self.parser.parse_args())


@site.route('/resources')
class SiteResources(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=str, help='站点索引ID', location='form', required=True)
    parser.add_argument('page', type=int, help='页码', location='form')
    parser.add_argument('keyword', type=str, help='站点名称', location='form')

    @site.doc(parser=parser)
    def post(self):
        """
        查询站点资源列表
        """
        return WebAction().api_action(cmd='list_site_resources', data=self.parser.parse_args())


@search.route('/keyword')
class SearchKeyword(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('search_word', type=str, help='搜索关键字', location='form', required=True)
    parser.add_argument('unident', type=bool, help='快速模式', location='form')
    parser.add_argument('filters', type=str, help='过滤条件', location='form')
    parser.add_argument('tmdbid', type=str, help='TMDBID', location='form')
    parser.add_argument('media_type', type=str, help='类型（电影/电视剧）', location='form')

    @search.doc(parser=parser)
    def post(self):
        """
        根据关键字/TMDBID搜索
        """
        return WebAction().api_action(cmd='search', data=self.parser.parse_args())


@download.route('/search')
class DownloadSearch(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=str, help='搜索结果ID', location='form', required=True)
    parser.add_argument('dir', type=str, help='下载目录', location='form')

    @download.doc(parser=parser)
    def post(self):
        """
        下载搜索结果
        """
        return WebAction().api_action(cmd='download', data=self.parser.parse_args())


@download.route('/item')
class DownloadItem(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('enclosure', type=str, help='链接URL', location='form', required=True)
    parser.add_argument('title', type=str, help='标题', location='form', required=True)
    parser.add_argument('site', type=str, help='站点名称', location='form')
    parser.add_argument('description', type=str, help='描述', location='form')
    parser.add_argument('page_url', type=str, help='详情页面URL', location='form')
    parser.add_argument('size', type=str, help='大小', location='form')
    parser.add_argument('seeders', type=str, help='做种数', location='form')
    parser.add_argument('uploadvolumefactor', type=float, help='上传因子', location='form')
    parser.add_argument('downloadvolumefactor', type=float, help='下载因子', location='form')
    parser.add_argument('dl_dir', type=str, help='保存目录', location='form')

    @download.doc(parser=parser)
    def post(self):
        """
        下载链接
        """
        return WebAction().api_action(cmd='download_link', data=self.parser.parse_args())


@download.route('/start')
class DownloadStart(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=str, help='任务ID', location='form', required=True)

    @download.doc(parser=parser)
    def post(self):
        """
        开始下载任务
        """
        return WebAction().api_action(cmd='pt_start', data=self.parser.parse_args())


@download.route('/stop')
class DownloadStop(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=str, help='任务ID', location='form', required=True)

    @download.doc(parser=parser)
    def post(self):
        """
        暂停下载任务
        """
        return WebAction().api_action(cmd='pt_stop', data=self.parser.parse_args())


@download.route('/info')
class DownloadInfo(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('ids', type=str, help='任务IDS', location='form', required=True)

    @download.doc(parser=parser)
    def post(self):
        """
        查询下载进度
        """
        return WebAction().api_action(cmd='pt_info', data=self.parser.parse_args())


@download.route('/remove')
class DownloadRemove(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=str, help='任务ID', location='form', required=True)

    @download.doc(parser=parser)
    def post(self):
        """
        删除下载任务
        """
        return WebAction().api_action(cmd='pt_remove', data=self.parser.parse_args())


@download.route('/history')
class DownloadHistory(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('page', type=str, help='第几页', location='form', required=True)

    @download.doc(parser=parser)
    def post(self):
        """
        查询下载历史
        """
        return WebAction().api_action(cmd='get_downloaded', data=self.parser.parse_args())


@organization.route('/unknown/delete')
class UnknownDelete(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=str, help='未识别记录ID', location='form', required=True)

    @organization.doc(parser=parser)
    def post(self):
        """
        删除未识别记录
        """
        return WebAction().api_action(cmd='del_unknown_path', data=self.parser.parse_args())


@organization.route('/unknown/rename')
class UnknownRename(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('logid', type=str, help='转移历史记录ID', location='form')
    parser.add_argument('unknown_id', type=str, help='未识别记录ID', location='form')
    parser.add_argument('syncmod', type=str, help='转移模式', location='form', required=True)
    parser.add_argument('tmdb', type=int, help='TMDB ID', location='form')
    parser.add_argument('title', type=str, help='标题', location='form')
    parser.add_argument('year', type=str, help='年份', location='form')
    parser.add_argument('type', type=str, help='类型（MOV/TV/ANIME）', location='form')
    parser.add_argument('season', type=int, help='季号', location='form')
    parser.add_argument('episode_format', type=str, help='集数定位', location='form')
    parser.add_argument('min_filesize', type=int, help='最小文件大小', location='form')

    @organization.doc(parser=parser)
    def post(self):
        """
        手动识别
        """
        return WebAction().api_action(cmd='rename', data=self.parser.parse_args())


@organization.route('/unknown/renameudf')
class UnknownRenameUDF(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('inpath', type=str, help='源目录', location='form', required=True)
    parser.add_argument('outpath', type=str, help='目的目录', location='form', required=True)
    parser.add_argument('syncmod', type=str, help='转移模式', location='form', required=True)
    parser.add_argument('tmdb', type=int, help='TMDB ID', location='form')
    parser.add_argument('title', type=str, help='标题', location='form')
    parser.add_argument('year', type=str, help='年份', location='form')
    parser.add_argument('type', type=str, help='类型（MOV/TV/ANIME）', location='form')
    parser.add_argument('season', type=int, help='季号', location='form')
    parser.add_argument('episode_format', type=str, help='集数定位', location='form')
    parser.add_argument('episode_details', type=str, help='集数范围', location='form')
    parser.add_argument('episode_offset', type=str, help='集数偏移', location='form')
    parser.add_argument('min_filesize', type=int, help='最小文件大小', location='form')

    @organization.doc(parser=parser)
    def post(self):
        """
        自定义识别
        """
        return WebAction().api_action(cmd='rename_udf', data=self.parser.parse_args())


@organization.route('/unknown/redo')
class UnknownRedo(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('flag', type=str, help='类型（unknow/history）', location='form', required=True)
    parser.add_argument('ids', type=list, help='记录ID', location='form', required=True)

    @organization.doc(parser=parser)
    def post(self):
        """
        重新识别
        """
        return WebAction().api_action(cmd='re_identification', data=self.parser.parse_args())


@organization.route('/history/delete')
class TransferHistoryDelete(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('logids', type=list, help='记录IDS', location='form', required=True)

    @organization.doc(parser=parser)
    def post(self):
        """
        删除媒体整理历史记录
        """
        return WebAction().api_action(cmd='delete_history', data=self.parser.parse_args())


@organization.route('/library/start')
class MediaLibraryStart(ClientResource):

    @staticmethod
    def post():
        """
        开始媒体库同步
        """
        return WebAction().api_action(cmd='start_mediasync')


@organization.route('/cache/empty')
class TransferCacheEmpty(ClientResource):

    @staticmethod
    def post():
        """
        清空文件转移缓存
        """
        return WebAction().api_action(cmd='mediasync_state')


@organization.route('/library/status')
class MediaLibraryStart(ClientResource):

    @staticmethod
    def post():
        """
        查询媒体库同步状态
        """
        return WebAction().api_action(cmd='truncate_blacklist')


@system.route('/logging')
class SystemLogging(ClientResource):

    @staticmethod
    def post():
        """
        获取实时日志
        """
        return WebAction().api_action(cmd='logging')


@system.route('/version')
class SystemVersion(ClientResource):

    @staticmethod
    def post():
        """
        查询最新版本号
        """
        return WebAction().api_action(cmd='version')


@system.route('/restart')
class SystemRestart(ClientResource):

    @staticmethod
    def post():
        """
        重启
        """
        return WebAction().api_action(cmd='restart')


@system.route('/update')
class SystemUpdate(ClientResource):

    @staticmethod
    def post():
        """
        更新
        """
        return WebAction().api_action(cmd='update_system')


@system.route('/logout')
class SystemUpdate(ClientResource):

    @staticmethod
    def post():
        """
        注销
        """
        token = request.headers.get("Authorization", default=None)
        if token:
            TokenCache.delete(token)
        return {
            "code": 0,
            "success": True
        }


@system.route('/message')
class SystemMessage(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('lst_time', type=str, help='时间（YYYY-MM-DD HH24:MI:SS）', location='form')

    @system.doc(parser=parser)
    def post(self):
        """
        查询消息中心消息
        """
        return WebAction().get_system_message(lst_time=self.parser.parse_args().get("lst_time"))


@system.route('/progress')
class SystemProgress(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('type', type=str, help='类型（search/mediasync）', location='form', required=True)

    @system.doc(parser=parser)
    def post(self):
        """
        查询搜索/媒体同步等进度
        """
        return WebAction().api_action(cmd='refresh_process', data=self.parser.parse_args())


@config.route('/update')
class ConfigUpdate(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('items', type=dict, help='配置项', location='form', required=True)

    def post(self):
        """
        新增/修改配置
        """
        return WebAction().api_action(cmd='update_config', data=self.parser.parse_args().get("items"))


@config.route('/test')
class ConfigTest(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('command', type=str, help='测试命令', location='form', required=True)

    @config.doc(parser=parser)
    def post(self):
        """
        测试配置连通性
        """
        return WebAction().api_action(cmd='test_connection', data=self.parser.parse_args())


@config.route('/restore')
class ConfigRestore(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('file_name', type=str, help='备份文件名', location='form', required=True)

    @config.doc(parser=parser)
    def post(self):
        """
        恢复备份的配置
        """
        return WebAction().api_action(cmd='restory_backup', data=self.parser.parse_args())


@subscribe.route('/delete')
class SubscribeDelete(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str, help='名称', location='form')
    parser.add_argument('type', type=str, help='类型（MOV、TV）', location='form')
    parser.add_argument('year', type=str, help='发行年份', location='form')
    parser.add_argument('season', type=int, help='季号', location='form')
    parser.add_argument('rssid', type=int, help='已有订阅ID', location='form')
    parser.add_argument('tmdbid', type=str, help='TMDBID', location='form')

    @subscribe.doc(parser=parser)
    def post(self):
        """
        删除订阅
        """
        return WebAction().api_action(cmd='remove_rss_media', data=self.parser.parse_args())


@subscribe.route('/add')
class SubscribeAdd(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str, help='名称', location='form', required=True)
    parser.add_argument('type', type=str, help='类型（MOV、TV）', location='form', required=True)
    parser.add_argument('year', type=str, help='发行年份', location='form')
    parser.add_argument('season', type=int, help='季号', location='form')
    parser.add_argument('rssid', type=int, help='已有订阅ID', location='form')
    parser.add_argument('tmdbid', type=str, help='TMDBID', location='form')
    parser.add_argument('doubanid', type=str, help='豆瓣ID', location='form')
    parser.add_argument('match', type=bool, help='模糊匹配', location='form')
    parser.add_argument('sites', type=list, help='RSS站点', location='form')
    parser.add_argument('search_sites', type=list, help='搜索站点', location='form')
    parser.add_argument('over_edition', type=bool, help='洗版', location='form')
    parser.add_argument('rss_restype', type=str, help='资源类型', location='form')
    parser.add_argument('rss_pix', type=str, help='分辨率', location='form')
    parser.add_argument('rss_team', type=str, help='字幕组/发布组', location='form')
    parser.add_argument('rss_rule', type=str, help='过滤规则', location='form')
    parser.add_argument('total_ep', type=int, help='总集数', location='form')
    parser.add_argument('current_ep', type=int, help='开始集数', location='form')

    @subscribe.doc(parser=parser)
    def post(self):
        """
        新增/修改订阅
        """
        return WebAction().api_action(cmd='add_rss_media', data=self.parser.parse_args())


@subscribe.route('/movie/date')
class SubscribeMovieDate(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=str, help='TMDBID/DB:豆瓣ID', location='form', required=True)

    @subscribe.doc(parser=parser)
    def post(self):
        """
        电影上映日期
        """
        return WebAction().api_action(cmd='movie_calendar_data', data=self.parser.parse_args())


@subscribe.route('/tv/date')
class SubscribeTVDate(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=str, help='TMDBID/DB:豆瓣ID', location='form', required=True)
    parser.add_argument('season', type=int, help='季号', location='form', required=True)
    parser.add_argument('name', type=str, help='名称', location='form')

    @subscribe.doc(parser=parser)
    def post(self):
        """
        电视剧上映日期
        """
        return WebAction().api_action(cmd='tv_calendar_data', data=self.parser.parse_args())


@subscribe.route('/search')
class SubscribeSearch(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('type', type=str, help='类型（MOV、TV）', location='form', required=True)
    parser.add_argument('rssid', type=int, help='订阅ID', location='form', required=True)

    @subscribe.doc(parser=parser)
    def post(self):
        """
        订阅搜索
        """
        return WebAction().api_action(cmd='refresh_rss', data=self.parser.parse_args())


@subscribe.route('/info')
class SubscribeInfo(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('rssid', type=int, help='订阅ID', location='form', required=True)
    parser.add_argument('type', type=str, help='订阅类型（MOV、TV）', location='form', required=True)

    @subscribe.doc(parser=parser)
    def post(self):
        """
        订阅详情
        """
        return WebAction().api_action(cmd='rss_detail', data=self.parser.parse_args())


@subscribe.route('/redo')
class SubscribeRedo(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('rssid', type=int, help='订阅历史ID', location='form', required=True)
    parser.add_argument('type', type=str, help='订阅类型（MOV、TV）', location='form', required=True)

    @subscribe.doc(parser=parser)
    def post(self):
        """
        历史重新订阅
        """
        return WebAction().api_action(cmd='re_rss_history', data=self.parser.parse_args())


@subscribe.route('/history/delete')
class SubscribeHistoryDelete(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('rssid', type=int, help='订阅ID', location='form', required=True)

    @subscribe.doc(parser=parser)
    def post(self):
        """
        删除订阅历史
        """
        return WebAction().api_action(cmd='delete_rss_history', data=self.parser.parse_args())


@subscribe.route('/cache/delete')
class SubscribeCacheDelete(ClientResource):
    @staticmethod
    def post():
        """
        清理订阅缓存
        """
        return WebAction().api_action(cmd='truncate_rsshistory')


@recommend.route('/list')
class RecommendList(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('type', type=str,
                        help='类型（hm、ht、nm、nt、dbom、dbhm、dbht、dbdh、dbnm、dbtop、dbzy）',
                        location='form', required=True)
    parser.add_argument('page', type=int, help='页码', location='form', required=True)

    @recommend.doc(parser=parser)
    def post(self):
        """
        推荐列表
        """
        return WebAction().api_action(cmd='get_recommend', data=self.parser.parse_args())


@rss.route('/info')
class RssInfo(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=int, help='任务ID', location='form', required=True)

    @rss.doc(parser=parser)
    def post(self):
        """
        自定义订阅任务详情
        """
        return WebAction().api_action(cmd='get_userrss_task', data=self.parser.parse_args())


@rss.route('/delete')
class RssDelete(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=int, help='任务ID', location='form', required=True)

    @rss.doc(parser=parser)
    def post(self):
        """
        删除自定义订阅任务
        """
        return WebAction().api_action(cmd='delete_userrss_task', data=self.parser.parse_args())


@rss.route('/update')
class RssUpdate(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=int, help='任务ID', location='form')
    parser.add_argument('name', type=str, help='任务名称', location='form', required=True)
    parser.add_argument('address', type=str, help='RSS地址', location='form', required=True)
    parser.add_argument('parser', type=int, help='解析器ID', location='form', required=True)
    parser.add_argument('interval', type=int, help='刷新间隔（分钟）', location='form', required=True)
    parser.add_argument('uses', type=str, help='动作', location='form', required=True)
    parser.add_argument('state', type=str, help='状态（Y/N）', location='form', required=True)
    parser.add_argument('include', type=str, help='包含', location='form')
    parser.add_argument('exclude', type=str, help='排除', location='form')
    parser.add_argument('filterrule', type=int, help='过滤规则', location='form')
    parser.add_argument('note', type=str, help='备注', location='form')

    @rss.doc(parser=parser)
    def post(self):
        """
        新增/修改自定义订阅任务
        """
        return WebAction().api_action(cmd='update_userrss_task', data=self.parser.parse_args())


@rss.route('/parser/info')
class RssParserInfo(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=int, help='解析器ID', location='form', required=True)

    @rss.doc(parser=parser)
    def post(self):
        """
        解析器详情
        """
        return WebAction().api_action(cmd='get_rssparser', data=self.parser.parse_args())


@rss.route('/parser/delete')
class RssParserDelete(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=int, help='解析器ID', location='form', required=True)

    @rss.doc(parser=parser)
    def post(self):
        """
        删除解析器
        """
        return WebAction().api_action(cmd='delete_rssparser', data=self.parser.parse_args())


@rss.route('/parser/update')
class RssParserUpdate(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=int, help='解析器ID', location='form', required=True)
    parser.add_argument('name', type=str, help='名称', location='form', required=True)
    parser.add_argument('type', type=str, help='类型（JSON/XML）', location='form', required=True)
    parser.add_argument('format', type=str, help='解析格式', location='form', required=True)
    parser.add_argument('params', type=str, help='附加参数', location='form')

    @rss.doc(parser=parser)
    def post(self):
        """
        新增/修改解析器
        """
        return WebAction().api_action(cmd='update_rssparser', data=self.parser.parse_args())


@rss.route('/run')
class RssRun(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=int, help='任务ID', location='form', required=True)

    @rss.doc(parser=parser)
    def post(self):
        """
        运行自定义订阅任务
        """
        return WebAction().api_action(cmd='run_userrss', data=self.parser.parse_args())


@rss.route('/preview')
class RssPreview(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=int, help='任务ID', location='form', required=True)

    @rss.doc(parser=parser)
    def post(self):
        """
        自定义订阅预览
        """
        return WebAction().api_action(cmd='list_rss_articles', data=self.parser.parse_args())


@rss.route('/name/test')
class RssNameTest(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('taskid', type=int, help='任务ID', location='form', required=True)
    parser.add_argument('title', type=str, help='名称', location='form', required=True)

    @rss.doc(parser=parser)
    def post(self):
        """
        自定义订阅名称测试
        """
        return WebAction().api_action(cmd='rss_article_test', data=self.parser.parse_args())


@rss.route('/item/history')
class RssItemHistory(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('id', type=int, help='任务ID', location='form', required=True)

    @rss.doc(parser=parser)
    def post(self):
        """
        自定义订阅任务条目处理记录
        """
        return WebAction().api_action(cmd='list_rss_history', data=self.parser.parse_args())


@rss.route('/item/set')
class RssItemSet(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('flag', type=str, help='操作类型（set_finished、set_unfinish）', location='form', required=True)
    parser.add_argument('articles', type=list, help='条目（{title、enclosure}）', location='form', required=True)

    @rss.doc(parser=parser)
    def post(self):
        """
        自定义订阅任务条目状态调整
        """
        return WebAction().api_action(cmd='rss_articles_check', data=self.parser.parse_args())


@rss.route('/item/download')
class RssItemDownload(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('taskid', type=int, help='任务ID', location='form', required=True)
    parser.add_argument('articles', type=list, help='条目（{title、enclosure}）', location='form', required=True)

    @rss.doc(parser=parser)
    def post(self):
        """
        自定义订阅任务条目下载
        """
        return WebAction().api_action(cmd='rss_articles_download', data=self.parser.parse_args())


"""

# media
"modify_tmdb_cache": self.__modify_tmdb_cache,
"clear_tmdb_cache": self.__clear_tmdb_cache,
"get_tvseason_list": self.__get_tvseason_list,
"get_categories": self.__get_categories,
"media_info": self.__media_info,
"delete_tmdb_cache": self.__delete_tmdb_cache,

# brushtask
"add_brushtask": self.__add_brushtask,
"del_brushtask": self.__del_brushtask,
"brushtask_detail": self.__brushtask_detail,
"add_downloader": self.__add_downloader,
"delete_downloader": self.__delete_downloader,
"get_downloader": self.__get_downloader,
"run_brushtask": self.__run_brushtask,

# filterrule
"add_filtergroup": self.__add_filtergroup,
"restore_filtergroup": self.__restore_filtergroup,
"set_default_filtergroup": self.__set_default_filtergroup,
"del_filtergroup": self.__del_filtergroup,
"add_filterrule": self.__add_filterrule,
"del_filterrule": self.__del_filterrule,
"filterrule_detail": self.__filterrule_detail,
"share_filtergroup": self.__share_filtergroup,
"import_filtergroup": self.__import_filtergroup



# words
"add_custom_word_group": self.__add_custom_word_group,
"delete_custom_word_group": self.__delete_custom_word_group,
"add_or_edit_custom_word": self.__add_or_edit_custom_word,
"get_custom_word": self.__get_custom_word,
"delete_custom_word": self.__delete_custom_word,
"check_custom_words": self.__check_custom_words,
"export_custom_words": self.__export_custom_words,
"analyse_import_custom_words_code": self.__analyse_import_custom_words_code,
"import_custom_words": self.__import_custom_words,


# sync
"add_or_edit_sync_path": self.__add_or_edit_sync_path,
"get_sync_path": self.__get_sync_path,
"delete_sync_path": self.__delete_sync_path,
"check_sync_path": self.__check_sync_path,

"""
