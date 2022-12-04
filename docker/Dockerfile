FROM debian:bullseye-slim

RUN apt-get update \
    && apt-get install -y git gcc python3-pip python3-dev libxml2-dev libxslt1-dev tzdata zip curl bash fuse xvfb inotify-tools chromium-driver npm \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && curl https://rclone.org/install.sh | bash \
    && curl https://dl.min.io/client/mc/release/linux-arm/mc --create-dirs -o /usr/bin/mc \
    && chmod +x /usr/bin/mc

RUN apt-get install -y python3-cryptography python3-bs4 python3-cffi python3-lxml python3-pycryptodome python3-selenium python3-urllib3 python3-websocket

RUN npm install pm2 -g \
    && pip install -r https://github.com/geziang/nas-tools/raw/master/requirements.txt
    
RUN useradd -u 911 -U -d /config abc && \
 usermod -G users abc
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache
    
ENV LANG="C.UTF-8" \
    TZ="Asia/Shanghai" \
    NASTOOL_CONFIG="/config/config.yaml" \
    NASTOOL_AUTO_UPDATE=false \
    PS1="\u@\h:\w \$ " \
    REPO_URL="https://github.com/geziang/nas-tools.git" \
    PUID=0 \
    PGID=0 \
    UMASK=000 \
    WORKDIR="/nas-tools"
WORKDIR ${WORKDIR}
RUN python_ver=$(python3 -V | awk '{print $2}') \
    && mkdir /usr/lib/python${python_ver%.*}/site-packages \
    && echo "${WORKDIR}/" > /usr/lib/python${python_ver%.*}/site-packages/nas-tools.pth \
    && ln -s /usr/lib/python3/dist-packages/Cryptodome /usr/lib/python3/dist-packages/Crypto \
    && echo 'fs.inotify.max_user_watches=524288' >> /etc/sysctl.conf \
    && echo 'fs.inotify.max_user_instances=524288' >> /etc/sysctl.conf \
    && git config --global pull.ff only \
    && git clone -b master ${REPO_URL} ${WORKDIR} --recurse-submodule \
    && git config --global --add safe.directory ${WORKDIR}
EXPOSE 3000
VOLUME ["/config"]
ENTRYPOINT ["/nas-tools/docker/entrypoint.sh"]
