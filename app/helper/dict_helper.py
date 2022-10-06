from app.db.main_db import MainDb


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
            return MainDb().update_by_sql("UPDATE SYSTEM_DICT SET VALUE = ? WHERE TYPE = ? AND KEY = ?",
                                            (value, dtype, key))
        else:
            return MainDb().update_by_sql("INSERT INTO SYSTEM_DICT (TYPE, KEY, VALUE, NOTE) VALUES (?, ?, ?, ?)",
                                            (dtype, key, value, note))

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
        ret = MainDb().select_by_sql("SELECT VALUE FROM SYSTEM_DICT WHERE TYPE = ? AND KEY = ?",
                                       (dtype, key))
        if ret and ret[0][0]:
            return ret[0][0]
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
        return MainDb().update_by_sql("DELETE FROM SYSTEM_DICT WHERE TYPE = ? AND KEY = ?", (dtype, key))

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
        ret = MainDb().select_by_sql("SELECT COUNT(1) FROM SYSTEM_DICT WHERE TYPE = ? AND KEY = ?", (dtype, key))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False
