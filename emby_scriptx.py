import sys

import requests

if __name__ == "__main__":
    if len(sys.argv) > 5:
        server_name = sys.argv[1]
        user_name = sys.argv[2]
        device_name = sys.argv[3]
        ip = sys.argv[4]
        flag = sys.argv[5]
        req_url = "http://10.10.10.250:3000/emby?server_name=%s&user_name=%s&device_name=%s&ip=%s&flag=%s" \
                  % (server_name, user_name, device_name, ip, flag)
        requests.get(req_url)
