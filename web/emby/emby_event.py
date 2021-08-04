from datetime import datetime


class EmbyEvent:
    def __init__(self, input_json):
        event = input_json['Event']
        self.category = event.split('.')[0]
        self.action = event.split('.')[1]
        self.timestamp = datetime.now()

        if self.category == 'playback':
            self.user_name = input_json.get('User', {}).get('Name')
            self.item_type = input_json.get('Item', {}).get('Type')
            if self.item_type == 'Episode':
                self.item_name = input_json.get('Item', {}).get('SeriesName') + ' ' \
                                 + input_json.get('Item', {}).get('Name')
            else:
                self.item_name = input_json.get('Item', {}).get('Name')
            self.provider_ids = input_json.get('Item', {}).get('ProviderIds')
            self.ip = input_json.get('Session', {}).get('RemoteEndPoint')
            self.device_name = input_json.get('Session', {}).get('DeviceName')
            self.client = input_json.get('Session', {}).get('Client')

        if self.category == 'user':
            if self.action == 'login':
                self.user_name = input_json.get('User', {}).get('user_name')
                self.user_name = input_json.get('User', {}).get('user_name')
                self.device_name = input_json.get('User', {}).get('device_name')
                self.ip = input_json.get('User', {}).get('device_ip')
                self.server_name = input_json.get('Server', {}).get('server_name')
                self.status = input_json['Status']
