import base64

from app.utils import RequestUtils
from config import DEFAULT_OCR_SERVER


class OcrHelper:

    _ocr_b64_url = "%sb64/text" % DEFAULT_OCR_SERVER

    def __init__(self):
        pass

    def get_captcha_text(self, image_url, cookie=None, ua=None):
        """
        根据图片地址，获取验证码图片，并识别内容
        """
        if not image_url:
            return ""
        text = ""
        ret = RequestUtils(cookies=cookie, headers=ua).get_res(image_url)
        if ret and ret.status_code == 200:
            image_bin = ret.content
            if not ret.content:
                return ""
            ret = RequestUtils().post_res(url=self._ocr_b64_url, params=base64.b64encode(image_bin).decode())
            if ret and ret.status_code == 200:
                return ret.text
        return text
