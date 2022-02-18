import atexit
import signal
import sys
import log
from config import get_config
from functions import get_host_name
from message.send import sendmsg
from web.main import create_app


def run_webhook():
    try:
        app = create_app()

        @atexit.register
        def atexit_fun():
            raise RuntimeError('Flask Server Shutdown...')

        def signal_fun(signum, frame):
            log.info("【RUN】webhook捕捉到信号：" + str(signum) + "，开始退出...")
            sendmsg("【NASTOOL】" + get_host_name() + "正在关闭！")
            sys.exit()

        signal.signal(signal.SIGTERM, signal_fun)
        signal.signal(signal.SIGINT, signal_fun)
        config = get_config()
        web_port = config['app']['web_port']
        ssl_cert = config['app']['ssl_cert']
        ssl_key = config['app']['ssl_key']

        if ssl_cert:
            app.run(
                host='0.0.0.0',
                port=web_port,
                debug=False,
                use_reloader=False,
                ssl_context=(ssl_cert, ssl_key)
            )
        else:
            app.run(
                host='0.0.0.0',
                port=web_port,
                debug=False,
                use_reloader=False
            )
    except Exception as err:
        log.error("【RUN】启动web服务失败：" + str(err))
        sendmsg("【NASTOOL】启动web服务失败！", str(err))
