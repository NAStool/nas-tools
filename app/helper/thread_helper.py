from concurrent.futures import ThreadPoolExecutor

from app.utils.commons import singleton


@singleton
class ThreadHelper:
    _thread_num = 100
    executor = None

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=self._thread_num)

    def init_config(self):
        pass

    def start_thread(self, func, kwargs):
        self.executor.submit(func, *kwargs)
