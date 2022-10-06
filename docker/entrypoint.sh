#!/bin/sh

cd ${WORKDIR}
if [ "$NASTOOL_AUTO_UPDATE" = "true" ]; then
    if [ ! -s /tmp/requirements.txt.sha256sum ]; then
        sha256sum requirements.txt > /tmp/requirements.txt.sha256sum
    fi
    if [ ! -s /tmp/third_party.txt.sha256sum ]; then
        sha256sum third_party.txt > /tmp/third_party.txt.sha256sum
    fi
    echo "更新程序..."
    git remote set-url origin ${REPO_URL} &>/dev/null
    echo "windows/" > .gitignore
    echo "third_party/feapder/feapder/network/proxy_file/" >> .gitignore
    git clean -dffx
    git reset --hard HEAD
    git pull
    if [ $? -eq 0 ]; then
        echo "更新成功..."
        hash_old=$(cat /tmp/requirements.txt.sha256sum)
        hash_new=$(sha256sum requirements.txt)
        if [ "$hash_old" != "$hash_new" ]; then
            echo "检测到requirements.txt有变化，重新安装依赖..."
            pip install --upgrade pip setuptools wheel
            pip install -r requirements.txt
            if [ $? -ne 0 ]; then
                echo "无法安装依赖，请更新镜像..."
            else
                echo "依赖安装成功..."
                sha256sum requirements.txt > /tmp/requirements.txt.sha256sum
                hash_old=$(cat /tmp/third_party.txt.sha256sum)
                hash_new=$(sha256sum third_party.txt)
                if [ "$hash_old" != "$hash_new" ]; then
                    echo "检测到third_party.txt有变化，更新第三方组件..."
                    git submodule update --init --recursive
                    if [ $? -ne 0 ]; then
                        echo "无法更新第三方组件，请更新镜像..."
                    else
                        echo "第三方组件安装成功..."
                        sha256sum third_party.txt > /tmp/third_party.txt.sha256sum
                    fi
                fi
            fi
        fi
    else
        echo "更新失败，继续使用旧的程序来启动..."
    fi
else
    echo "程序自动升级已关闭，如需自动升级请在创建容器时设置环境变量：NASTOOL_AUTO_UPDATE=true"
fi

echo "以PUID=${PUID}，PGID=${PGID}的身份启动程序..."
echo "注意：日志将停止打印，请通过文件或WEB页面查看日志"
mkdir -p /config/logs/supervisor
mkdir -p /.local
chown -R ${PUID}:${PGID} ${WORKDIR} /config /usr/lib/chromium /.local
export PATH=$PATH:/usr/lib/chromium
umask ${UMASK}
exec su-exec ${PUID}:${PGID} /usr/bin/supervisord -n -c ${WORKDIR}/supervisord.conf