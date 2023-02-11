from app.utils import SystemUtils


class FfmpegHelper:

    @staticmethod
    def get_thumb_image_from_video(video_path, image_path, frames="00:03:01"):
        """
        使用ffmpeg从视频文件中截取缩略图
        """
        if not video_path or not image_path:
            return False
        cmd = 'ffmpeg -i "{video_path}" -ss {frames} -vframes 1 -f image2 "{image_path}"'.format(video_path=video_path,
                                                                                                 frames=frames,
                                                                                                 image_path=image_path)
        result = SystemUtils.execute(cmd)
        if result:
            return True
        return False
