import base64

from app.utils import RequestUtils
from config import DEFAULT_OCR_SERVER


class OcrHelper:
    req = None
    _ocr_b64_url = "%s/captcha/base64" % DEFAULT_OCR_SERVER

    def __init__(self):
        self.req = RequestUtils(content_type="application/json")

    def get_captcha_text(self, image_url=None, image_b64=None):
        """
        根据图片地址，获取验证码图片，并识别内容
        """
        if not image_url and not image_b64:
            return ""
        if image_url:
            ret = self.req.get_res(image_url)
            if ret is not None:
                image_bin = ret.content
                if not image_bin:
                    return ""
                image_b64 = base64.b64encode(image_bin).decode()
        ret = self.req.post_res(url=self._ocr_b64_url,
                                json={"base64_img": image_b64})
        if ret:
            return ret.json().get("result")
        return ""
