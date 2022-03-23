# -*- coding: utf-8 -*-
# @Author  : Qliangw
# @Time    : 2022/3/1 21:05
# @Function: http请求工具

import datetime
import random
import time

import requests
import urllib3


class RequestUtils:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    __pre_request_time = None

    def __init__(self, request_interval_mode=False):
        self.request_interval_mode = request_interval_mode

    def check_request(self):
        if not self.request_interval_mode:
            return
        """
        todo 对不同domain做不同配置
        检测每次请求的间隔，如果频率太快则休息，休息时间尽量无规律
        :return:
        """
        if self.__pre_request_time is None:
            self.__pre_request_time = datetime.datetime.now()
            return
        during_time = datetime.datetime.now() - self.__pre_request_time
        ms = during_time.microseconds / 1000
        # 至少间隔1秒，随机是为了无规律
        if ms < random.randint(1000, 5000):
            min_sleep_secs = 1
            # 随机休眠0.5-5秒，扣除间隔影响，避免休眠太久
            max_sleep_secs = 10.0 - (ms / 1000)
            # 避免间隔太久随机出错
            if max_sleep_secs <= min_sleep_secs:
                max_sleep_secs = min_sleep_secs * 2
            sleep_secs = random.uniform(min_sleep_secs, max_sleep_secs)
            time.sleep(sleep_secs)
        self.__pre_request_time = datetime.datetime.now()

    def post(self, url, params, headers={}, json={}):
        """
        post 请求

        :param url:
        :param params:
        :param headers:
        :param json:
        :return:
        """
        i = 0
        while i < 3:
            try:
                self.check_request()
                r = requests.post(url, data=params,
                                  verify=False, headers=headers, json=json)
                # return str(r.content, 'UTF-8')
                return r
            except requests.exceptions.RequestException:
                i += 1

    def get(self, url, params=None, headers=None):
        i = 0
        while i < 3:
            try:
                self.check_request()
                r = requests.get(url, verify=False, headers=headers, params=params)
                return str(r.content, 'UTF-8')
            except requests.exceptions.RequestException:
                i += 1

    def get_res(self, url, params=None, headers={}, cookies=None):
        i = 0
        while i < 3:
            try:
                self.check_request()
                return requests.get(url, params=params, verify=False, headers=headers, cookies=cookies)
            except requests.exceptions.RequestException as e:
                print(e)
                i += 1

    def post_res(self, url, params=None, headers={}, cookies=None, allow_redirects=True):
        i = 0
        while i < 3:
            try:
                self.check_request()
                return requests.post(url, params=params, verify=False, headers=headers, cookies=cookies,
                                     allow_redirects=allow_redirects)
            except requests.exceptions.RequestException as e:
                print(e)
                i += 1
