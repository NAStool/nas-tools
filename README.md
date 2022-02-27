# NAS媒体库资源自动搜刮整理工具

Docker源：https://hub.docker.com/repository/docker/jxxghp/nas-tools

TG交流：https://t.me/nastool_chat

## 功能：
### 1、PT自动下载
* 通过订阅PT站RSS以及配置过滤关键字，实现PT资源自动检索追新，可用于快速累积媒体库资源、追剧、追未出资源的电影等，支持qBittorrent或transmission客户端。

* 在豆瓣发现想看的电影进行标记，或者微信直接发送电影电视剧名称，系统自动在各PT站检索资源并添加下载【开发中】。

### 2、媒体识别和重命名
* 监控下载软件，下载完成后自动识别真实名称，硬链接到媒体库并重命名。

* 对目录进行监控，目录下新增了影视文件时，自动识别媒体信息硬链接到媒体库并重命名。

* 支持国产剧集，针对PT站种子名称优化，重命名成功率高，Emby/Plex 100%搜刮。

### 3、消息服务
* 支持ServerChan、微信、Telegram等图文消息通知， 新增下载转移状态推送消息到手机上，还能在手机上控制服务运行。

### 4、其它
* PT站自动签到，电影预告片搜刮和下载，Emby播放状态通知等等。


## 更新日志
2022.2.26
* 新增版本号管理
* 优化目录监控、文件识别、消息推送处理逻辑
* 优化WEBUI RSS关键字设置操作体验

2022.2.24
* 新增下载、转移完成支持图文消息（微信、telegram）
* 目录监控硬链接支持多对多，详情参考配置文件模板注释

2022.2.23
* 支持关闭电影、电视剧的自动分类功能，新增配置项：media.movie_subtypedir、media.tv_subtypedir，未配置默认开
* 支持对目录进行监控，发现文件变化时自动复制或硬链接并重命名，修改配置项：media.resiliosync_path -> media.sync_path，新增配置项：media.sync_mod
* 部分没什么用的功能支持关闭（配置项配空），同时管理页面不显示，新增配置：media.movie_trailer
* 支持精简模式，只有两个功能：1、监控下载软件，下载完成后自动做硬链接/复制；2、监控目录，目录有变化时自动硬链接/复制。没有UI界面及消息服务，使用simple.yaml模板配置。

2022.2.21
* 支持qbittorrent、transmission两种PT客户端（强烈推荐使用qb），注意新加了配置项：pt->pt_client

2022.2.19
* 增加存量资源整理工具及说明，支持复制或者硬链接方式将已有的存量资源批量整理成媒体库

2022.2.18
* 配置文件由ini调整为yaml，配置方式更简洁，使用最新版本需要转换一下配置文件
* 增加配置文件检查与日志输出

## 安装
### 1、Docker
[jxxghp/nas-tools:latest](https://hub.docker.com/repository/docker/jxxghp/nas-tools)
```
docker pull jxxghp/nas-tools:latest
```

### 2、本地运行
python3.8版本
```
python3 -m pip install -r requirements.txt
export NASTOOL_CONFIG="/xxx/config/config.yaml"
nohup python3 run.py & 
```

### 3、群晖套件
仅适用于dsm6，要先安装python3套件（版本大于3.7）。

https://github.com/jxxghp/nas-tools/releases

![image](https://user-images.githubusercontent.com/51039935/155314082-47d5c637-6659-4c32-a12a-d2678cff93fe.png)

## 配置
### 1、申请相关API KEY
* 在 https://www.themoviedb.org/ 申请用户，得到API KEY：rmt_tmdbkey。

* 在 https://work.weixin.qq.com/ 申请企业微信自建应用（推荐），获得corpid、corpsecret、agentid，扫描二维码在微信中关注企业自建应用；或者在 https://sct.ftqq.com/ 申请 Server酱SendKey：sckey；或者在Telegram中申请自建机器人，获得：telegram_token（关注BotFather生成机器人）、telegram_chat_id（关注getuserID拿到ID）。

* 申请PT站用户，至少要有1个不然没法玩。点PT的RSS图标获取RSS链接，注意项目标题格式只选中标题，不要勾选其它的，以免误导识别。
![image](https://user-images.githubusercontent.com/51039935/154024206-f2522f1b-7407-46bf-81b4-b147ea304b33.png)

RSS链接不要用错了，是下载客户端使用的那个。


### 2、配置文件
* 确定是用【复制】模式还是【硬链接】模式：复制模式下载做种和媒体库是两份，多占用存储（下载盘大小决定能保多少种），好处是媒体库的盘不用24小时运行可以休眠；硬链接模式不用额外增加存储空间，一份文件两份目录，但需要下载目录和媒体库目录在一个磁盘分区或者存储空间。两者在媒体库使用上是一致的，按自己需要按配置文件模板说明配置。

* 有两种运行模式:【全功能模式】、【精简模式】。如果需要全部功能，参考 config/config.yaml的配置示例进行配置；如果只需要精简功能，参考config/simple.yaml的配置示例进行配置，配置好后重命名为config.yaml放配置目录下。
  1) 全功能模式：适用于想搭建PT自动下载、保种、媒体识别改名、Emby播放、消息通知、预告等全自动化整理媒体库的用户，有WEBUI控制界面。
  2) 精简模式：适用于手工进行PT下载，但是希望能自动进行硬链接和媒体识别改名，同时有消息通知的用户，支持监控下载软件进行硬链接改名以及监控下载目录进行硬链接改名两种方式，没有WEBUI控制界面。

* docker：需要映射/config目录，并将修改好后的config.yaml放到配置映射目录下；全能模式需要映射WEB访问端口（默认3000，精简模式下不需要）；按需映射电影、电视剧及PT下载、资源监控等目录到容器上并与配置一致。
   
* 群晖套件：在套件安装界面中设置配置文件路径，比如：/homes/admin/.config/nastool/config.yaml，并将修改好的配置文件【提前】放置在对应路径下。

### 3、设置Emby（可选）
* 在Emby的Webhooks插件中，设置地址为：http(s)://IP:3000/emby，勾选“播放事件”和“用户事件（建议只对管理用户勾选）“
* 如果启用了自动分类功能，会是如下的目录结构，分别设置好媒体库（自动分类可选，不想分类的可关闭）。
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
   > 
   > 预告

### 4、配置ResilioSync（可选）
* 安装resiliosync软件，配置好神KEY（主KEY：BCWHZRSLANR64CGPTXRE54ENNSIUE5SMO，大片抢先看：BA6RXJ7YOAOOFV42V6HD56XH4QVIBL2P6，也可以使用其他的Key），同步目录注意要配置到本程序的监控目录中。

### 5、配置微信应用消息及菜单（可选）
如果只是使用消息接受服务，则配置好配置文件中的[wechat]前三个参数就可以了，如果需要通过微信进行控制，则需要按如下方式配置：
* 配置微信消息服务：在企业微信自建应用管理页面-》API接收消息 开启消息接收服务，URL填写：http(s)://IP:3000/wechat，Token和EncodingAESKey填入配置文件[wechat]区。
   
* 配置微信菜单控制：有两种方式，一是直接在聊天窗口中输入命令或者PT下载的链接；二是在https://work.weixin.qq.com/wework_admin/frame#apps 应用自定义菜单页面按如下图所示维护好菜单（条目顺序需要一模一样，如果不一样需要修改config.py中定义的WECHAT_MENU菜单序号定义），菜单内容为发送消息，消息内容为命令。
命令与功能的对应关系： 
   
   |  命令   | 功能  |
   |  ----  | ----  |
   | /rss  | RSS下载 |
   | /ptt  | PT文件转移 |
   | /ptr  | PT删种 |
   | /pts | PT自动签到 |
   | /hotm  | 热门预告片 |
   | /mrt  | 本地电影预告 |
   | /rst  | 资源同步 |
   
   ![image](https://user-images.githubusercontent.com/51039935/155314403-f5e9836b-abea-47f7-af0c-6f74edb16d3b.png)


### 6、整理存量媒体资源（可选）
经过以上步骤整套程序就已经搭完了，不出意外所有新下载的资源都能自动整理成完美的媒体库了。但是之前已经下载好的资源怎么办？按下面操作，把存量的媒体资源也整理到媒体库里来。

重要说明：-d 参数为可选，如不输入则会自动区分电影还是电视剧分别存储到配置文件对应的电影电视剧媒体库目录中；-d 参数有输入时则不管是电影还是电视剧，都往-d目录中转移。

* Docker版本，宿主机上运行以下命令，nas-tools修改为你的docker名称，修改源目录和目的目录参数。
   ```
   docker exec -it nas-tools /bin/bash
   python3 /nas-tools/rmt/media.py -s /from/path -d /to/path
   ```
* 群晖套件版本，ssh到后台运行以下命令，同样修改配置文件路径以及源目录、目的目录参数。
   ```
   export NASTOOL_CONFIG=/volume1/homes/admin/.config/nastool/config.yaml
   /var/packages/py3k/target/usr/local/bin/python3 /var/packages/nastool/target/rmt/media.py -s /from/path -d /to/path
   ```
* 本地直接运行的，cd 到程序根目录，执行以下命令，修改配置文件、源目录和目的目录参数。
   ```
   export NASTOOL_CONFIG=/xxx/config/config.yaml
   python3 rmt/media.py -s /from/path -d /to/path
   ```

## 使用
1) WEB UI界面，可以修改配置、手工启动服务（仅全功能模式支持）
![image](https://user-images.githubusercontent.com/51039935/155827426-e013dfe5-87dd-4cee-a0e4-56a1966a8fbd.png)
![image](https://user-images.githubusercontent.com/51039935/155827403-537d8b29-94df-40fe-8f11-0c3c626646c0.png)

2) 手机端图文通知和控制界面，控制服务运行（输入命令或者点击菜单）
![IMG_2768](https://user-images.githubusercontent.com/51039935/155554473-a505dc3d-f5e4-46c5-8b3c-59aa8edda2a2.jpeg)

3) 效果
![image](https://user-images.githubusercontent.com/51039935/153886867-50a3debd-e982-4723-974b-04ba16f732b1.png)
![image](https://user-images.githubusercontent.com/51039935/153887369-478433bb-59e1-4520-a16a-6400b817c8b9.png)
![image](https://user-images.githubusercontent.com/51039935/153985095-7dfd7cd8-172b-4f3e-9583-fa25e69d8838.png)

## TODO
1) 同一资源有多个版本时支持策略选种
2) 自定义分类
3) PT全局资源检索
4) 通过豆瓣或者微信消息自动检索下载
