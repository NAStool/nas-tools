# NAS媒体库资源归集整理工具

[![GitHub stars](https://img.shields.io/github/stars/jxxghp/nas-tools?style=plastic)](https://github.com/jxxghp/nas-tools/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/jxxghp/nas-tools?style=plastic)](https://github.com/jxxghp/nas-tools/network/members)
[![GitHub issues](https://img.shields.io/github/issues/jxxghp/nas-tools?style=plastic)](https://github.com/jxxghp/nas-tools/issues)
[![GitHub license](https://img.shields.io/github/license/jxxghp/nas-tools?style=plastic)](https://github.com/jxxghp/nas-tools/blob/master/LICENSE.md)

Docker：https://hub.docker.com/repository/docker/jxxghp/nas-tools

群晖套件：https://github.com/jxxghp/nas-tools/releases

TG频道：https://t.me/nastool

WIKI：https://github.com/jxxghp/nas-tools/wiki

配置文件模板：https://github.com/jxxghp/nas-tools/blob/master/config/config.yaml
（现已可通过WEB界面配置，但里面的注释可以参考）

## 功能：

### 1、资源检索和订阅
* 站点RSS聚合，想看的加入订阅，资源自动实时追新。
* 通过微信、Telegram或者WEB界面聚合资源搜索下载，最新热门资源一键搜索或者订阅。
* 与豆瓣联动，在豆瓣中标记想看后台自动检索下载，未出全的自动加入订阅。

### 2、媒体库整理
* 监控下载软件，下载完成后自动识别真实名称，硬链接到媒体库并重命名。
* 对目录进行监控，文件变化时自动识别媒体信息硬链接到媒体库并重命名。
* 解决保种与媒体库整理冲突的问题，专为中文环境优化，支持国产剧集和动漫，重命名准确率高，改名后Emby/Jellyfin/Plex 100%搜刮。

### 3、站点养护
* 全面的站点数据统计，实时监测你的站点流量情况。
* 全自动化托管养站，支持远程下载器。
* 站点每日自动登录保号。

### 4、消息服务
* 支持ServerChan、微信、Telegram、Bark等图文消息通知
* 支持通过微信、Telegram远程控制订阅和下载。
* Emby/Jellyfin/Plex播放状态通知。


## 更新日志
2022.7.11
* 微信消息推送支持设置代理服务，更加强大的过滤规则设置

2022.7.8
* 新增自动化托管刷流功能

2022.6.11
* 新增订阅日历

2022.6.1
* 新增近期下载
* 新增TMDB缓存管理

2022.5.24
* 新增站点数据统计

2022.5.18
* 支持Opensubtitles.org、ChineseSubFinder下载字幕

2022.5.4
* 支持Plex

2022.5.1
* 支持不识别重命名直接对目录进行硬链接同步

2022.4.27
* RSS支持全局优先规则
* 程序所有设置可通过WEB进行配置

2022.4.23
* 支持设定优先规则检索和下载资源，实现字幕、配音等择优
* RSS及资源检索的过滤规则现在通过WEB页面设置

2022.4.19
* 支持prowlarr做为检索器
* 支持Jellyfin做为媒体服务器
* 支持Telegram Bot远程运行服务及PT检索下载

2022.4.17
* 支持Windows运行
* 优化媒体信息检索匹配

2022.4.14
* 媒体库支持多目录，支持多硬盘/存储空间组媒体库

2022.4.12
* 支持配置代理

2022.4.8
* RSS订阅及PT资源检索支持按关键字和文件大小灵活过滤

2022.4.2
* 支持对识别错误的记录手工重新识别转移
* 支持自定义分类
* 支持动漫识别（使用 <a href="https://github.com/igorcmoura/anitopy" target="_blank">anitopy</a>）

2022.3.27
* 支持查询识别转移历史记录
* 对于自动识别失败的记录，支持手工识别转移

2022.3.18
* 全新的WEB UI，媒体库、搜索、推荐、下载、服务等功能上线

2022.3.13
* 整合 <a href="https://github.com/Qliangw/notion_sync_data" target="_blank">Qliangw</a> 提供的豆瓣同步部分代码，支持同步豆瓣收藏记录，后台自动下载。

2022.3.9
* 支持WEB资源检索，手动选种下载

2022.3.4
* 支持Jackett聚合检索，微信发送关键字直接检索下载

2022.3.3
* 优化文件名识别策略
* RSS订阅机制优化
* Docker启动时自动检查升级
* 通知推送支持Bark

2022.2.28
* 支持RSS简单策略选种
* 优化图文消息推送及媒体整理
* 删除了原来打算整合的原开源代码

2022.2.26
* 新增版本号管理
* 优化目录同步、文件识别、消息推送处理逻辑
* 优化WEBUI RSS关键字设置操作体验

2022.2.24
* 新增下载、转移完成支持图文消息（微信、telegram）
* 目录同步硬链接支持多对多，详情参考配置文件模板注释

2022.2.19
* 增加存量资源整理工具及说明，将已有的存量资源批量整理成媒体库


## 安装
### 1、Docker

教程见 [这里](docker/readme.md) 。

### 2、本地运行
python3版本
```
python3 -m pip install -r requirements.txt
export NASTOOL_CONFIG="/xxx/config/config.yaml"
nohup python3 run.py & 
```

### 3、群晖套件
仅适用于dsm6，依赖python3套件。

套件版本不支持自动升级且部分功能无法使用（比如WEB页面重启和更新），推荐使用Docker版本。

https://github.com/jxxghp/nas-tools/releases


## 配置
### 1、申请相关API KEY
* 申请TMDB用户，在 https://www.themoviedb.org/ 申请用户，得到API KEY。

* 申请消息通知服务
  1) 微信（推荐）：在 https://work.weixin.qq.com/ 申请企业微信自建应用，获得企业ID、自建应用secret、agentid；微信扫描自建应用二维码可实现在微信中使用消息服务，无需打开企业微信。
  2) Server酱：或者在 https://sct.ftqq.com/ 申请SendKey。
  3) Telegram：关注BotFather申请机器人获取token，关注getuserID拿到chat_id。
  4) Bark：安装Bark客户端获得KEY，可以自建Bark服务器或者使用默认的服务器。


### 2、基础配置
* 文件转移模式说明：目前支持五种模式：复制、硬链接、软链接、移动、RCLONE。复制模式下载做种和媒体库是两份，多占用存储（下载盘大小决定能保多少种），好处是媒体库的盘不用24小时运行可以休眠；硬链接模式不用额外增加存储空间，一份文件两份目录，但需要下载目录和媒体库目录在一个磁盘分区或者存储空间；软链接模式就是快捷方式，需要容器内路径与真实路径一致才能正常使用；移动模式会移动和删除原文件及目录；RCLONE模式只针对RCLONE网盘使用场景。

* 启动程序并配置：Docker默认使用3000端口启动（群晖套件默认3003端口），默认用户密码：admin/password（docker需要参考教程提前映射好端口、下载目录、媒体库目录），登录管理界面后，在设置中根据每个配置项的提示在WEB页面修改好配置并重启生效（基础设置中有标红星的是必须要配置的，如TMDB APIKEY等）。详细配置方法可参考默认配置文件的注释及WIKI中的教程。

### 3、设置Emby/Jellyfin/Plex媒体库（推荐）
* 在Emby/Jellyfin/Plex的Webhook插件中，设置地址为：http(s)://IP:PORT/emby、jellyfin、plex，用于接收播放通知
* 将Emby/Jellyfin/Plex的相关信息配置到程序中，会用于资源下载和检索控重，提升使用体验。
* 如果启用了默认分类，需按如下的目录结构分别设置好媒体库；如是自定义分类，请按自己的定义建立好媒体库目录，分类定义请参考default-category.yaml分类配置文件模板。注意，开启二级分类时，媒体库需要将目录设置到二级分类子目录中（可添加多个子目录到一个媒体库，也可以一个子目录设置一个媒体库），否则媒体库管理软件可能无法正常搜刮识别。
   > 电影
   >> 精选
   >> 华语电影
   >> 外语电影
   > 
   > 电视剧
   >> 国产剧
   >> 欧美剧
   >> 日韩剧
   >> 动漫
   >> 纪录片
   >> 综艺
   >> 儿童

### 4、配置同步目录（可选）
* 目录同步可以对多个分散的文件夹进行监控，文件夹中有新增媒体文件时会自动进行识别重命名，并按配置的转移方式转移到媒体库目录或指定的目录中。如将PT下载软件的下载目录也纳入目录同步范围的，建议关闭下载软件监控功能，否则会触发重复处理。

### 5、配置微信菜单/Telegram机器人（推荐）
配置好微信或Telegram机器人后，可以直接通过微信/Telegram机器人发送名字实现自动检索下载，以及控制程序运行。

1) 微信消息推送及回调

* 配置消息推送代理：由于微信官方限制，2022年6月20日后创建的企业微信应用需要有固定的公网IP地址并加入IP白名单后才能接收到消息，使用有固定公网IP的代理服务器转发可解决该问题

    如使用nginx搭建代理服务，需在配置中增加以下代理配置：
    ```
    location /cgi-bin/gettoken {
      proxy_pass https://qyapi.weixin.qq.com;
    }
    location /cgi-bin/message/send {
      proxy_pass https://qyapi.weixin.qq.com; 
    }
    ```

    如使用Caddy搭建代理服务，需在配置中增加以下代理配置（`{upstream_hostport}` 部分不是变量，不要改，原封不动复制粘贴过去即可）。
    ```
    reverse_proxy https://qyapi.weixin.qq.com {
      header_up Host {upstream_hostport}
    }
    ```
    注意：代理服务器仅适用于在微信中接收工具推送的消息，消息回调与代理服务器无关。

* 配置微信消息接收服务：在企业微信自建应用管理页面-》API接收消息 开启消息接收服务：1、在微信页面生成Token和EncodingAESKey，并在NASTool设置->消息通知->微信中填入对应的输入项并保存。2、重启NASTool。3、微信页面地址URL填写：http(s)://IP:PORT/wechat，点确定进行认证。
*配置微信菜单控制：1、在https://work.weixin.qq.com/wework_admin/frame#apps 应用自定义菜单页面按如下图所示维护好菜单，菜单内容为发送消息，消息内容随意（一级菜单及一级菜单下的前几个子菜单顺序需要一模一样，在符合截图的示例项后可以自己增加别的二级菜单项），通过菜单远程控制工具运行。2、通过微信发送电影电视剧名称，或者“订阅”加电影电视剧名称，可以实现远程搜索和订阅，详细使用方法参考WIKI说明。

  ![image](https://user-images.githubusercontent.com/51039935/170855173-cca62553-4f5d-49dd-a255-e132bc0d8c3e.png)

2) Telegram Bot机器人

* 在NASTool设置中设置好本程序的外网访问地址以及打开Telegram Webhook开关。
* 在Telegram BotFather机器人中按下表维护好bot命令菜单（也可以不维护），选择菜单或输入命令运行对应服务，输入其它内容则启动PT聚合检索。
* 注意：受Telegram限制，程序运行端口需要设置为以下端口之一：443, 80, 88, 8443，且需要有以网认证的Https证书。

命令与功能对应关系：

   |  命令   | 功能  |
   |  ----  | ----  |
   | /rss  | RSS订阅 |
   | /ptt  | PT下载转移 |
   | /ptr  | PT删种 |
   | /pts | PT站签到 |
   | /rst  | 目录同步 |
   | /db   | 豆瓣想看 |
   

### 6、配置Jackett/Prowlarr（推荐）
如果你想通过微信、Telegram发送名称后就自动检索，或者使用WEB页面的聚合资源检索功能，则需要获取API Key以及Torznab Feed/地址等，配置到设置->索引器->Jackett/Prowlarr中。

Jackett/Prowlarr二选一，但推荐使用Jackett，支持并发且支持副标题识别。

### 7、配置站点（推荐）
本工具的电影电视剧订阅、站点数据统计、刷流等功能均依赖于正确配置站点信息，需要在“站点管理->站点维护”中维护好站点RSS链接以及Cookie等。其中站点RSS链接生成时请尽量选择影视类资源分类，且勾选副标题。

### 8、整理存量媒体资源（可选）
如果你的存量资源所在的目录与你目录同步中配置的源路径目的路径相同，则可以通过WEBUI或微信/Telegram的“目录同步”按钮触发全量同步。 如果不相同则可以按以下说明操作，手工输入命令整理特定目录下的媒体资源。

重要说明：-d 参数为可选，如不输入则会自动区分电影/电视剧/动漫分别存储到对应的媒体库目录中；-d 参数有输入时则不管类型，都往-d目录中转移。

* Docker版本，宿主机上运行以下命令，nas-tools修改为你的docker名称，修改源目录和目的目录参数。
   ```
   docker exec -it nas-tools sh
   python3 /nas-tools/rmt/filetransfer.py -s /from/path -d /to/path
   ```
* 群晖套件版本，ssh到后台运行以下命令，同样修改配置文件路径以及源目录、目的目录参数。
   ```
   export NASTOOL_CONFIG=/volume1/NASTOOL/config.yaml
   /var/packages/py3k/target/usr/local/bin/python3 /var/packages/nastool/target/rmt/filetransfer.py -s /from/path -d /to/path
   ```
* 本地直接运行的，cd 到程序根目录，执行以下命令，修改配置文件、源目录和目的目录参数。
   ```
   export NASTOOL_CONFIG=/xxx/config.yaml
   python3 rmt/filetransfer.py -s /from/path -d /to/path
   ```

## 鸣谢
* 程序UI模板及图标来源于开源项目<a href="https://github.com/tabler/tabler">tabler</a>，此外项目中还使用到了开源模块：<a href="https://github.com/igorcmoura/anitopy" target="_blank">anitopy</a>、<a href="https://github.com/AnthonyBloomer/tmdbv3api" target="_blank">tmdbv3api</a>、<a href="https://github.com/pkkid/python-plexapi" target="_blank">python-plexapi</a>、<a href="https://github.com/rmartin16/qbittorrent-api">qbittorrent-api</a>、<a href="https://github.com/Trim21/transmission-rpc">transmission-rpc</a>等
* 感谢 <a href="https://github.com/devome" target="_blank">nevinee</a> 完善docker构建
* 感谢 <a href="https://github.com/tbc0309" target="_blank">tbc0309</a> 适配群晖套件
* 感谢 PR 代码、完善WIKI、发布教程的所有大佬
