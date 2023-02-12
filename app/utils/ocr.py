import aip
import re

class Ocr:

   def baidu_captcha(self, ocr, img_url):
    """
    百度OCR高精度识别，传入图片URL
    """
    try:
        ocr_client = aip.AipOcr(appId=ocr.get('app_id'), secretKey=ocr.get('secret_key'), apiKey=ocr.get('api_key'))
        # 通用文字识别（标准版）
        res = ocr_client.basicGeneralUrl(img_url)
        if res.get('error_code'):
            # 通用文字识别（高精度版）
            res = ocr_client.basicAccurateUrl(img_url)
        if res.get('error_code'):
            return ''
        # 获取识别出来的验证码
        images_str = res.get('words_result')[0].get('words')
        # 去除杂乱字符
        images_str = ''.join(re.findall('[A-Za-z0-9]+', images_str)).strip()
        return images_str
    except Exception as e:
        return ''
