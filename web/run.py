import log
import settings
from message.send import sendmsg
from web.main import create_app


def run_webhook(config_file):
    settings.config_file_path = config_file
    settings.reload_config()
    try:
        app = create_app()
        app.run(
            host='0.0.0.0',
            port=3000,
            debug=False,
            use_reloader=False
        )
    except Exception as err:
        log.error("【RUN】启动web服务失败：" + str(err))
        sendmsg("【NASTOOL】启动web服务失败！", str(err))
