from app.utils import ExceptionUtils
from PIL import Image, ImageDraw, ImageOps
from collections import Counter
import requests
from io import BytesIO
import base64
import log


class ImageUtils:

    @staticmethod
    def calculate_theme_color(image_path):
        # 打开图片并转换为RGB模式
        img = Image.open(image_path).convert('RGB')
        # 缩小图片尺寸以加快计算速度
        img = img.resize((100, 100), resample=Image.BILINEAR)
        # 获取所有像素颜色值
        pixels = img.getdata()
        # 统计每种颜色在像素中出现的频率
        pixel_count = Counter(pixels)
        # 找到出现频率最高的颜色，作为主题色
        dominant_color = pixel_count.most_common(1)[0][0]
        # 将主题色转换为16进制表示
        theme_color = '#{:02x}{:02x}{:02x}'.format(*dominant_color)
        # 返回主题色
        return theme_color

    @staticmethod
    def get_libraries_image(urls):
        """
        下载媒体库前4张图片,进行拼接拼接
        """
        try:
            posters = []
            for url in urls:
                response = requests.get(url)
                image = Image.open(BytesIO(response.content))
                posters.append(image)

            # 准备参数
            poster_width, poster_height, gradient_height = 123, 200, 47
            width = poster_width * len(posters)
            height = poster_height + gradient_height
            poster_width_offset = 0

            # 最终图片
            all_posters_images = Image.new('RGB', (width, poster_height))

            # 拼接海报
            for image in posters:
                image = image.resize((poster_width, poster_height))
                all_posters_images.paste(image, (poster_width_offset, 0))
                poster_width_offset += poster_width
            # 倒影
            reflection = all_posters_images.copy().transpose(Image.FLIP_TOP_BOTTOM)
            # 渐变
            gradient_image = Image.new('L', (width, gradient_height), 0)
            draw = ImageDraw.Draw(gradient_image)
            for i in range(gradient_height):
                alpha = int(255 * i / gradient_height * 0.15)
                draw.line((0, i, width, i), fill=alpha)
            gradient_image = gradient_image.transpose(Image.FLIP_TOP_BOTTOM)
            # 渐变遮罩
            gradient_mask = ImageOps.invert(gradient_image)

            # 最终结果
            result_image = Image.new('RGB', (width, height))
            result_image.paste(all_posters_images, (0, 0))
            result_image.paste(reflection, (0, poster_height))
            result_image.paste(gradient_image, (0, poster_height), gradient_mask)

            # 将图片转为base64
            buffer = BytesIO()
            result_image.save(buffer, format='JPEG')
            base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return 'data:image/jpeg;base64,' + base64_str
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"拼接媒体库封面出错：" + str(e))
        return "../static/img/mediaserver/plex_backdrop.png"
