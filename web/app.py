import log
from config import Config
from web.main import create_flask_app


class FlaskApp:
    __app = None
    __web_port = None
    __ssl_cert = None
    __ssl_key = None
    __config = None
    __login_user = None
    __login_password = None

    def __init__(self):
        self.__config = Config()
        app = self.__config.get_config('app')
        if app:
            self.__web_port = app.get('web_port')
            self.__ssl_cert = app.get('ssl_cert')
            self.__ssl_key = app.get('ssl_key')
            self.__login_user = app.get('login_user')
            self.__login_password = app.get('login_password')
        if not self.__web_port:
            self.__web_port = 3000
        if not self.__login_user:
            self.__login_user = "admin"
        if not self.__login_password:
            self.__login_password = "password"
        self.__app = create_flask_app(self.__login_user, self.__login_password, self.__ssl_cert)

    def run_service(self):
        try:

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
