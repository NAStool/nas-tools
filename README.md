# NAS媒体自动搜刮和整理工具

国内源：https://gitee.com/jxxghp/nas-tools

Docker源：https://hub.docker.com/repository/docker/jxxghp/nas-tools

## 功能：
### 一、PT自动搜刮下载、保种
1) 根据配置的关键字，从PT站定时搜刮种子，自动添加qBittorrent任务下载。比如电影可配置2022关键字，把2022年新出的资源都自动下载。【重点: 识别率很高，具支持国产剧集命名的识别哦，这点很多国外软件都是不支持的。】

2) 下载完成后自动识别电影剧集名称并重命名为Emby/Plex文件名格式，自动复制到Emby/Plex媒体库目录下并自动分好类，实现Emby/Plex 100%完美识别

3) qBittorrent保种，可配置保种时间，避免下载盘被挤爆

### 二、ResilioSync资源同步
监控Resilio Sync同步目录，识别电影剧集名称，自动复制并重命名到Emby/Plex媒体库目录实现100%完美识别

### 三、消息服务
支持ServerChan、微信、Telegram消息通知服务， 以上功能运行状态可通过消息服务推送消息到手机上，比如新增加了电影、签到完成、Emby播放状态（需要在Emby中配置webhook插件）等。

### 四、其它的一些功能
PT站自动签到，qBittorrent删种、电影预告片搜刮和下载（已有电影的预告片、热门预告片）等等。不需要的可以在配置中关掉。


【代码写的比较烂，初学仅限于能实现功能，轻喷。。。】


## 安装
### 1、Docker
```
docker push jxxghp/nas-tools:latest
```
[jxxghp/nas-tools:latest](https://hub.docker.com/repository/docker/jxxghp/nas-tools)

### 2、本地运行
python3.8版本
```
python3 -m pip install -r requirements.txt
nohup python3 run.py -c ./config/config.ini & 
```

### 3、群晖套件
仅适用于dsm6，且只能是admin用户使用。

https://github.com/jxxghp/nas-tools/raw/master/nastool_6.2.3.spk

![image](https://user-images.githubusercontent.com/51039935/153745028-3a9b7e9a-0404-45c0-9674-1763e272c005.png)


## 配置
### 一、申请相关API KEY
1) 在 https://www.themoviedb.org/ 申请用户，得到API KEY：rmt_tmdbkey。

2) 在 https://work.weixin.qq.com/ 申请企业微信自建应用（推荐），获得corpid、corpsecret、agentid，或者在 https://sct.ftqq.com/ 申请 Server酱SendKey：sckey，或者在Telegram中申请自建机器人，获得：telegram_token、telegram_bot_id（具体方法百度）。

3) 申请PT站用户，至少要有1个不然没法玩。

### 二、配置文件
1) 参考 config/config.ini的配置示例进行配置，填入申请好的相关API KEY，以及媒体库电影、电视剧存储路径、PT站RSS信息、qBittorrent信息等等，示例文件中有详细的说明。

2) docker：需要映射/config目录，并将修改好后的config.ini放到配置映射目录下；需要映射WEB访问端口（默认3000）；需要映射媒体库目录及PT下载目录、ResilioSync目录到容器上并与配置文件保持一致。
   
3) 群晖套件：配置文件地址必须为：/homes/admin/.config/nastool/config.ini，即必须是admin用户运行且按路径放置配置文件。

### 三、设置Emby
1) 在Emby的Webhooks插件中，设置地址为：http(s)://IP:3000/emby，勾选“播放事件”和“用户事件（建议只对管理用户勾选）“
2) 按以下目录结构建立文件夹，并分别设置好媒体库（第二级程序会自动建）。
> 电影
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

### 四、配置ResilioSync
1) 安装resiliosync软件，配置好神KEY（主KEY：BCWHZRSLANR64CGPTXRE54ENNSIUE5SMO，大片抢先看：BA6RXJ7YOAOOFV42V6HD56XH4QVIBL2P6，根据主Key的网页也可以使用其他的Key）
   
2) 如果是docker则将ResilioSync资源目录同步映射到docker容器中；如果是群晖套件则需要检查访问权限。均需与配置文件保持一致。

### 五、配置微信应用消息及菜单
如果只是使用消息接受服务，则配置好配置文件中的[wechat]前三个参数就可以了，如果需要通过微信进行控制，则需要按如下方式配置：
1) 配置微信消息服务：在企业微信自建应用管理页面-》API接收消息 开启消息接收服务，URL填写：http(s)://IP:3000/wechat，Token和EncodingAESKey填入配置文件[wechat]区。
   
2) 配置微信菜单控制：有两种方式，一是直接在聊天窗口中输入命令或者PT下载的链接；二是在https://work.weixin.qq.com/wework_admin/frame#apps 应用自定义菜单页面按如下图所示维护好菜单（条目顺序需要一模一样，如果不一样需要修改web/menu.py中定义的菜单序号），菜单内容为发送消息，消息内容为命令。
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


## 使用
1) WEB UI界面，可以修改配置、手工启动服务、修改资源订阅关键字等，用户: admin，密码在配置文件中。
![image](https://user-images.githubusercontent.com/51039935/153804911-0f470480-e250-42e9-a06f-2c2a7e0de627.png)
![image](https://user-images.githubusercontent.com/51039935/153804992-9d7c6dc3-8f6f-47f3-8f46-14ccd33d9542.png)


2) 手机端通知和控制界面，实时接收程序运行状态，控制服务运行（输入命令或者点击菜单）
![image](https://user-images.githubusercontent.com/51039935/151723777-14eb0252-4838-4bdb-9089-75393e6af277.png)

3) 效果（这些分类都是程序自动维护的）
![image](https://user-images.githubusercontent.com/51039935/153733308-498fd68c-4a24-4238-820d-10a1cd1025d1.png)
![image](https://user-images.githubusercontent.com/51039935/151723518-5ee68798-bd24-459a-b99f-43ebe27857e7.png)
![image](https://user-images.githubusercontent.com/51039935/153847136-fee22815-4f89-443a-bac1-617d903cde68.png)

4) 推荐使用1T以上的SSD做为PT下载盘和Resilio Sync的同步盘，大容量硬盘则为存储盘（当前没有也行，分开目录即可）。结合这套程序的PT自动下载转移和定期删种，实现作种和媒体存放分离，Emby/Plex完美搜刮，同时避免PT损伤存储硬盘。可以做到无人值守自动媒体库维护，且资源变化情况均有通知一目了然。


## TODO
1) 支持link方式保种（目前只支持复制转移方式，需要下载和存储分离）
2) 接入豆瓣自动拉取关注电影、电视剧，自动维护订阅关键字
3) PT站资源全局检索（目前依赖RSS订阅，仅支持增量发布内容）
4) 重组代码，插件化、模块化（遥遥无期...）
