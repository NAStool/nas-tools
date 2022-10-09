import log
from config import Config
from web.main import create_flask_app


class FlaskApp:
    __app = None
    __web_host = "::"
    __web_port = None
    __ssl_cert = None
    __ssl_key = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        app = config.get_config('app')
        if app:
            if app.get("web_host"):
                self.__web_host = app.get("web_host")
            self.__web_port = int(app.get('web_port')) if str(app.get('web_port')).isdigit() else 3000
            self.__ssl_cert = app.get('ssl_cert')
            self.__ssl_key = app.get('ssl_key')
        if not self.__web_port:
            self.__web_port = 3000
        self.__app = create_flask_app()

    def run_service(self):
        try:
            if self.__ssl_cert:
                self.__app.run(
                    host=self.__web_host,
                    port=self.__web_port,
                    debug=False,
                    threaded=True,
                    use_reloader=False,
                    ssl_context=(self.__ssl_cert, self.__ssl_key)
                )
            else:
                self.__app.run(
                    host=self.__web_host,
                    port=self.__web_port,
                    debug=False,
                    threaded=True,
                    use_reloader=False
                )
        except Exception as err:
            log.error("【RUN】启动web服务失败：%s" % str(err))
