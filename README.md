# nas-tools NAS工具集
## 功能：
### 1、qBittorrent下载电影剧集识别转移和重命名
定时检测qbittorrent，下载完成后识别电影剧集名称并从TheMovieDb搜刮媒体信息，复制到Emby/Plex媒体库目录并重命名，命名格式："名称 (年份)/名称 (年份) - 分辨率.后缀"

### 2、Resilio Sync电影剧集识别转移和命名名
监控Resilio Sync同步结果目录，识别电影剧集名称并从TheMovieDb搜刮媒体信息，复制到Emby/Plex媒体库目录并重命名，命名格式："名称 (年份)/名称 (年份) - 分辨率.后缀"

### 3、定时任务
PT站、什么值得买、联动营业厅每日签到，qBittorrent做种清理、电影预告片搜刮和下载，具体看图：
![定时任务](https://github.com/jxxghp/nastool/blob/master/nastool.png)

### 4、消息
支持ServerChan、微信、Telegram消息通知服务， 以上功能运行状态可通过消息服务推送消息到手机上，比如新增加了电影、签到完成等

### 5、Emby WebHook
在Emby WebHooks中设置为 http://IP:3000/emby ，则Emby相关播放状态将通过消息服务发送消息到手机

### 6、WEB UI管理界面
3000端口访问WEB UI界面



## 安装
### 1、Docker镜像
[jxxghp/nas-tools:latest](https://hub.docker.com/repository/docker/jxxghp/nas-tools)

Docker配置挂载目录：/config，配置文件名：config.ini，根据配置情况把相关目录挂载到容器中或通过[automount]区配置将网络路径直接挂载到容器中

### 2、本地运行
python 3版本
pip install -r requirements.txt 安装依赖
nohub python3 run.py & 运行

## 配置
参考config/config.ini配置文件示例
