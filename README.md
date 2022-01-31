# nas-tools NAS媒体库整理工具
## 功能：
### 1、PT搜刮下载
1) 根据配置的关键字，从PT站定时搜刮种子，自动添加qBittorrent任务下载。比如电影可配置2022关键字，把2022年新出的资源都自动下载

2) qBittorrent下载完成后自动识别电影剧集名称并重命名为Emby/Plex格式，自动复制到Emby/Plex媒体库目录下并自动分好类，重命名后可实现100%完美识别

3) qBittorrent定期删种，避免下载盘被挤爆

### 2、Resilio Sync电影同步
监控Resilio Sync同步目录，识别电影剧集名称，自动复制并重命名到Emby/Plex媒体库目录实现100%完美识别
这个神Key你值得拥有，大片抢先看：BA6RXJ7YOAOOFV42V6HD56XH4QVIBL2P6

### 3、其他的一些功能
每日签到（PT站、什么值得买、联动营业厅），qBittorrent定期删种、电影预告片搜刮和下载、定期同步iCloud中的照片到NAS等等

### 4、消息服务
支持ServerChan、微信、Telegram消息通知服务， 以上功能运行状态可通过消息服务推送消息到手机上，比如新增加了电影、签到完成、Emby播放状态（需要在Emby中配置webhook插件）等。
如果是使用微信渠道，还能实现在微信中直接控制（需要在企业微信中设置菜单，还要改一些代码）


## 安装
### 1、Docker镜像
[jxxghp/nas-tools:latest](https://hub.docker.com/repository/docker/jxxghp/nas-tools)

Docker配置挂载目录：/config，配置文件名：config.ini，根据配置情况把相关目录挂载到容器中或通过[automount]区配置将网络路径直接挂载到容器中

### 2、本地运行
python 3版本

pip install -r requirements.txt 安装依赖

nohup python3 run.py -c ./config/config.ini & 运行

## 配置
1) 参考源码中config/config.ini配置文件示例进行配置，每一个配置项有注释说明

2) 导入nastool.sql到MySql数据库（不是必须）

3) 在Emby WebHooks中设置为 http://IP:3000/emby ，接受Emby消息通知。

## 使用
1) WEB UI界面（3000端口）

![schduler](https://github.com/jxxghp/nas-tools/raw/master/scheduler.png)

2) 手机端通知界面

![image](https://user-images.githubusercontent.com/51039935/151723777-14eb0252-4838-4bdb-9089-75393e6af277.png)

2) Emby和重命名效果（这些分类都是程序自动维护的）

![image](https://github.com/jxxghp/nas-tools/raw/master/emby.png)
![image](https://user-images.githubusercontent.com/51039935/151723518-5ee68798-bd24-459a-b99f-43ebe27857e7.png)

3、推荐使用1T以上的SSD做为PT下载盘和Resilio Sync的同步盘，大容量硬盘则为存储盘，结合这套程序的PT自动下载转移和定期删种，实现作种和媒体存放分离，Emby/Plex完美搜刮，同时避免PT损伤存储硬盘。


