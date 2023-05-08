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
    def report(plugins):
        """
        批量上报插件安装统计数据
        """
        return RequestUtils(content_type="application/json",
                            timeout=5).post(f"https://nastool.cn/plugin/update", json={
            "plugins": [{"plugin_id": plugin, "count": 1} for plugin in plugins]
        })

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
