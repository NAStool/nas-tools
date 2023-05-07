from cachetools import cached, TTLCache

from app.utils import RequestUtils


class PluginHelper:

    @staticmethod
    def install(plugin_id):
        """
        插件安装统计计数
        """
        return RequestUtils(timeout=5).get(f"https://nastool.cn/plugin/{plugin_id}/install")

    @staticmethod
    @cached(cache=TTLCache(maxsize=1, ttl=3600))
    def statistic():
        """
        获取插件安装统计数据
        """
        ret = RequestUtils(accept_type="application/json",
                           timeout=5).get_res("https://nastool.cn/plugin/statistic")
        if ret:
            try:
                return ret.json()
            except Exception as e:
                print(e)
        return {}
