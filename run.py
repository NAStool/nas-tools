import os
import signal

import log
from config import Config
from service.run import run_monitor, stop_monitor
from service.run import run_scheduler, stop_scheduler
from utils.check_config import check_config
from utils.functions import get_system, check_process
from utils.types import OsType
from version import APP_VERSION
from web.app import FlaskApp


def sigal_handler(num, stack):
    if get_system() == OsType.LINUX and check_process("supervisord"):
        print(str(stack))
        log.warn('捕捉到退出信号：%s，开始退出...' % num)
        # 停止定时服务
        stop_scheduler()
        # 停止监控
        stop_monitor()
        # 退出主进程
        quit()


if __name__ == "__main__":

    print("""
       ~7^         !77^         .7?.          .^7?JJJ?!^  :77777777777777777.                               ~JYY.       
       JGP?.      .PGG?         ?GGJ         !5GGP5Y5PGY. ~PPPPPPGGGGPPPPPPP:                               ?GGP.       
       JGPGP!     .5GG?        7GGGG?       ~GGG7    .^:   ......?GPP^......    ..               .          ?GG5.       
       JGPPGGY^   .5GG?       ~GG55GG!      ~GGG?.               ?GPP.      ~?Y5PP5Y?~      .!JY5P55J7:     ?GG5.       
       JGG5JPGP?. .5GG?      ^PGG^:PGP~      7PGGPJ!:.           ?GPP:    ^YGG5?!!?5GGY:   !PGGY7!7JPGP?    ?GG5.       
       JGG5 ^YGG5!.5GG?     :5GG?  7GGP:      .~?5GGG5?^         ?GPP:   :PGGJ.    .YGG5. !GGP!     ^PGG7   ?GG5.       
       JGG5   7PGGYPPG?    .YGG5.  .YGG5.         :!YGGG?        ?GPP:   !GPG^      !GPG^ YGG5       YGG5   ?GG5.       
       JGG5    :JGGPPG?    JGPGP5555PGPGY            ?GPG:       ?GPP:   ~GPG~      ?GGP: JGG5.     .5GGY   ?GG5.       
       JGG5      ~5GPG?   7GPG7!!!!!!7PPGJ   ^7^:...:JGG5.       ?GPP:    JGG5~.  .7PGG?  :PGGJ:. .:JGGP^   ?GGP.       
       JGG5.      .?PG?  !GGG?        7GGG7 :5GGPPPPGGPJ:        ?GGP:     !5PGP55PGPY~    :?5GGP5PGGPJ:    !GGGJ:      
       ^!!~         ^?~  ~!!~.         ~!!!. :~!7??7!^.          ^!!~.       :~!77!~:        .^~!77!^.       ^!!~.      
     """)

    # 参数
    os.environ['TZ'] = 'Asia/Shanghai'
    log.console("配置文件地址：%s" % os.environ.get('NASTOOL_CONFIG'))
    log.console('NASTool 当前版本号：%s' % APP_VERSION)

    # 检查配置文件
    config = Config()
    if not check_config(config):
        quit()

    # 启动进程
    log.console("开始启动进程...")

    # 退出事件
    signal.signal(signal.SIGINT, sigal_handler)
    signal.signal(signal.SIGTERM, sigal_handler)

    # 启动定时服务
    run_scheduler()

    # 启动监控服务
    run_monitor()

    # 启动主WEB服务
    FlaskApp().run_service()
