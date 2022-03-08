from datetime import datetime

from utils.meta.types import MediaType


class EmbyEvent:
    def __init__(self, input_json):
        event = input_json['Event']
        self.category = event.split('.')[0]
        self.action = event.split('.')[1]
        self.timestamp = datetime.now()
        User = input_json.get('User', {})
        Item = input_json.get('Item', {})
        Session = input_json.get('Session', {})
        Server = input_json.get('Server', {})
        Status = input_json.get('Status', {})

        if self.category == 'playback':
            self.user_name = User.get('Name')
            self.item_type = Item.get('Type')
            self.provider_ids = Item.get('ProviderIds')
            if self.item_type == 'Episode':
                self.media_type = MediaType.TV
                self.item_name = "%s %s" % (Item.get('SeriesName'), Item.get('Name'))
                self.tmdb_id = Item.get('SeriesId')
            else:
                self.item_name = Item.get('Name')
                self.tmdb_id = self.provider_ids.get('Tmdb')
                self.media_type = MediaType.MOVIE
            self.ip = Session.get('RemoteEndPoint')
            self.device_name = Session.get('DeviceName')
            self.client = Session.get('Client')

        if self.category == 'user':
            if self.action == 'login':
                self.user_name = User.get('user_name')
                self.user_name = User.get('user_name')
                self.device_name = User.get('device_name')
                self.ip = User.get('device_ip')
                self.server_name = Server.get('server_name')
                self.status = Status

        if self.category == 'item':
            if self.action == 'rate':
                self.movie_name = Item.get('Name')
                self.movie_path = Item.get('Path')
