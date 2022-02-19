# NAS媒体库资源自动搜刮整理工具

Docker源：https://hub.docker.com/repository/docker/jxxghp/nas-tools

## 功能：
### 1、PT自动搜刮下载、整理、保种
* 根据配置的关键字（PT站种子名称关键字或者电影电视剧的真实名称都可以，前者可正则匹配后者则需完全匹配），从PT站定时搜刮种子，自动添加qBittorrent任务下载（已经有的不会重复下载）。 比如电影可配置为“[\s\.]+2021|2022[\s\.]+”正则式，把2021、2022年新出的资源都自动下载；或者配置为“永恒族”，出现该电影资源时第一时间下载。

* 下载完成后自动识别电影剧集名称并重命名为Emby/Plex文件名格式，自动复制或者硬链接到Emby/Plex媒体库目录下并自动分好类，实现Emby/Plex 100%完美识别【重点: 识别率成功率很高，且支持国产剧集命名的识别，这点很多国外软件都是不支持的】。

* PT保种，【复制模式】或【硬链接模式】自由选择。复制模式可配置保种时间，避免下载盘被挤爆；硬链接模式则适合长期大量保种。

### 2、ResilioSync资源同步
* 监控Resilio Sync同步目录，识别电影剧集名称，自动复制（同步源可能会删内容，所以只支持复制模式）并重命名到Emby/Plex媒体库目录实现100%完美识别。要配合神KEY使用。

### 3、消息服务
* 支持ServerChan、微信、Telegram消息通知服务三选一， 以上功能运行状态可通过消息服务推送消息到手机上，比如新增加了电影、签到完成、Emby播放状态（需要在Emby中配置webhook插件）等。甚至还能在手机上控制服务运行。

### 4、其它的一些功能
* PT站自动签到，qBittorrent定时删种、电影预告片搜刮和下载（已有电影的预告片、热门预告片）等等，不需要的可以在配置中关掉。


【代码写的比较烂，初学仅限于能实现功能，轻喷。。。有玩明白的帮我写个教程，让更多的人受益，不甚感谢！】

## 更新日志
2022.2.19
* 增加存量资源整理工具及说明，支持复制或者硬链接方式将已有的存量资源批量整理成媒体库

2022.2.18
* 配置文件由ini调整为yaml，配置方式更简洁，使用最新版本需要转换一下配置文件
* 增加配置文件检查与日志输出

## 安装
### 1、Docker
[jxxghp/nas-tools:latest](https://hub.docker.com/repository/docker/jxxghp/nas-tools)
```
docker push jxxghp/nas-tools:latest
```

### 2、本地运行
python3.8版本
```
python3 -m pip install -r requirements.txt
nohup python3 run.py -c ./config/config.yaml & 
```

### 3、群晖套件
仅适用于dsm6，且只能是admin用户使用，【要先安装python 3套件，且必须是3.8版本】。

https://github.com/jxxghp/nas-tools/releases

![image](https://user-images.githubusercontent.com/51039935/153745028-3a9b7e9a-0404-45c0-9674-1763e272c005.png)


## 配置
### 1、申请相关API KEY
* 在 https://www.themoviedb.org/ 申请用户，得到API KEY：rmt_tmdbkey。

* 在 https://work.weixin.qq.com/ 申请企业微信自建应用（推荐），获得corpid、corpsecret、agentid，扫描二维码在微信中关注企业自建应用；或者在 https://sct.ftqq.com/ 申请 Server酱SendKey：sckey；或者在Telegram中申请自建机器人，获得：telegram_token、telegram_chat_id（具体方法百度）。

* 申请PT站用户，至少要有1个不然没法玩。点PT的RSS图标获取RSS链接，注意项目标题格式只选中标题，不要勾选其它的，以免误导识别。
![image](https://user-images.githubusercontent.com/51039935/154024206-f2522f1b-7407-46bf-81b4-b147ea304b33.png)


### 2、配置文件
* 确定是用【复制】模式还是【硬链接】模式：复制模式下载做种和媒体库是两份，多占用存储（下载盘大小决定能保多少种），好处是媒体库的盘不用24小时运行可以休眠；硬链接模式不用额外增加存储空间，一份文件两份目录，但需要下载目录和媒体库目录在一个磁盘分区或者存储空间。两者在媒体库使用上是一致的，按自己需要在[pt]rmt_mode按说明配置。

* 参考 config/config.yaml的配置示例进行配置，填入申请好的相关API KEY，以及媒体库电影、电视剧存储路径、PT站RSS信息、qBittorrent信息等等，示例文件中有详细的说明。

* docker：需要映射/config目录，并将修改好后的config.yaml放到配置映射目录下；需要映射WEB访问端口（默认3000）；需要映射媒体库目录及PT下载目录、ResilioSync目录到容器上并与配置文件保持一致。
   
* 群晖套件：配置文件地址必须为：/homes/admin/.config/nastool/config.yaml，即必须是admin用户运行且按路径放置配置文件。

### 3、设置Emby
* 在Emby的Webhooks插件中，设置地址为：http(s)://IP:3000/emby，勾选“播放事件”和“用户事件（建议只对管理用户勾选）“
* 按以下目录结构建立文件夹，并分别设置好媒体库（第二级目录程序会自动建）。
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
* 安装resiliosync软件，配置好神KEY（主KEY：BCWHZRSLANR64CGPTXRE54ENNSIUE5SMO，大片抢先看：BA6RXJ7YOAOOFV42V6HD56XH4QVIBL2P6，根据主Key的网页也可以使用其他的Key）
   
* 如果是docker则将ResilioSync资源目录同步映射到docker容器中；如果是群晖套件则需要检查访问权限。均需与配置文件保持一致。

### 5、配置微信应用消息及菜单（可选）
如果只是使用消息接受服务，则配置好配置文件中的[wechat]前三个参数就可以了，如果需要通过微信进行控制，则需要按如下方式配置：
* 配置微信消息服务：在企业微信自建应用管理页面-》API接收消息 开启消息接收服务，URL填写：http(s)://IP:3000/wechat，Token和EncodingAESKey填入配置文件[wechat]区。
   
* 配置微信菜单控制：有两种方式，一是直接在聊天窗口中输入命令或者PT下载的链接；二是在https://work.weixin.qq.com/wework_admin/frame#apps 应用自定义菜单页面按如下图所示维护好菜单（条目顺序需要一模一样，如果不一样需要修改config.py中定义的WECHAT_MENU菜单序号定义），菜单内容为发送消息，消息内容为命令。
命令与功能的对应关系： 
   
   |  命令   | 功能  |
   |  ----  | ----  |
   | /qbt  | qBittorrent转移 |
   | /qbr  | qBittorrent删种 |
   | /hotm  | 热门预告 |
   | /pts | PT签到 |
   | /mrt  | 预告片下载 |
   | /rst  | ResilioSync同步 |
   | /rss  | RSS下载 |

   ![image](https://user-images.githubusercontent.com/51039935/153850570-b97a2bbc-0961-44d8-85e6-bd5f6215e4a4.png)

### 6、整理存量媒体资源（可选）
经过以上步骤整套程序就已经搭完了，不出意外所有新下载的资源都能自动整理成完美的媒体库了。但是之前已经下载好的资源怎么办？按下面操作，把存量的媒体资源也整理到媒体库里来。
* Docker版本，在宿主机上运行以下命令，nas-tools修改为你的docker名称，/xxx/xxx修改为需要转移的媒体文件目录。
   ```
   docker exec -it nas-tools /bin/bash
   python3 /nas-tools/rmt/media.py -c /config/config.yaml -d /xxx/xxx
   ```
* 群晖套件版本，的在宿主机上运行以下命令，/xxx/xxx修改为需要转移的媒体文件目录，其他不用改。
   ```
   /var/packages/py3k/target/usr/local/bin/python3 /var/packages/nastool/target/rmt/media.py  -c /volume1/homes/admin/.config/nastool/config.yaml -d /xxx/xxx
   ```
* 本地直接运行的，cd 到程序根目录，执行以下命令，/xxx/xxx修改为需要转移的媒体文件目录。
   ```
   python3 rmt/media.py -c config/config.yaml -d /xxx/xxx
   ```

## 使用
1) WEB UI界面，可以修改配置、手工启动服务、修改资源订阅关键字等，用户: admin，密码在配置文件中。
![image](https://user-images.githubusercontent.com/51039935/154681434-5e541cb2-999b-4fde-aac2-62b79e707f6e.png)
![image](https://user-images.githubusercontent.com/51039935/154773429-64dc17ce-5184-4e27-aac5-3fb9b7b342b5.png)


2) 手机端通知和控制界面，实时接收程序运行状态，控制服务运行（输入命令或者点击菜单）
![image](https://user-images.githubusercontent.com/51039935/153968714-47835fa0-1a35-4d77-bfcf-8f24b99396c9.png)


3) 效果（这些分类都是程序自动维护的）
![image](https://user-images.githubusercontent.com/51039935/153886867-50a3debd-e982-4723-974b-04ba16f732b1.png)
![image](https://user-images.githubusercontent.com/51039935/153887369-478433bb-59e1-4520-a16a-6400b817c8b9.png)
![image](https://user-images.githubusercontent.com/51039935/153985095-7dfd7cd8-172b-4f3e-9583-fa25e69d8838.png)

4) 说一下几点使用心得：
* PT下载与媒体库分离模式：复制模式下能避免PT频繁写盘损伤大容量存储盘，同时媒体库盘不观看时还可以休眠，节能减噪，PT推荐使用1TB以上的SSD（当然普通硬盘也行）。硬链接模式我没有用，有需求的可以体验下。
* 自动保种：PT下载完成后是以复制或硬链接并重命名的方式转移到媒体库的，原下载文件还有可以继续保种，复制模式下还可以设置保种时间自动清理。
* 高搜刮识别率：支持国内PT站资源命名识别，同时因为进行了文件夹和文件的重命名，Emby/Plex的识别率几乎是100%。国内连续剧也能轻松识别。
* 全自动：全程不需要人管，有新资源第一时间自动下载整理到媒体库。电影可以设置关键字为 * 或者当前的年份，有新资源无脑下。电视剧则想追哪部再设置哪个的关键字就行，几十T的媒体库轻轻松松。


## TODO
1) 接入豆瓣自动拉取关注电影、电视剧，自动维护订阅关键字
2) PT站资源全局检索（目前依赖RSS订阅，仅支持增量发布内容）
3) 重组代码，插件化、模块化（遥遥无期...）
