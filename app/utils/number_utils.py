class NumberUtils:

    @staticmethod
    def max_ele(a, b):
        """
        返回非空最大值
        """
        if not a:
            return b
        if not b:
            return a
        return max(int(a), int(b))

    @staticmethod
    def get_size_gb(size):
        """
        将字节转换为GB
        """
        if not size:
            return 0.0
        return float(size) / 1024 / 1024 / 1024
