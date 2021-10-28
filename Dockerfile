FROM python:3.8-slim-buster
ENV LANG C.UTF-8
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
ADD nas-tools.tar .
WORKDIR /nas-tools
RUN echo "/nas-tools/" > /usr/local/lib/python3.8/site-packages/nas-tools.pth
RUN python3 -m pip install -r /nas-tools/requirements.txt
RUN apt-get update
RUN apt-get install -y --no-install-recommends curl xxd procps nfs-common cifs-utils vim lm-sensors intel-gpu-tools wget
RUN echo fs.inotify.max_user_watches=65535 | tee -a /etc/sysctl.conf
RUN ln -s /nas-tools/bin/rmt.sh /usr/bin/rmtqb
RUN ln -s /nas-tools/bin/run.sh /usr/bin/nastool
RUN chmod +x /nas-tools/bin/*.sh
EXPOSE 3000
CMD ["python3", "/nas-tools/run.py"]