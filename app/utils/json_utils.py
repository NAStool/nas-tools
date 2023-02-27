import json
from enum import Enum


class JsonUtils:

    @staticmethod
    def json_serializable(obj):
        """
        将普通对象转化为支持json序列化的对象
        @param obj: 待转化的对象
        @return: 支持json序列化的对象
        """

        def _try(o):
            if isinstance(o, Enum):
                return o.value
            try:
                return o.__dict__
            except Exception as err:
                print(str(err))
                return str(o)

        return json.loads(json.dumps(obj, default=lambda o: _try(o)))
