import re


class RssTitleUtils:

    @staticmethod
    def keepfriends_title(title):
        """
        处理pt.keepfrds.com的RSS标题
        """
        if not title:
            return ""
        try:
            title_re = re.search(r"\[(.*)]", title, re.IGNORECASE)
            if title_re:
                torrent_name = title_re.group(1)
                torrent_desc = title.replace(title_re.group(), "").strip()
                title = "%s %s" % (torrent_name, torrent_desc)
        except Exception as err:
            print(str(err))
        return title
