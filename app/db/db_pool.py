# -*- coding: utf-8 -*-

import sqlite3
import threading
from queue import Empty, Queue
import log


class SQLit3PoolConnection:
    @staticmethod
    def create_conn(**config):
        return sqlite3.connect(**config)


dbcs = {
    "SQLite3": SQLit3PoolConnection
}


class DBPool(object):
    """
    数据库连接池
    """

    def __init__(self, max_active=5, max_wait=10, init_size=0, db_type="SQLite3", **config):
        self.__free_conns = Queue(max_active)
        self.max_wait = max_wait
        self.db_type = db_type
        self.config = config
        self.__lock = threading.Lock()
        if init_size > max_active:
            init_size = max_active
        for i in range(init_size):
            log.debug("【Db】初始化数据库连接%s" % str(i))
            self.free(self._create_conn())

    def __del__(self):
        print("__del__ Pool..")
        self.release()

    def release(self):
        """
        释放资源，关闭池中的所有连接
        """
        print("release Pool..")
        self.__lock.acquire()
        while self.__free_conns and not self.__free_conns.empty():
            try:
                con = self.__free_conns.get()
                con.close()
            except Empty:
                break
        self.__free_conns = None
        self.__lock.release()

    def _create_conn(self):
        """
        创建连接
        """
        if self.db_type in dbcs:
            log.debug("【Db】创建连接")
            return dbcs[self.db_type]().create_conn(**self.config)

    def get(self, timeout=None):
        """
        获取一个连接
        @param timeout:超时时间
        """
        log.debug("【Db】获取连接...")
        conn = None
        if timeout is None:
            timeout = self.max_wait
        try:
            self.__lock.acquire()
            if self.__free_conns.empty():  # 如果容器是空的，直接创建一个连接
                conn = self._create_conn()
            else:
                try:
                    conn = self.__free_conns.get(timeout=timeout)
                except Exception as err:
                    # 此处应该考虑获取不到连接处理事务问题, 此处先打印
                    # to do
                    log.warn("【Db】获取连接失败: %s" % str(err))
            return conn
        finally:
            self.__lock.release()

    def free(self, conn):
        """
        将一个连接放回池中
        @param conn: 连接对象
        """
        if conn is None:
            return
        try:
            self.__lock.acquire()
            if self.__free_conns.full():  # 如果当前连接池已满，直接关闭连接
                conn.close()
                log.debug("【Db】关闭连接")
                return
            try:
                log.debug("【Db】回收连接")
                self.__free_conns.put_nowait(conn)
            except Exception as err:
                log.error("【WARN】当前线程池已满，无法放回, 直接释放！%s" % str(err))
                conn.close()
        finally:
            self.__lock.release()
