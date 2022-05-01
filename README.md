# NAS媒体库资源归集整理工具

[![GitHub stars](https://img.shields.io/github/stars/jxxghp/nas-tools?style=plastic)](https://github.com/jxxghp/nas-tools/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/jxxghp/nas-tools?style=plastic)](https://github.com/jxxghp/nas-tools/issues)

Docker：https://hub.docker.com/repository/docker/jxxghp/nas-tools

群晖套件：https://github.com/jxxghp/nas-tools/releases

TG交流：https://t.me/nastool_chat

WIKI：https://github.com/jxxghp/nas-tools/wiki

配置文件模板：https://github.com/jxxghp/nas-tools/blob/master/config/config.yaml

## 功能：

### 1、资源检索
* PT站聚合RSS订阅，实现资源自动追新。

* 通过微信、Telegram或者WEB界面聚合检索资源并择优，最新热门一键搜索或者订阅。

* 在豆瓣中标记，后台自动检索，未出全的自动加入RSS追更。

### 2、媒体识别和重命名
* 监控下载软件，下载完成后自动识别真实名称，硬链接到媒体库并重命名。

* 对目录进行监控，文件变化时自动识别媒体信息硬链接到媒体库并重命名。

* 支持国产剧集，支持动漫，改名后Emby/Jellyfin/Plex 100%搜刮。

### 3、消息服务
* 支持ServerChan、微信、Telegram、Bark等图文消息通知，直接在手机上控制。

### 4、其它
* 自动签到、Emby/Jellyfin播放状态通知等等。


## 更新日志
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
* 优化图文消息推送及媒体识别
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
仅适用于dsm6，要先安装python3套件（版本大于3.7）。

https://github.com/jxxghp/nas-tools/releases


## 配置
### 1、申请相关API KEY
* 申请TMDB用户，在 https://www.themoviedb.org/ 申请用户，得到API KEY，填入rmt_tmdbkey。

* 申请消息通知服务
  1) 微信（推荐）：在 https://work.weixin.qq.com/ 申请企业微信自建应用，获得corpid、corpsecret、agentid，扫描二维码在微信中关注企业自建应用。
  2) Server酱：或者在 https://sct.ftqq.com/ 申请SendKey，填入sckey。
  3) Telegram：关注BotFather申请机器人，关注getuserID拿到chat_id，填入telegram_token、telegram_chat_id。
  4) Bark：安装Bark客户端获得KEY，可以自建Bark服务器或者使用默认的服务器。


### 2、配置文件
* 确定是用【复制】模式还是【硬链接】模式：复制模式下载做种和媒体库是两份，多占用存储（下载盘大小决定能保多少种），好处是媒体库的盘不用24小时运行可以休眠；硬链接模式不用额外增加存储空间，一份文件两份目录，但需要下载目录和媒体库目录在一个磁盘分区或者存储空间。两者在媒体库使用上是一致的，按自己需要按配置文件模板说明配置。

* 有两种运行模式:【全功能模式】、【精简模式】。如果需要全部功能，参考 config/config.yaml的配置示例进行配置；如果只需要精简功能，参考config/simple.yaml的配置示例进行配置，配置好后重命名为config.yaml放配置目录下。
  1) 全功能模式：适用于想搭建PT自动下载、保种、媒体识别改名、PT资源搜索、Emby/Jellyfin播放、消息通知等全自动化整理媒体库的用户，有WEBUI控制界面，WEB默认用户名密码：admin password，端口：3000。
  2) 精简模式：适用于手工进行PT下载，但是希望能自动进行硬链接和媒体识别改名，同时有消息通知的用户，只支持监控下载目录进行自动硬链接改名。

* docker：需要映射/config目录，并将修改好后的config.yaml放到配置映射目录下；全能模式需要映射WEB访问端口（默认3000，精简模式下不需要）；按需映射电影、电视剧及PT下载、资源监控等目录到容器上并与配置一致。
   
* 群晖套件：在套件安装界面中设置配置文件路径，比如：/homes/admin/.config/nastool/config.yaml，并将修改好的配置文件【提前】放置在对应路径下。

### 3、设置Emby/Jellyfin媒体库（推荐）
* 在Emby/Jellyfin的Webhook插件中，设置地址为：http(s)://IP:3000/emby 或 http(s)://IP:3000/jellyfin，勾选“播放事件”和“用户事件（建议只对管理用户勾选）“
* 将Emby/Jellyfin的服务器地址及api key配置到程序中，会用于资源下载和检索控重，提升使用体验。
* 如果启用了默认分类，需按如下的目录结构分别设置好媒体库；如是自定义分类，请按自己的定义建立好媒体库目录，分类定义请参考配置文件模板。
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

### 4、配置目录同步（可选）
* 安装resiliosync软件，配置好神KEY（主KEY：BCWHZRSLANR64CGPTXRE54ENNSIUE5SMO，大片抢先看：BA6RXJ7YOAOOFV42V6HD56XH4QVIBL2P6，也可以使用其他的Key），resiliosync同步目录配置到本程序的监控目录中，实现有资源更新自动整理。
* 其它分散的媒体文件夹，可以过配置目录同步的方式实现文件变化时自动整理到媒体库。

### 5、配置微信菜单/Telegram机器人（推荐）
1) 微信消息菜单

* 配置微信消息接收服务：在企业微信自建应用管理页面-》API接收消息 开启消息接收服务，URL填写：http(s)://IP:3000/wechat，Token和EncodingAESKey填入配置文件[wechat]区（配置好后需要先重启服务，然后才在微信页面中点确定）。
配置完成后可以通过微信发送消息直接检索PT资料下载。
* 配置微信菜单控制：有两种方式，一是直接在聊天窗口中输入命令；二是在https://work.weixin.qq.com/wework_admin/frame#apps 应用自定义菜单页面按如下图所示维护好菜单（条目顺序需要一模一样，如果不一样需要修改config.py中定义的WECHAT_MENU菜单序号定义），菜单内容为发送消息，消息内容为命令。

* ![image](https://user-images.githubusercontent.com/51039935/163518481-d1d4fa43-86e6-4477-a414-8d107f2eecee.png)

2) Telegram Bot机器人

* 在配置文件中设置好本程序的公网地址以及打开telegram webhook开关。
* 在Telegram BotFather机器人中按下表维护好bot命令菜单（也可以不维护），选择菜单或输入命令运行对应服务，输入其它内容则启动PT聚合检索。
* 注意：受Telegram限制，程序运行端口需要设置为以下端口之一：443, 80, 88, 8443

命令与功能对应关系：

   |  命令   | 功能  |
   |  ----  | ----  |
   | /rss  | RSS订阅 |
   | /ptt  | PT下载转移 |
   | /ptr  | PT删种 |
   | /pts | PT站签到 |
   | /rst  | 目录同步 |
   | /db   | 豆瓣收藏 |
   

### 6、配置Jackett/Prowlarr（推荐）
如果你想通过微信、Telegram发送名称后就自动检索，或者使用WEB页面的聚合资源检索功能，则需要配置Jackett/Prowlarr，获取API Key以及Torznab Feed/地址，相关参数填入配置文件。

Jackett/Prowlarr二选一，相关配置参考网上的各类教程。

### 7、整理存量媒体资源（可选）
如果你的存量资源所在的目录与你在配置文件Sync中配置的源路径目的路径相同，则可以通过WEBUI或微信的“目录同步”按钮触发全量同步。 如果不相同则可以按以下说明操作，手工输入命令整理特定目录下的媒体资源。

重要说明：-d 参数为可选，如不输入则会自动区分电影/电视剧/动漫分别存储到配置文件对应的媒体库目录中；-d 参数有输入时则不管类型，都往-d目录中转移。

* Docker版本，宿主机上运行以下命令，nas-tools修改为你的docker名称，修改源目录和目的目录参数。
   ```
   docker exec -it nas-tools sh
   python3 /nas-tools/rmt/filetransfer.py -s /from/path -d /to/path
   ```
* 群晖套件版本，ssh到后台运行以下命令，同样修改配置文件路径以及源目录、目的目录参数。
   ```
   export NASTOOL_CONFIG=/volume1/homes/admin/.config/nastool/config.yaml
   /var/packages/py3k/target/usr/local/bin/python3 /var/packages/nastool/target/rmt/filetransfer.py -s /from/path -d /to/path
   ```
* 本地直接运行的，cd 到程序根目录，执行以下命令，修改配置文件、源目录和目的目录参数。
   ```
   export NASTOOL_CONFIG=/xxx/config/config.yaml
   python3 rmt/filetransfer.py -s /from/path -d /to/path
   ```

## 使用
1) 3000 端口访问 WEB UI界面，可以修改订阅、搜索资源以及启动服务

![image](https://user-images.githubusercontent.com/51039935/163519714-ca2cb339-b5e2-423e-a9d8-b475e2cf9ba2.png)


2) 手机端图文通知和控制界面，控制服务运行（输入命令或者点击菜单）

![image](https://user-images.githubusercontent.com/51039935/163519064-7abad158-0768-450c-82d5-a6a4ae7ccf62.jpg)
![image](https://user-images.githubusercontent.com/51039935/163519547-8aa2e845-6ffe-452b-909d-bf58f23fbb42.jpg)
![image](https://user-images.githubusercontent.com/51039935/163519563-0d06c95f-7b31-43eb-a528-7cc5aa1155aa.jpg)


3) 效果

![image](https://user-images.githubusercontent.com/51039935/153886867-50a3debd-e982-4723-974b-04ba16f732b1.png)

## 鸣谢
* 程序UI模板及图标来源于开源项目<a href="https://github.com/tabler/tabler">tabler</a>
* 感谢 <a href="https://github.com/Qliangw/notion_sync_data" target="_blank">Qliangw</a> 贡献豆瓣部分的代码
* 感谢 <a href="https://hub.docker.com/r/nevinee/nas-tools" target="_blank">nevinee</a> 完善docker构建
* 感谢 PR 代码、完善WIKI、发布教程的所有大佬
