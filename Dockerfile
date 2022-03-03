FROM python:3.8-slim-buster
ENV LANG C.UTF-8
ENV TZ=Asia/Shanghai
ENV NASTOOL_CONFIG=/config/config.yaml
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
ADD . /nas-tools
WORKDIR /
RUN echo "/nas-tools/" > /usr/local/lib/python3.8/site-packages/nas-tools.pth
RUN python3 -m pip install -r /nas-tools/requirements.txt
RUN apt-get update
RUN apt-get install -y --no-install-recommends procps vim wget git
RUN echo fs.inotify.max_user_watches=524288 | tee -a /etc/sysctl.conf
RUN echo fs.inotify.max_user_instances=524288 | tee -a /etc/sysctl.conf
RUN mv /nas-tools/start.sh /start.sh
RUN chmod +x /start.sh
EXPOSE 3000
CMD ["bash", "/start.sh"]
