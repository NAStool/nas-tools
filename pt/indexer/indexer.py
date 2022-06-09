from abc import ABCMeta, abstractmethod


class IIndexer(metaclass=ABCMeta):

    @abstractmethod
    def get_status(self):
        """
        检查连通性
        """
        pass

    @abstractmethod
    def search_by_keyword(self, key_word, filter_args: dict, match_type, match_words):
        """
        根据关键字和过滤条件检索
        """
        pass
