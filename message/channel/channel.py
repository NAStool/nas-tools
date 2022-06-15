from abc import ABCMeta, abstractmethod


class IMessageChannel(metaclass=ABCMeta):

    @abstractmethod
    def get_status(self):
        """
        检查连通性
        """
        pass

    @abstractmethod
    def send_msg(self, title, text, image, url, user_id):
        """
        消息发送入口，支持文本、图片、链接跳转、指定发送对象
        :param title: 消息标题
        :param text: 消息内容
        :param image: 图片地址
        :param url: 点击消息跳转URL
        :param user_id: 消息发送对象的ID，为空则发给所有人
        :return: 发送状态，错误信息
        """
        pass
