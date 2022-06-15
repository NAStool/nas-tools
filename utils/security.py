import ipaddress

from config import Config


class Security:
    media_server_webhook_allow_ip = {}
    telegram_webhook_allow_ip = {}

    def __init__(self):
        config = Config()
        security = config.get_config('security')
        if security:
            self.media_server_webhook_allow_ip = security.get('media_server_webhook_allow_ip') or {}
            self.telegram_webhook_allow_ip = security.get('telegram_webhook_allow_ip') or {}

    def check_mediaserver_ip(self, ip):
        return self.webhook_allow_access(self.media_server_webhook_allow_ip, ip)

    def check_telegram_ip(self, ip):
        return self.webhook_allow_access(self.telegram_webhook_allow_ip, ip)

    @staticmethod
    def webhook_allow_access(allow_ips, ip):
        """
        判断IP是否合法
        :param allow_ips: 充许的IP范围 {"ipv4":, "ipv6":}
        :param ip: 需要检查的ip
        """
        if not allow_ips:
            return True
        try:
            ipaddr = ipaddress.ip_address(ip)
            if ipaddr.version == 4 or ipaddr.ipv4_mapped:
                if not allow_ips.get('ipv4'):
                    return True
                allow_ipv4s = allow_ips.get('ipv4').split(",")
                for allow_ipv4 in allow_ipv4s:
                    if ipaddr.version == 4 and ipaddr in ipaddress.ip_network(allow_ipv4):
                        return True
                    if ipaddr.ipv4_mapped and ipaddr.ipv4_mapped in ipaddress.ip_network(allow_ipv4):
                        return True
            else:
                if not allow_ips.get('ipv6'):
                    return True
                allow_ipv6s = allow_ips.get('ipv6').split(",")
                for allow_ipv6 in allow_ipv6s:
                    if ipaddr in ipaddress.ip_network(allow_ipv6):
                        return True
        except Exception as e:
            print(str(e))
        return False
