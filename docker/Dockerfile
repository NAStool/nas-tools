FROM alpine
ENV LANG="C.UTF-8" \
    TZ="Asia/Shanghai" \
    NASTOOL_CONFIG="/config/config.yaml" \
    NASTOOL_AUTO_UPDATE=false \
    PS1="\u@\h:\w \$ " \
    REPO_URL="https://github.com/jxxghp/nas-tools.git" \
    PUID=0 \
    PGID=0 \
    UMASK=000 \
    WORKDIR="/nas-tools"
WORKDIR ${WORKDIR}
RUN apk add --no-cache \
       git \
       gcc \
       musl-dev \
       python3-dev \
       py3-pip \
       libxml2-dev \
       libxslt-dev \
       tzdata \
       su-exec \
    && ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && python_ver=$(python3 -V | awk '{print $2}') \
    && echo "${WORKDIR}/" > /usr/lib/python${python_ver%.*}/site-packages/nas-tools.pth \
    && echo 'fs.inotify.max_user_watches=524288' >> /etc/sysctl.conf \
    && echo 'fs.inotify.max_user_instances=524288' >> /etc/sysctl.conf \
    && git config --global pull.ff only \
    && git clone -b master ${REPO_URL} --depth=1 ${WORKDIR} \
    && git config --global --add safe.directory ${WORKDIR} \
    && pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt \
    && mkdir -p /var/log/supervisor \
    && rm -rf \
       /tmp/* \
       /root/.cache \
       /var/cache/apk/*
VOLUME ["/config"]
ENTRYPOINT ["/nas-tools/docker/entrypoint.sh"]
