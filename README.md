# nas-tools NAS媒体库整理工具
## 功能：
### 1、自动PT下载、做种、转移和重命名
根据配置的关键字，从PT站定时搜刮种子，自动添加qBittorrent任务下载，下载完成后自动识别电影剧集名称并重命名和复制到Emby/Plex媒体库目录下以供识别。
比如电影可配置2022关键字，把2022年新出的资源都自动下载。

### 2、Resilio Sync电影剧集识别转移和命名名
监控Resilio Sync同步目录，识别电影剧集名称，复制并命命名到Emby/Plex媒体库目录以供识别。
这个神Key你值得拥有，大片抢先看：BA6RXJ7YOAOOFV42V6HD56XH4QVIBL2P6

### 3、其他的一些功能
每日签到（PT站、什么值得买、联动营业厅），qBittorrent做种清理、电影预告片搜刮和下载等等，具体看图：
![定时任务](https://github.com/jxxghp/nastool/blob/master/nastool.png)

### 4、消息
支持ServerChan、微信、Telegram消息通知服务， 以上功能运行状态可通过消息服务推送消息到手机上，比如新增加了电影、签到完成等

### 5、Emby WebHook
在Emby WebHooks中设置为 http://IP:3000/emby ，接受Emby消息通知。

### 6、WEB UI管理界面
3000端口访问WEB UI界面



## 安装
### 1、Docker镜像
[jxxghp/nas-tools:latest](https://hub.docker.com/repository/docker/jxxghp/nas-tools)

Docker配置挂载目录：/config，配置文件名：config.ini，根据配置情况把相关目录挂载到容器中或通过[automount]区配置将网络路径直接挂载到容器中

### 2、本地运行
python 3版本

pip install -r requirements.txt 安装依赖

nohup python3 run.py /config/config.ini & 运行

## 配置
参考config/config.ini配置文件示例

按需导入nastool.sql到MySql数据库

