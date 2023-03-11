import socket


class IpUtils:

    @staticmethod
    def is_ipv4(ip):
        try:
            socket.inet_pton(socket.AF_INET, ip)
        except AttributeError:  # no inet_pton here,sorry
            try:
                socket.inet_aton(ip)
            except socket.error:
                return False
            return ip.count('.') == 3
        except socket.error:  # not a valid ip
            return False
        return True

    @staticmethod
    def is_ipv6(ip):
        try:
            socket.inet_pton(socket.AF_INET6, ip)
        except socket.error:  # not a valid ip
            return False
        return True






