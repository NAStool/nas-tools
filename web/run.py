import log
from message.send import sendmsg
from web.main import create_app

logger = log.Logger("run").logger


def run_webhook():
    try:
        app = create_app()
        app.run(
            host='0.0.0.0',
            port=3000,
            debug=False,
            use_reloader=False
        )
    except Exception as err:
        logger.error("【RUN】启动web服务失败：" + str(err))
        sendmsg("【NASTOOL】启动web服务失败！", str(err))


if __name__ == "__main__":
    run_webhook()
