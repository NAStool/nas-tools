from queue import Queue, Empty
from threading import Thread

import log
from app.utils.commons import singleton
from app.utils.types import EventType


@singleton
class EventManager:
    """
    事件管理器
    """

    # 事件队列
    _eventQueue = None
    # 事件响应函数字典
    _handlers = {}
    # 事件处理线程
    _thread = None
    # 开关
    _active = False

    def __init__(self):
        self.init_config()

    def init_config(self):
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
        self._thread.start()

    def stop(self):
        """
        停止
        """
        # 将事件管理器设为停止
        self._active = False
        # 等待事件处理线程退出
        self._thread.join()

    def add_event_listener(self, etype: EventType, handler):
        """
        注册事件处理
        """
        try:
            handlerList = self._handlers[etype.value]
        except KeyError:
            handlerList = []
            self._handlers[etype.value] = handlerList
        if handler not in handlerList:
            handlerList.append(handler)
        log.debug(f"已注册事件：{self._handlers}")

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

    def send_event(self, etype: EventType, data: dict = None):
        """
        发送事件
        """
        if etype not in EventType:
            return
        event = Event(etype.value)
        event.dict = data or {}
        self._eventQueue.put(event)

    def register(self, etype: EventType):
        """
        事件注册
        :param etype: 事件类型
        """

        def decorator(f):
            self.add_event_listener(etype, f)
            return f

        return decorator


class Event(object):
    """
    事件对象
    """

    def __init__(self, etype=None):
        # 事件类型
        self.etype = etype
        # 字典用于保存具体的事件数据
        self.dict = {}


# 实例引用，用于注册事件
EventHandler = EventManager()
