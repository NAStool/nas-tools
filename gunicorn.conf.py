"""
这个文件是对gunicorn启动方式进行管理的配置文件具体参数可以查看下边的说明注释
主要涉及到启动方式，进程数，线程数已经配置读取
"""
from config import Config

# 这里读取配置文件进行启动项参数的入参
app_conf = Config().get_config('app')
if app_conf:
    _web_host = app_conf.get("web_host")
    if not _web_host or _web_host == '::':
        _web_host = '[::]'
    _web_port = int(app_conf.get('web_port')) if str(app_conf.get('web_port')).isdigit() else 3000
    bind = f"{_web_host}:{int(_web_port)}"
    keyfile = app_conf.get('ssl_cert')
    certfile = app_conf.get('ssl_key')

#
# Server socket
#
#   bind - The socket to bind.
#
#       A string of the form: 'HOST', 'HOST:PORT', 'unix:PATH'.
#       An IP is a valid HOST.
#
#   backlog - The number of pending connections. This refers
#       to the number of clients that can be waiting to be
#       served. Exceeding this number results in the client
#       getting an error when attempting to connect. It should
#       only affect servers under significant load.
#       挂起的连接数。这是指可以等待服务的客户数量。超过此数字会导致客户端在尝试连接时出错。它应该只影响负载很大的服务器
#
#       Must be a positive integer. Generally set in the 64-2048
#       range.
#       必须是正整数。一般设置在 64-2048 范围内

# 工作模式协程
#
# Worker processes
#
#   workers - The number of worker processes that this server
#       should keep alive for handling requests.
#       此服务器应保持活动状态以处理请求的工作进程数

#       A positive integer generally in the 2-4 x $(NUM_CORES)
#       range. You'll want to vary this a bit to find the best
#       for your particular application's work load.
#       通常在 2-4 x (NUM_CORES) 范围内的正整数。您需要稍微改变一下，以找到最适合您的特定应用程序工作负载的方法
#
#   worker_class - The type of workers to use. The default
#       sync class should handle most 'normal' types of work
#       loads. You'll want to read
#       http://docs.gunicorn.org/en/latest/design.html#choosing-a-worker-type
#       for information on when you might want to choose one
#       of the other worker classes.
#
#       A string referring to a Python path to a subclass of
#       gunicorn.workers.base.Worker. The default provided values
#       can be seen at
#       http://docs.gunicorn.org/en/latest/settings.html#worker-class
#
#   worker_connections - For the eventlet and gevent worker classes
#       this limits the maximum number of simultaneous clients that
#       a single process can handle.
#
#       A positive integer generally set to around 1000.
#       对于 eventlet 和 gevent worker 类，这限制了单个进程可以处理的同时客户端的最大数量。一个正整数，通常设置为 1000 左右
#
#   timeout - If a worker does not notify the master process in this
#       number of seconds it is killed and a new worker is spawned
#       to replace it.
#
#       Generally set to thirty seconds. Only set this noticeably
#       higher if you're sure of the repercussions for sync workers.
#       For the non sync workers it just means that the worker
#       process is still communicating and is not tied to the length
#       of time required to handle a single request.
#
#   keepalive - The number of seconds to wait for the next request
#       on a Keep-Alive HTTP connection.
#
#       A positive integer. Generally set in the 1-5 seconds range.
# worker_class = 'uvicorn.workers.UvicornWorker'
workers = 1
worker_class = 'sync'
# 指定每个工作者的线程数
threads = 8
# 设置最大并发量
worker_connections = 1000
timeout = 0
keepalive = 2

# 日志级别，这个日志级别指的是错误日志的级别，而访问日志的级别无法设置
#
#   Logging
#
#   logfile - The path to a log file to write to.
#
#       A path string. "-" means log to stdout.
#
#   loglevel - The granularity of log output
#
#       A string of "debug", "info", "warning", "error", "critical"
#

errorlog = "-"
loglevel = "info"

#
#   spew - Install a trace function that spews every line of Python
#       that is executed when running the server. This is the
#       nuclear option.
#       安装一个跟踪函数，该函数会在运行服务器时生成每行执行的 Python
#
#       True or False
#

spew = False
#
# Server mechanics
#
#   daemon - Detach the main Gunicorn process from the controlling
#       terminal with a standard fork/fork sequence.
#
#       True or False
#
#   raw_env - Pass environment variables to the execution environment.
#
#   pidfile - The path to a pid file to write
#
#       A path string or None to not write a pid file.
#
#   user - Switch worker processes to run as this user.
#
#       A valid user id (as an integer) or the name of a user that
#       can be retrieved with a call to pwd.getpwnam(value) or None
#       to not change the worker process user.
#
#   group - Switch worker process to run as this group.
#
#       A valid group id (as an integer) or the name of a user that
#       can be retrieved with a call to pwd.getgrnam(value) or None
#       to change the worker processes group.
#
#   umask - A mask for file permissions written by Gunicorn. Note that
#       this affects unix socket permissions.
#
#       A valid value for the os.umask(mode) call or a string
#       compatible with int(value, 0) (0 means Python guesses
#       the base, so values like "0", "0xFF", "0022" are valid
#       for decimal, hex, and octal representations)
#
#   tmp_upload_dir - A directory to store temporary request data when
#       requests are read. This will most likely be disappearing soon.
#
#       A path to a directory where the process owner can write. Or
#       None to signal that Python should choose one on its own.
#

daemon = False


def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def pre_fork(server, worker):
    pass  # 暂时未定义需求，留空


def pre_exec(server):
    server.log.info("Forked child, re-executing.")


def when_ready(server):
    server.log.info("Server is ready. Spawning workers")


def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

    # get traceback info
    import sys
    import threading
    import traceback

    id2name = {th.ident: th.name for th in threading.enumerate()}
    code = []
    for thread_id, stack in sys._current_frames().items():
        code.append("\n# Thread: %s(%d)" % (id2name.get(thread_id, ""), thread_id))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    worker.log.debug("\n".join(code))


def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal")
