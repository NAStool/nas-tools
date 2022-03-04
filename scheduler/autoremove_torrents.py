import log
from pt.downloader import Downloader


class AutoRemoveTorrents:
    downloader = None

    def __init__(self):
        self.downloader = Downloader()

    def run_schedule(self):
        try:
            if self.downloader:
                self.downloader.pt_removetorrents()
        except Exception as err:
            log.error("【RUN】执行任务autoremovetorrents出错：%s" % str(err))


if __name__ == "__main__":
    AutoRemoveTorrents().run_schedule()
