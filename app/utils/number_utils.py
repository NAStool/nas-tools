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
        return max(a, b)
