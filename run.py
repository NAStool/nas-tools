import server
from web.app import FlaskApp

if __name__ == "__main__":

    # 参数
    server.os.environ['TZ'] = 'Asia/Shanghai'
    server.log.console("配置文件地址：%s" % server.os.environ.get('NASTOOL_CONFIG'))
    server.log.console('NASTool 当前版本号：%s' % server.APP_VERSION)

    config = server.Config()

    # 数据库初始化
    server.init_db()

    # 数据库更新
    server.update_db(config)

    # 升级配置文件
    server.update_config(config)

    # 检查配置文件
    if not server.check_config(config):
        server.sys.exit()

    # 启动进程
    server.log.console("开始启动进程...")

    # 退出事件
    server.signal.signal(server.signal.SIGINT, server.sigal_handler)
    server.signal.signal(server.signal.SIGTERM, server.sigal_handler)

    # 启动定时服务
    server.run_scheduler()

    # 启动监控服务
    server.run_monitor()

    # 启动刷流服务
    server.BrushTask()

    # 启动自定义订阅服务
    server.RssChecker()

    # 加载索引器配置
    server.IndexerHelper()

    # Windows启动托盘
    if server.is_windows_exe:
        homepage = config.get_config('app').get('domain')
        if not homepage:
            homepage = "http://localhost:%s" % str(config.get_config('app').get('web_port'))
        log_path = server.os.environ.get("NASTOOL_LOG")


        def traystart():
            server.trayicon(server.server.homepage, server.log_path)


        if len(server.os.popen("tasklist| findstr %s" % server.os.path.basename(server.sys.executable), 'r').read().splitlines()) <= 2:
            p1 = server.threading.Thread(target=traystart, daemon=True)
            p1.start()

    # 启动主WEB服务
    FlaskApp().run_service()
