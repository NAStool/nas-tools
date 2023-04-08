import time


class SiteRateLimiter:
    def __init__(self, limit_interval: int, limit_count: int, limit_seconds: int):
        """
        限制访问频率
        :param limit_interval: 单位时间（秒）
        :param limit_count: 单位时间内访问次数
        :param limit_seconds: 访问间隔（秒）
        """
        self.limit_count = limit_count
        self.limit_interval = limit_interval
        self.limit_seconds = limit_seconds
        self.last_visit_time = 0
        self.count = 0

    def check_rate_limit(self) -> (bool, str):
        """
        检查是否超出访问频率控制
        :return: 超出返回True，否则返回False，超出时返回错误信息
        """
        current_time = time.time()
        # 防问间隔时间
        if self.limit_seconds:
            if current_time - self.last_visit_time < self.limit_seconds:
                return True, f"触发流控规则，访问间隔不得小于 {self.limit_seconds} 秒，" \
                             f"上次访问时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_visit_time))}"
        # 单位时间内访问次数
        if self.limit_interval and self.limit_count:
            if current_time - self.last_visit_time > self.limit_interval:
                # 计数清零
                self.count = 0
            if self.count >= self.limit_count:
                return True, f"触发流控规则，{self.limit_interval} 秒内访问次数不得超过 {self.limit_count} 次，" \
                             f"上次访问时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_visit_time))}"
            # 访问计数
            self.count += 1
        # 更新最后访问时间
        self.last_visit_time = current_time
        # 未触发流控
        return False, ""


if __name__ == "__main__":
    # 限制 1 分钟内最多访问 10 次，单次访问间隔不得小于 10 秒
    site_rate_limit = SiteRateLimiter(10, 60, 10)

    # 模拟访问
    for i in range(12):
        if site_rate_limit.check_rate_limit():
            print("访问频率超限")
        else:
            print("访问成功")
        time.sleep(3)
