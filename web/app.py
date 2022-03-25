import signal
import sys
from time import sleep

import log
from config import Config
from web.main import create_flask_app

WEB_RUNNING = True


class FlaskApp:
    __app = None
    __web_port = None
    __ssl_cert = None
    __ssl_key = None
    __config = None

    def __init__(self):
        self.__app = create_flask_app()
        self.__config = Config()
        app = self.__config.get_config('app')
        if app:
            self.__web_port = app.get('web_port')
            self.__ssl_cert = app.get('ssl_cert')
            self.__ssl_key = app.get('ssl_key')

    def run_service(self):
        global WEB_RUNNING

        def signal_fun(signum, frame):
            global WEB_RUNNING
            log.info("【RUN】web捕捉到信号：" + str(signum) + "，开始退出...")
            WEB_RUNNING = False

        try:

            if not self.__app:
                while WEB_RUNNING:
                    try:
                        sleep(1)
                    except KeyboardInterrupt as e:
                        sys.exit()
            else:
                signal.signal(signal.SIGTERM, signal_fun)
                signal.signal(signal.SIGINT, signal_fun)

                if self.__ssl_cert:
                    self.__app.run(
                        host='0.0.0.0',
                        port=self.__web_port,
                        debug=False,
                        use_reloader=False,
                        ssl_context=(self.__ssl_cert, self.__ssl_key)
                    )
                else:
                    self.__app.run(
                        host='0.0.0.0',
                        port=self.__web_port,
                        debug=False,
                        use_reloader=False
                    )
        except Exception as err:
            log.error("【RUN】启动web服务失败：%s" % str(err))
