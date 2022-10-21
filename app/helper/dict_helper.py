from app.db.main_db import MainDb
from app.db.models import SYSTEMDICT


class DictHelper:

    @staticmethod
    def set(dtype, key, value, note=""):
        """
        设置字典值
        :param dtype: 字典类型
        :param key: 字典Key
        :param value: 字典值
        :param note: 备注
        :return: True False
        """
        if not dtype or not key or not value:
            return False
        if DictHelper.exists(dtype, key):
            return MainDb().query(SYSTEMDICT).filter(SYSTEMDICT.TYPE == dtype,
                                                     SYSTEMDICT.KEY == key).update(
                {
                    "VALUE": value
                }
            )
        else:
            return MainDb().insert(SYSTEMDICT(
                TYPE=dtype,
                KEY=key,
                VALUE=value,
                NOTE=note
            ))

    @staticmethod
    def get(dtype, key):
        """
        查询字典值
        :param dtype: 字典类型
        :param key: 字典Key
        :return: 返回字典值
        """
        if not dtype or not key:
            return ""
        ret = MainDb().query(SYSTEMDICT.VALUE).filter(SYSTEMDICT.TYPE == dtype,
                                                      SYSTEMDICT.KEY == key).first()
        if ret:
            return ret[0]
        else:
            return ""

    @staticmethod
    def delete(dtype, key):
        """
        删除字典值
        :param dtype: 字典类型
        :param key: 字典Key
        :return: True False
        """
        if not dtype or not key:
            return False
        return MainDb().query(SYSTEMDICT).filter(SYSTEMDICT.TYPE == dtype,
                                                 SYSTEMDICT.KEY == key).delete()

    @staticmethod
    def exists(dtype, key):
        """
        查询字典是否存在
        :param dtype: 字典类型
        :param key: 字典Key
        :return: True False
        """
        if not dtype or not key:
            return False
        ret = MainDb().query(SYSTEMDICT).filter(SYSTEMDICT.TYPE == dtype,
                                                SYSTEMDICT.KEY == key).count()
        if ret > 0:
            return True
        else:
            return False
