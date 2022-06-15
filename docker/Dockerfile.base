FROM alpine
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
    && pip install --upgrade pip setuptools wheel \
    && pip install -r https://raw.githubusercontent.com/jxxghp/nas-tools/master/requirements.txt \
    && rm -rf /tmp/* /root/.cache /var/cache/apk/*
