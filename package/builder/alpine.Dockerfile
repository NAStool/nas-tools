FROM python:3.10.10-alpine AS Builder

ARG branch

ENV NASTOOL_CONFIG=/nas-tools/config/config.yaml
ENV py_site_packages=/usr/local/lib/python3.10/site-packages

RUN apk add build-base git libxslt-dev libxml2-dev musl-dev gcc libffi-dev
RUN pip install --upgrade pip setuptools
RUN pip install wheel cython pyinstaller==5.7.0
RUN git clone --depth=1 -b ${branch} https://github.com/NAStool/nas-tools --recurse-submodule /nas-tools
WORKDIR /nas-tools
RUN pip install -r requirements.txt
RUN pip install pyparsing
RUN cp ./package/rely/hook-cn2an.py ${py_site_packages}/PyInstaller/hooks/ && \
    cp ./package/rely/hook-zhconv.py ${py_site_packages}/PyInstaller/hooks/ && \
    cp ./package/rely/hook-iso639.py ${py_site_packages}/PyInstaller/hooks/ && \
    cp ./third_party.txt ./package/ && \
    mkdir -p ${py_site_packages}/setuptools/_vendor/pyparsing/diagram/ && \
    cp ./package/rely/template.jinja2 ${py_site_packages}/setuptools/_vendor/pyparsing/diagram/ && \
    cp -r ./web/. ${py_site_packages}/web/ && \
    cp -r ./config/. ${py_site_packages}/config/ && \
    cp -r ./scripts/. ${py_site_packages}/scripts/
WORKDIR /nas-tools/package
RUN pyinstaller nas-tools.spec
RUN ls -al /nas-tools/package/dist/
WORKDIR /rootfs
RUN cp /nas-tools/package/dist/nas-tools .

FROM scratch

COPY --from=Builder /rootfs/nas-tools /nas-tools