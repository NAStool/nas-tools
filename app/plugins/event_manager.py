from queue import Queue, Empty
from threading import Thread, Timer

import log
from app.utils.commons import singleton


@singleton
class EventManager:
    """
    事件管理器
    """

    def __init__(self):
        # 事件队列
        self._eventQueue = Queue()
        # 事件响应函数字典
        self._handlers = {}
        # 事件处理线程
        self._thread = Thread(target=self.__run)
        # 开关
        self._active = True
        # 默认启动
        self.start()

    def __run(self):
        """
        事件处理线程
        """
        while self._active:
            try:
                event = self._eventQueue.get(block=True, timeout=1)
                log.info(f"处理事件：{event}")
                self.__process_event(event)
            except Empty:
                pass

    def __process_event(self, event):
        """
        处理事件
        """
        if event.etype in self._handlers:
            for handler in self._handlers[event.etype]:
                try:
                    handler(event)
                except Exception as err:
                    log.error(f"处理事件出错：{err}")

    def start(self):
        """
        启动
        """
        # 将事件管理器设为启动
        self._active = True
        # 启动事件处理线程
        log.info("事件管理器启动")
        self._thread.start()

    def stop(self):
        """
        停止
        """
        # 将事件管理器设为停止
        self._active = False
        # 等待事件处理线程退出
        log.info("【System】事件管理器停止")
        self._thread.join()

    def add_event_listener(self, etype, handler):
        """
        注册事件处理
        """
        try:
            handlerList = self._handlers[etype]
        except KeyError:
            handlerList = []
            self._handlers[etype] = handlerList
        if handler not in handlerList:
            handlerList.append(handler)

    def remove_event_listener(self, etype, handler):
        """
        移除监听器的处理函数
        """
        try:
            handlerList = self._handlers[etype]
            if handler in handlerList:
                handlerList.remove(handler)
            if not handlerList:
                del self._handlers[etype]
        except KeyError:
            pass

    def send_event(self, event):
        """
        发送事件
        """
        self._eventQueue.put(event)


class Event:
    """
    事件对象
    """
    def __init__(self, etype=None):
        # 事件类型
        self.etype = etype
        # 字典用于保存具体的事件数据
        self.dict = {}
