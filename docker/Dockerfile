FROM alpine
ENV LANG="C.UTF-8" \
    TZ="Asia/Shanghai" \
    NASTOOL_CONFIG="/config/config.yaml" \
    NASTOOL_AUTO_UPDATE=1 \
    PS1="\u@\h:\w \$ " \
    PUID=0 \
    PGID=0 \
    UMASK=000
WORKDIR /nas-tools
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories \
    && apk add --no-cache \
       git \
       python3 \
       py3-pip \
       libxml2 \
       libxslt \
       tzdata \
       su-exec \
    && apk add --no-cache --virtual .build \
       gcc \
       musl-dev \
       python3-dev \
       libxml2-dev \
       libxslt-dev \
    && ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && python_ver=$(python3 -V | awk '{print $2}') \
    && echo "/nas-tools/" > /usr/lib/python${python_ver%.*}/site-packages/nas-tools.pth \
    && echo 'fs.inotify.max_user_watches=524288' >> /etc/sysctl.conf \
    && echo 'fs.inotify.max_user_instances=524288' >> /etc/sysctl.conf \
    && git config --global pull.ff only \
    && git clone -b master https://github.com/jxxghp/nas-tools . \
    && pip config set global.index-url https://mirrors.bfsu.edu.cn/pypi/web/simple \
    && pip install pip -U \
    && pip install -r requirements.txt \
    && apk del --purge .build \
    && rm -rf \
       /tmp/* \
       /root/.cache \
       /var/cache/apk/*
VOLUME ["/config"]
ENTRYPOINT ["/nas-tools/docker/entrypoint.sh"]
