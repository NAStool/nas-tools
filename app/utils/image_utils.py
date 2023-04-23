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
            # 单张的宽和高
            poster_width, poster_height, = 150, 252
            # 边框的宽和高
            margin_width, margin_height, = 8, 4
            # 倒影的高
            gradient_height = 100
            # 倒影的真实的高度,单张图片的一般高度,多出来的部分不展示
            gradient_actual_height = poster_height // 2
            # 4 张海报的宽和高(不含外边框,含内边框)
            all_poster_width = poster_width * len(posters) + 8 * (len(posters) - 1)
            all_poster_height = poster_height

            width = poster_width * len(posters) + margin_width * (len(posters) + 1)
            height = poster_height + gradient_height + margin_height * 2

            # 海报图片
            all_posters_images = Image.new('RGB', (all_poster_width, all_poster_height))

            # 拼接海报
            poster_width_offset = 0
            for image in posters:
                image = image.resize((poster_width, poster_height))
                all_posters_images.paste(image, (poster_width_offset, 0))
                poster_width_offset += poster_width + margin_width
            # 倒影
            reflection = all_posters_images.copy().transpose(Image.FLIP_TOP_BOTTOM)
            reflection = reflection.resize((all_poster_width, gradient_actual_height))
            # 渐变遮罩
            gradient_mask = Image.new('L', (all_poster_width, gradient_actual_height), 0)
            draw = ImageDraw.Draw(gradient_mask)
            for i in range(gradient_actual_height):
                alpha = 128 - int(i * (256 / gradient_actual_height))
                draw.line((0, i, width, i), fill=alpha)

            # 最终结果
            result_image = Image.new('RGB', (width, height))
            result_image.paste(all_posters_images, (margin_width, margin_height))
            result_image.paste(reflection, (margin_width, poster_height + margin_height * 2), gradient_mask)

            # 将图片转为base64
            buffer = BytesIO()
            result_image.save(buffer, format='JPEG')
            base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return 'data:image/jpeg;base64,' + base64_str
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"拼接媒体库封面出错：" + str(e))
        return "../static/img/mediaserver/plex_backdrop.png"
