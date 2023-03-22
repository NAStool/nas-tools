#!/bin/sh

cd ${WORKDIR}

# 自动更新
if [ "${NASTOOL_AUTO_UPDATE}" = "true" ]; then
    if [ ! -s /tmp/requirements.txt.sha256sum ]; then
        sha256sum requirements.txt > /tmp/requirements.txt.sha256sum
    fi
    if [ ! -s /tmp/third_party.txt.sha256sum ]; then
        sha256sum third_party.txt > /tmp/third_party.txt.sha256sum
    fi
    if [ ! -s /tmp/package_list.txt.sha256sum ]; then
        sha256sum package_list.txt > /tmp/package_list.txt.sha256sum
    fi
    echo "更新程序..."
    git remote set-url origin "${REPO_URL}" &> /dev/null
    echo "windows/" > .gitignore
    # 更新分支
    if [ "${NASTOOL_VERSION}" == "dev" ]; then
      branch="dev"
    else
      branch="master"
    fi

    git clean -dffx
    git fetch --depth 1 origin ${branch}
    git reset --hard origin/${branch}

    if [ $? -eq 0 ]; then
        echo "更新成功..."
        # Python依赖包更新
        hash_old=$(cat /tmp/requirements.txt.sha256sum)
        hash_new=$(sha256sum requirements.txt)
        if [ "${hash_old}" != "${hash_new}" ]; then
            echo "检测到requirements.txt有变化，重新安装依赖..."
            if [ "${NASTOOL_CN_UPDATE}" = "true" ]; then
                pip install --upgrade pip setuptools wheel -i "${PYPI_MIRROR}"
                pip install -r requirements.txt -i "${PYPI_MIRROR}"
            else
                pip install --upgrade pip setuptools wheel
                pip install -r requirements.txt
            fi
            if [ $? -ne 0 ]; then
                echo "无法安装依赖，请更新镜像..."
            else
                echo "依赖安装成功..."
                sha256sum requirements.txt > /tmp/requirements.txt.sha256sum
                hash_old=$(cat /tmp/third_party.txt.sha256sum)
                hash_new=$(sha256sum third_party.txt)
                if [ "${hash_old}" != "${hash_new}" ]; then
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
        # 系统软件包更新
        hash_old=$(cat /tmp/package_list.txt.sha256sum)
        hash_new=$(sha256sum package_list.txt)
        if [ "${hash_old}" != "${hash_new}" ]; then
            echo "检测到package_list.txt有变化，更新软件包..."
            if [ "${NASTOOL_CN_UPDATE}" = "true" ]; then
                sed -i "s/dl-cdn.alpinelinux.org/${ALPINE_MIRROR}/g" /etc/apk/repositories
                apk update -f
            fi
            apk add --no-cache libffi-dev
            apk add --no-cache $(echo $(cat package_list.txt))
            if [ $? -ne 0 ]; then
                echo "无法更新软件包，请更新镜像..."
            else
                echo "软件包安装成功..."
                sha256sum package_list.txt > /tmp/package_list.txt.sha256sum
            fi
        fi
    else
        echo "更新失败，继续使用旧的程序来启动..."
    fi
else
    echo "程序自动升级已关闭，如需自动升级请在创建容器时设置环境变量：NASTOOL_AUTO_UPDATE=true"
fi

echo "以PUID=${PUID}，PGID=${PGID}的身份启动程序..."

# /nas-tools/下除.git|.github之外 chown
find ${WORKDIR} -maxdepth 1 -not \( -path "${WORKDIR}/.git" -prune \) -not \( -path "${WORKDIR}/.github" -prune \) -exec chown -R "${PUID}":"${PGID}" {} \;
# 创建目录、权限设置
mkdir -p /.pm2 /.local
chown -R "${PUID}":"${PGID}" /config /.pm2 /etc/hosts /usr/lib/chromium /.local
# 避免 issue #3816，减少 chown 操作
if [ "$(stat -c %u .git)":"$(stat -c %g .git)" != "${PUID}":"${PGID}" ]; then
  find .git ! -user "${PUID}" -a ! -group "${PGID}" -exec chown "${PUID}":"${PGID}" {} \;
  find .github ! -user "${PUID}" -a ! -group "${PGID}" -exec chown "${PUID}":"${PGID}" {} \;
fi
export PATH=${PATH}:/usr/lib/chromium

# 掩码设置
umask "${UMASK}"

# 启动Redis
if [ -n "$(which redis-server)" ]; then
    echo "启动Redis..."
    redis-server --daemonize yes
fi

# 启动主程序
exec su-exec "${PUID}":"${PGID}" "$(which dumb-init)" "$(which pm2-runtime)" start run.py -n NAStool --interpreter python3
