# nas-tools NAS工具合集
## 主要功能：
### 1、媒体文件转移和重命名
支持目录监控和qBittorrent两种方式，自动复制文件到媒体库正式目录并重命名，Emby、Plex完美识别。
支持电影、剧集，支持国产剧集Exx的命名方式，支持剧集按类别分类存放。

qBittorrent：定时自动检测下载完成的文件，识别文件名并从TheMovieDb搜刮媒体信息，复制一份到媒体库正式目录并重命名。

目录监控：被监控目录文件发生变化时，自动触发识别文件名并从TheMovieDb搜刮媒体信息，重命名和复制转移，目前仅能用于ResilioSync配合神Key同步资源。

### 2、Icloud照片同步
定时将Icloud上的照片同步到NAS本地目录，并按时间分目录存放

### 3、自动签到
支持PT站、什么值得买、联动营业厅每日签到

### 4、电影预告片搜刮和下载
从TheMoiveDb中检查预告片信息并从Youtube下载预告片。

目录监听：电影目录发生变化时，比如新增加了影片，则自动触发预告片检索和下载

定时更新：定时从TheMoiveDb中检索正在上映和即将上映的预告本，下载到本地单独目录，可建单独的媒体库进行展示，如已存在对应电影则会进行整合。

### 5、消息服务
ServerChan、微信、Telegram消息通知服务。 以上功能运行状态可通过消息服务推送消息到手机上，比如新增加了电影、签到完成等。
同时监听3000端口，可通过网页发送消息到手机端。

### 6、Emby WebHook
在Emby WebHooks中设置http://IP:3000/emby，则Emby相关状态将通过消息服务发送消息。

### 7、qBittorrent做种清理
根据配置条件定时清理qBittorrent中种子信息，避免无限占用磁盘空间，基于autoremove-torrents实现。

### 8、WEB UI管理界面
3000端口访问WEB UI界面

## 配置说明：
Docker镜像：jxxghp/nas-tools:latest

Docker配置挂载目录：/config

监听端口：3000

配置文件示例如下：
```
[root]
# 日志文件路径，建议放config目录下以便在宿主机查看
logpath=/config/logs

[automount]
# 自动挂载共享目录 远程目录;本地目录;用户名;密码
automount_flag=ON
media=//10.10.10.10/Video;/mnt/media;admin;password
photo=//10.10.10.30/Photo;/mnt/photo;admin;password
pt=
relisiosync=

[qbittorrent]
# qBittorrent配置，用于转移下载完成的文件复制到媒体库目录并重命名
qbhost=10.10.10.250
qbport=8080
qbusername=admin
qbpassword=password

[mysql]
# 数据库记录开关 ON OFF，用于记录媒体文件同步记录和消息发送记录
mysql_flag=ON
# Mysql连接配置
mysql_host=10.10.10.250
mysql_port=3306
mysql_user=root
mysql_pw=password
mysql_db=nastool

[monitor]
# 监听文件夹
# ResilioSync同步文件夹监听开关，用于将ResilioSync同步完成的媒体文件复制到媒体库目录并重命名
resiliosync_flag=ON
# ResilioSync同步文件夹目录
resiliosync_monpath=/mnt/resiliosync/大片抢先看

# 电影文件夹监听开关，用于自动下载预告片、字幕等
movie_flag=ON
# 媒体库电影文件存放目录
movie_monpath=/mnt/media/电影

[rmt]
# 媒体文件转移和重命名工具，支持电影和剧集，支持国产剧集命名方式
# 电影存放目录
rmt_moviepath=/mnt/media
# 剧集存储目录
rmt_tvpath=/mnt/media/电视剧
# 剧集类型，目前不能修改
rmt_tvtype=国产剧,欧美剧,日韩剧,动漫,纪录片,综艺,儿童
# 支持的后缀格式
rmt_mediaext=.mp4,.mkv,.ts
rmt_subext=.srt,.ass
# TMDB API KEY，需要在TheMovieDb申请
rmt_tmdbkey=your tmdb key
# 没有搜刮到信息时强制迁移，qBittorrent传入了分类时才生效
rmt_forcetrans=True
# 欧美国家
rmt_country_ea=['US','FR','GB','DE','ES','IT','NL','PT','RU','UK']
# 亚洲国家
rmt_country_as=['JP','KP','KR','TH','IN','SG']
# qBittorrent Docker的下载保存路径
rmt_qbpath=/downloads/
# qBittorrent Docker下载对应容器的存储路径
rmt_containerpath=/mnt/pt/

[scheduler]
# 定时服务类
# icloudpd，定时执行命名将iCloudpd的照片同步到本地
icloudpd_flag=OFF
icloudpd_cmd=icloudpd -d /mnt/photo -u xxxx@xxx.com -p password --recent 100
icloudpd_interval=43200
# autoremovetorrents，定时清理qBittorrent种子及文件
autoremovetorrents_flag=ON
autoremovetorrents_cmd=autoremove-torrents --conf=/config/autoremove_torrents.yml --log=/config/logs
autoremovetorrents_interval=1800
# hot_movie 从TheMovieDB下载最新的预告片
hottrailer_flag=ON
hottrailer_cron=7:50
hottrailer_total=100
# pt_signin PT站每日签到
ptsignin_flag=ON
ptsignin_cron=7:51
# smzdm 什么值得买每日签到
smzdmsignin_flag=ON
smzdmsignin_cron=7:52
# hiunicom_signin 联动APP每日签到
unicomsignin_flag=ON
unicomsignin_cmd=bash /nas-tools/bin/unicom_signin.sh "$USER" "$PASSWORD" "$APPID"
unicomsignin_cron=7:53
# qb_transfer 定时转移qBittorrent中下载完成的文件到媒体目录并重命名
qbtransfer_flag=ON
qbtransfer_interval=1800

[webhook]
# 不通知的Emby用户或设备  user:device
webhook_ignore=['admin:xx的iPhone 12']
# 发送消息使用的渠道 wechat serverchan telegram
msg_channel=wechat

[wechat]
# 企业微信消息应用，在企业微信中申请
corpid=your wechat corpid
corpsecret=your wechat corpsecret
agentid=your wechat agentid

[serverchan]
# ServerChan API KEY，SCT
sckey=your serverchan key

[telegram]
# Telegram机器人
telegram_token=your telegram token
telegram_bot_id=your telegram bot id

[youtobe]
# 从Youtube下载预告片的命令配置
youtube_dl_cmd=youtube-dl -o "$PATH" "https://www.youtube.com/watch?v=$KEY"
# 预告片存放目录，有对应电影存在时会优先转移到电影目录
hottrailer_path=/mnt/media/预告
# 电影目录，用于检索是否已经存在预告片，存在则不重复下载
movie_path=/mnt/media/电影

[pt]
# PT站签到配置信息，url为签到网页地址，cookie需要在浏览器中抓取
pt_tasks=['ptsbao','pthome','mteam']
ptsbao_url=https://ptsbao.club/mybonus.php
pthome_url=https://pthome.net/attendance.php
mteam_url=https://kp.m-team.cc/mybonus.php
pthome_cookie=
ptsbao_cookie=
mteam_cookie=

[smzdm]
# 什么值得买签到cookie
smzdm_cookie=

[unicom]
# 联通营业厅签到账号、密码及appid配置，appid需要在手机端抓取
unicom_tasks=['186xxxxxxxx:password','186xxxxxxxx:password']
unicom_appid=
```
