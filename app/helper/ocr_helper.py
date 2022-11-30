import base64
import cv2
import io
import numpy as np

from PIL import Image
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
            if not image_bin:
                return ""
            # 字节转换array进行读取
            image = cv2.imdecode(np.frombuffer(image_bin, np.uint8), cv2.IMREAD_COLOR)
            # 进行灰度化处理
            grayImage = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # 使用合适的阈值进行阈值化处理
            ret, thresh1 = cv2.threshold(grayImage, 20, 255, cv2.THRESH_BINARY)
            # debug显示使用
            # from matplotlib import pyplot as plt
            # plt.imshow(thresh1, cmap='gray')
            # plt.show()
            img = Image.fromarray(thresh1)
            img = img.convert("L")
            buffered = io.BytesIO()
            img.save(buffered, format="png", optimize=True)
            base64_img = base64.b64encode(buffered.getvalue()).decode("utf-8")
            ret = RequestUtils().post_res(url=self._ocr_b64_url, params=base64_img)
            if ret and ret.status_code == 200:
                return ret.text
        return text
