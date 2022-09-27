# -*- coding: utf-8 -*-

import xmlrpc.client

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 6800
SERVER_URI_FORMAT = '%s:%s/rpc'


class PyAria2(object):
    _secret = None

    def __init__(self, secret=None, host=DEFAULT_HOST, port=DEFAULT_PORT):
        """
        PyAria2 constructor.

        secret: aria2 secret token
        host: string, aria2 rpc host, default is 'localhost'
        port: integer, aria2 rpc port, default is 6800
        session: string, aria2 rpc session saving.
        """
        server_uri = SERVER_URI_FORMAT % (host, port)
        self._secret = "token:%s" % (secret or "")
        self.server = xmlrpc.client.ServerProxy(server_uri, allow_none=True)

    def addUri(self, uris, options=None, position=None):
        """
        This method adds new HTTP(S)/FTP/BitTorrent Magnet URI.

        uris: list, list of URIs
        options: dict, additional options
        position: integer, position in download queue

        return: This method returns GID of registered download.
        """
        return self.server.aria2.addUri(self._secret, uris, options, position)

    def addTorrent(self, torrent, uris=None, options=None, position=None):
        """
        This method adds BitTorrent download by uploading ".torrent" file.

        torrent: bin, torrent file bin
        uris: list, list of webseed URIs
        options: dict, additional options
        position: integer, position in download queue

        return: This method returns GID of registered download.
        """
        return self.server.aria2.addTorrent(self._secret, xmlrpc.client.Binary(torrent), uris, options, position)

    def addMetalink(self, metalink, options=None, position=None):
        """
        This method adds Metalink download by uploading ".metalink" file.

        metalink: string, metalink file path
        options: dict, additional options
        position: integer, position in download queue

        return: This method returns list of GID of registered download.
        """
        return self.server.aria2.addMetalink(self._secret, xmlrpc.client.Binary(open(metalink, 'rb').read()), options,
                                             position)

    def remove(self, gid):
        """
        This method removes the download denoted by gid.

        gid: string, GID.

        return: This method returns GID of removed download.
        """
        return self.server.aria2.remove(self._secret, gid)

    def forceRemove(self, gid):
        """
        This method removes the download denoted by gid.

        gid: string, GID.

        return: This method returns GID of removed download.
        """
        return self.server.aria2.forceRemove(self._secret, gid)

    def pause(self, gid):
        """
        This method pauses the download denoted by gid.

        gid: string, GID.

        return: This method returns GID of paused download.
        """
        return self.server.aria2.pause(self._secret, gid)

    def pauseAll(self):
        """
        This method is equal to calling aria2.pause() for every active/waiting download.

        return: This method returns OK for success.
        """
        return self.server.aria2.pauseAll(self._secret)

    def forcePause(self, gid):
        """
        This method pauses the download denoted by gid.

        gid: string, GID.

        return: This method returns GID of paused download.
        """
        return self.server.aria2.forcePause(self._secret, gid)

    def forcePauseAll(self):
        """
        This method is equal to calling aria2.forcePause() for every active/waiting download.

        return: This method returns OK for success.
        """
        return self.server.aria2.forcePauseAll()

    def unpause(self, gid):
        """
        This method changes the status of the download denoted by gid from paused to waiting.

        gid: string, GID.

        return: This method returns GID of unpaused download.
        """
        return self.server.aria2.unpause(self._secret, gid)

    def unpauseAll(self):
        """
        This method is equal to calling aria2.unpause() for every active/waiting download.

        return: This method returns OK for success.
        """
        return self.server.aria2.unpauseAll()

    def tellStatus(self, gid, keys=None):
        """
        This method returns download progress of the download denoted by gid.

        gid: string, GID.
        keys: list, keys for method response.

        return: The method response is of type dict and it contains following keys.
        """
        return self.server.aria2.tellStatus(self._secret, gid, keys)

    def getUris(self, gid):
        """
        This method returns URIs used in the download denoted by gid.

        gid: string, GID.

        return: The method response is of type list and its element is of type dict and it contains following keys.
        """
        return self.server.aria2.getUris(self._secret, gid)

    def getFiles(self, gid):
        """
        This method returns file list of the download denoted by gid.

        gid: string, GID.

        return: The method response is of type list and its element is of type dict and it contains following keys.
        """
        return self.server.aria2.getFiles(self._secret, gid)

    def getPeers(self, gid):
        """
        This method returns peer list of the download denoted by gid.

        gid: string, GID.

        return: The method response is of type list and its element is of type dict and it contains following keys.
        """
        return self.server.aria2.getPeers(self._secret, gid)

    def getServers(self, gid):
        """
        This method returns currently connected HTTP(S)/FTP servers of the download denoted by gid.

        gid: string, GID.

        return: The method response is of type list and its element is of type dict and it contains following keys.
        """
        return self.server.aria2.getServers(self._secret, gid)

    def tellActive(self, keys=None):
        """
        This method returns the list of active downloads.

        keys: keys for method response.

        return: The method response is of type list and its element is of type dict and it contains following keys.
        """
        return self.server.aria2.tellActive(self._secret, keys)

    def tellWaiting(self, offset, num, keys=None):
        """
        This method returns the list of waiting download, including paused downloads.

        offset: integer, the offset from the download waiting at the front.
        num: integer, the number of downloads to be returned.
        keys: keys for method response.

        return: The method response is of type list and its element is of type dict and it contains following keys.
        """
        return self.server.aria2.tellWaiting(self._secret, offset, num, keys)

    def tellStopped(self, offset, num, keys=None):
        """
        This method returns the list of stopped download.

        offset: integer, the offset from the download waiting at the front.
        num: integer, the number of downloads to be returned.
        keys: keys for method response.

        return: The method response is of type list and its element is of type dict and it contains following keys.
        """
        return self.server.aria2.tellStopped(self._secret, offset, num, keys)

    def changePosition(self, gid, pos, how):
        """
        This method changes the position of the download denoted by gid.

        gid: string, GID.
        pos: integer, the position relative which to be changed.
        how: string.
             POS_SET, it moves the download to a position relative to the beginning of the queue.
             POS_CUR, it moves the download to a position relative to the current position.
             POS_END, it moves the download to a position relative to the end of the queue.

        return: The response is of type integer and it is the destination position.
        """
        return self.server.aria2.changePosition(self._secret, gid, pos, how)

    def changeUri(self, gid, fileIndex, delUris, addUris, position=None):
        """
        This method removes URIs in delUris from and appends URIs in addUris to download denoted by gid.

        gid: string, GID.
        fileIndex: integer, file to affect (1-based)
        delUris: list, URIs to be removed
        addUris: list, URIs to be added
        position: integer, where URIs are inserted, after URIs have been removed

        return: This method returns a list which contains 2 integers. The first integer is the number of URIs deleted. The second integer is the number of URIs added.
        """
        return self.server.aria2.changeUri(self._secret, gid, fileIndex, delUris, addUris, position)

    def getOption(self, gid):
        """
        This method returns options of the download denoted by gid.

        gid: string, GID.

        return: The response is of type dict.
        """
        return self.server.aria2.getOption(self._secret, gid)

    def changeOption(self, gid, options):
        """
        This method changes options of the download denoted by gid dynamically.

        gid: string, GID.
        options: dict, the options.

        return: This method returns OK for success.
        """
        return self.server.aria2.changeOption(self._secret, gid, options)

    def getGlobalOption(self):
        """
        This method returns global options.

        return: The method response is of type dict.
        """
        return self.server.aria2.getGlobalOption(self._secret)

    def changeGlobalOption(self, options):
        """
        This method changes global options dynamically.

        options: dict, the options.

        return: This method returns OK for success.
        """
        return self.server.aria2.changeGlobalOption(self._secret, options)

    def getGlobalStat(self):
        """
        This method returns global statistics such as overall download and upload speed.

        return: The method response is of type struct and contains following keys.
        """
        return self.server.aria2.getGlobalStat(self._secret)

    def purgeDownloadResult(self):
        """
        This method purges completed/error/removed downloads to free memory.

        return: This method returns OK for success.
        """
        return self.server.aria2.purgeDownloadResult(self._secret)

    def removeDownloadResult(self, gid):
        """
        This method removes completed/error/removed download denoted by gid from memory.

        return: This method returns OK for success.
        """
        return self.server.aria2.removeDownloadResult(self._secret, gid)

    def getVersion(self):
        """
        This method returns version of the program and the list of enabled features.

        return: The method response is of type dict and contains following keys.
        """
        return self.server.aria2.getVersion(self._secret)

    def getSessionInfo(self):
        """
        This method returns session information.

        return: The response is of type dict.
        """
        return self.server.aria2.getSessionInfo(self._secret)

    def shutdown(self):
        """
        This method shutdowns aria2.

        return: This method returns OK for success.
        """
        return self.server.aria2.shutdown(self._secret)

    def forceShutdown(self):
        """
        This method shutdowns aria2.

        return: This method returns OK for success.
        """
        return self.server.aria2.forceShutdown(self._secret)
