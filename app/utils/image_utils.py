from PIL import Image
from collections import Counter


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
