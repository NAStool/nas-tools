from app.utils.commons import singleton


@singleton
class ProgressHelper(object):
    _process_detail = {}

    def __init__(self):
        self._process_detail = {}

    def init_config(self):
        pass

    def reset(self, ptype="search"):
        self._process_detail[ptype] = {
            "enable": False,
            "value": 0,
            "text": "请稍候..."
        }

    def start(self, ptype="search"):
        self.reset(ptype)
        self._process_detail[ptype]['enable'] = True

    def end(self, ptype="search"):
        if not self._process_detail.get(ptype):
            return
        self._process_detail[ptype]['enable'] = False

    def update(self, value=None, text=None, ptype="search"):
        if not self._process_detail.get(ptype, {}).get('enable'):
            return
        if value:
            self._process_detail[ptype]['value'] = value
        if text:
            self._process_detail[ptype]['text'] = text

    def get_process(self, ptype="search"):
        return self._process_detail.get(ptype)
