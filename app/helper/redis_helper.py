from app.utils import SystemUtils


class RedisHelper:

    @staticmethod
    def is_valid():
        """
        判斷redis是否有效
        """
        if SystemUtils.is_docker():
            return True if SystemUtils.execute("which redis-server") else False
        else:
            return False
