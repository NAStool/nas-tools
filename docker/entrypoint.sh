#!/bin/sh

cd /nas-tools
if [ -n $NASTOOL_AUTO_UPDATE ]; then
    if [ ! -s /tmp/requirements.txt.sha256sum ]; then
        sha256sum requirements.txt > /tmp/requirements.txt.sha256sum
    fi
    echo "更新程序..."
    git remote set-url origin ${REPO_URL} &>/dev/null
    git pull
    if [ $? -eq 0 ]; then
        echo "更新成功..."
        hash_old=$(cat /tmp/requirements.txt.sha256sum)
        hash_new=$(sha256sum requirements.txt)
        if [ "$hash_old" != "$hash_new" ]; then
            echo "检测到requirements.txt有变化，重新安装依赖..."
            pip install -r requirements.txt
            if [ $? -ne 0 ]; then
                echo "无法安装依赖，请更新镜像..."
            else
                echo "依赖安装成功..."
                sha256sum requirements.txt > /tmp/requirements.txt.sha256sum
            fi
        fi
    else
        echo "更新失败，继续使用旧的程序来启动..."
    fi
else
    echo "程序自动升级已关闭，如需打开请设置环境变量：NASTOOL_AUTO_UPDATE 为任意值..."
fi

echo "以PUID=${PUID}，PGID=${PGID}的身份启动程序..."
chown -R ${PUID}:${PGID} /config /nas-tools
umask $UMASK
exec su-exec ${PUID}:${PGID} python3 run.py
