FROM python:3.8-slim-buster
ENV LANG C.UTF-8
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
ADD nas-tools.tar .
WORKDIR /nas-tools
RUN echo "/nas-tools/" > /usr/local/lib/python3.8/site-packages/nas-tools.pth
RUN python3 -m pip install -r /nas-tools/requirements.txt
RUN echo fs.inotify.max_user_watches=65535 | tee -a /etc/sysctl.conf
EXPOSE 3000
CMD ["python3", "/nas-tools/run.py", "-c", "/config/config.ini"]