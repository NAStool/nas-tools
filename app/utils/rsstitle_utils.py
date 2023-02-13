import re

from app.utils.exception_utils import ExceptionUtils


class RssTitleUtils:

    @staticmethod
    def keepfriends_title(title):
        """
        处理pt.keepfrds.com的RSS标题
        """
        if not title:
            return ""
        try:
            title_search = re.search(r"\[(.*)]", title, re.IGNORECASE)
            if title_search:
                if title_search.span()[0] == 0:
                    title_all = re.findall(r"\[(.*?)]", title, re.IGNORECASE)
                    if title_all and len(title_all) > 1:
                        torrent_name = title_all[-1]
                        torrent_desc = title.replace(f"[{torrent_name}]", "").strip()
                        title = "%s %s" % (torrent_name, torrent_desc)
                else:
                    torrent_name = title_search.group(1)
                    torrent_desc = title.replace(title_search.group(), "").strip()
                    title = "%s %s" % (torrent_name, torrent_desc)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
        return title
