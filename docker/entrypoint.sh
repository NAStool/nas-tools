#!/bin/sh

cd ${WORKDIR}
if [ "$NASTOOL_AUTO_UPDATE" = "true" ]; then
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
            pip install --upgrade pip setuptools wheel
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
    echo "程序自动升级已关闭，如需自动升级请在创建容器时设置环境变量：NASTOOL_AUTO_UPDATE=true"
fi

cat << EOF
       ~7^         !77^         .7?.          .^7?JJJ?!^  :77777777777777777.                               ~JYY.
       JGP?.      .PGG?         ?GGJ         !5GGP5Y5PGY. ~PPPPPPGGGGPPPPPPP:                               ?GGP.
       JGPGP!     .5GG?        7GGGG?       ~GGG7    .^:   ......?GPP^......    ..               .          ?GG5.
       JGPPGGY^   .5GG?       ~GG55GG!      ~GGG?.               ?GPP.      ~?Y5PP5Y?~      .!JY5P55J7:     ?GG5.
       JGG5JPGP?. .5GG?      ^PGG^:PGP~      7PGGPJ!:.           ?GPP:    ^YGG5?!!?5GGY:   !PGGY7!7JPGP?    ?GG5.
       JGG5 ^YGG5!.5GG?     :5GG?  7GGP:      .~?5GGG5?^         ?GPP:   :PGGJ.    .YGG5. !GGP!     ^PGG7   ?GG5.
       JGG5   7PGGYPPG?    .YGG5.  .YGG5.         :!YGGG?        ?GPP:   !GPG^      !GPG^ YGG5       YGG5   ?GG5.
       JGG5    :JGGPPG?    JGPGP5555PGPGY            ?GPG:       ?GPP:   ~GPG~      ?GGP: JGG5.     .5GGY   ?GG5.
       JGG5      ~5GPG?   7GPG7!!!!!!7PPGJ   ^7^:...:JGG5.       ?GPP:    JGG5~.  .7PGG?  :PGGJ:. .:JGGP^   ?GGP.
       JGG5.      .?PG?  !GGG?        7GGG7 :5GGPPPPGGPJ:        ?GGP:     !5PGP55PGPY~    :?5GGP5PGGPJ:    !GGGJ:
       ^!!~         ^?~  ~!!~.         ~!!!. :~!7??7!^.          ^!!~.       :~!77!~:        .^~!77!^.       ^!!~.
EOF

echo "以PUID=${PUID}，PGID=${PGID}的身份启动程序..."
echo "注意：日志将停止打印，请通过文件或WEB页面查看日志"
chown -R ${PUID}:${PGID} /config ${WORKDIR} /var/log/supervisor/
umask ${UMASK}
exec su-exec ${PUID}:${PGID} /usr/bin/supervisord -n -c ${WORKDIR}/supervisord.conf
