from app.utils import RequestUtils
from config import NASTOOL_PLUGIN_INSTALL, NASTOOL_PLUGIN_STATISTIC


class PluginHelper:

    @staticmethod
    def install(plugin_id):
        """
        插件安装统计计数
        """
        return RequestUtils(timeout=5).get(NASTOOL_PLUGIN_INSTALL % plugin_id)

    @staticmethod
    def statistic():
        """
        获取插件安装统计数据
        """
        ret = RequestUtils(accept_type="application/json",
                           timeout=5).get_res(NASTOOL_PLUGIN_STATISTIC)
        if ret:
            try:
                return ret.json()
            except Exception as e:
                print(e)
        return {}
