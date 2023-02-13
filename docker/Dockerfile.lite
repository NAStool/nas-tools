FROM alpine
RUN apk add --no-cache libffi-dev  \
    git  \
    gcc  \
    musl-dev  \
    python3-dev  \
    py3-pip  \
    libxml2-dev  \
    libxslt-dev  \
    tzdata  \
    su-exec  \
    dumb-init  \
    npm \
    && ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && pip install --upgrade pip setuptools wheel \
    && pip install cython \
    && pip install -r https://raw.githubusercontent.com/jxxghp/nas-tools/master/requirements.txt \
    && npm install pm2 -g \
    && apk del --purge libffi-dev gcc musl-dev libxml2-dev libxslt-dev \
    && pip uninstall -y cython \
    && rm -rf /tmp/* /root/.cache /var/cache/apk/*
ENV LANG="C.UTF-8" \
    TZ="Asia/Shanghai" \
    NASTOOL_CONFIG="/config/config.yaml" \
    NASTOOL_AUTO_UPDATE=false \
    NASTOOL_CN_UPDATE=true \
    NASTOOL_VERSION=lite \
    PS1="\u@\h:\w \$ " \
    REPO_URL="https://github.com/jxxghp/nas-tools.git" \
    PYPI_MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple" \
    ALPINE_MIRROR="mirrors.ustc.edu.cn" \
    PUID=0 \
    PGID=0 \
    UMASK=000 \
    WORKDIR="/nas-tools"
WORKDIR ${WORKDIR}
RUN python_ver=$(python3 -V | awk '{print $2}') \
    && echo "${WORKDIR}/" > /usr/lib/python${python_ver%.*}/site-packages/nas-tools.pth \
    && echo 'fs.inotify.max_user_watches=524288' >> /etc/sysctl.conf \
    && echo 'fs.inotify.max_user_instances=524288' >> /etc/sysctl.conf \
    && git config --global pull.ff only \
    && git clone -b master ${REPO_URL} ${WORKDIR} --depth=1 --recurse-submodule \
    && git config --global --add safe.directory ${WORKDIR}
EXPOSE 3000
VOLUME ["/config"]
ENTRYPOINT ["/nas-tools/docker/entrypoint.sh"]