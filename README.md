# NAS媒体自动搜刮和整理工具

国内源：https://gitee.com/jxxghp/nas-tools

Docker源：https://hub.docker.com/repository/docker/jxxghp/nas-tools

## 功能：
### 1、PT自动搜刮下载
1) 根据配置的关键字，从PT站定时搜刮种子，自动添加qBittorrent任务下载。比如电影可配置2022关键字，把2022年新出的资源都自动下载。【重点: 识别率很高，具支持国产剧集命名的识别哦，这点很多国外软件都是不支持的。】

2) 下载完成后自动识别电影剧集名称并重命名为Emby/Plex文件名格式，自动复制到Emby/Plex媒体库目录下并自动分好类，实现Emby/Plex 100%完美识别

3) qBittorrent定期删种，避免下载盘被挤爆

### 2、ResilioSync资源同步
监控Resilio Sync同步目录，识别电影剧集名称，自动复制并重命名到Emby/Plex媒体库目录实现100%完美识别

这两个神Key你值得拥有：主KEY：BCWHZRSLANR64CGPTXRE54ENNSIUE5SMO，大片抢先看：BA6RXJ7YOAOOFV42V6HD56XH4QVIBL2P6

### 3、消息服务
支持ServerChan、微信、Telegram消息通知服务， 以上功能运行状态可通过消息服务推送消息到手机上，比如新增加了电影、签到完成、Emby播放状态（需要在Emby中配置webhook插件）等。
如果是使用微信渠道，还能实现在微信中直接控制（需要在企业微信中设置菜单，还要改一些代码）

### 4、其他的一些功能
自动签到（PT站、什么值得买、联动营业厅），qBittorrent定期删种、电影预告片搜刮和下载（已有电影的预告片、热门预告片）、定期同步iCloud中的照片到NAS等等。不需要的可以在配置中关掉。


【代码写的比较烂，初学仅限于能实现功能，轻喷。。。】


## 安装
### 1、Docker镜像
docker push jxxghp/nas-tools:latest

[jxxghp/nas-tools:latest](https://hub.docker.com/repository/docker/jxxghp/nas-tools)

Docker配置目录挂载：/config

配置文件名：config.ini，把源代码中config目录下的config.ini复制到配置目录并修改好即可。

端口映射：3000

### 2、本地运行
python3版本

pip install -r requirements.txt 安装依赖

nohup python3 run.py -c ./config/config.ini & 运行

config.ini文件根据源代码目录下的config.ini中的注释修改。

### 3、群晖套件
也制作了群晖套件可以直接在群晖中安装使用（只适用于dsm6.2.3），需要先安装python3.8套件，同时有些功能需要结合entware安装一些包（比如lm-sensors，也可以关掉）。
配置文件路径目前是写死的：/homes/admin/.config/nastool/config.ini，即只能是admin用户，且会找当前用户home目录下nastool/config.ini文件，需要DSM开启home目录且把nastool目录和配置文件建好。类似到qibittorrent的安装包，目前暂不知道怎么自动识别用户目录的问题。

https://github.com/jxxghp/nas-tools/raw/master/nastool_6.2.3.spk

![image](https://user-images.githubusercontent.com/51039935/153745028-3a9b7e9a-0404-45c0-9674-1763e272c005.png)


## 配置
1) 参考源码中config/config.ini配置文件示例进行配置，每一个配置项有注释说明。有的配置项需要在相关网站注册信息。

2) 导入nastool.sql到MySql数据库（不是必须）

3) 在Emby WebHooks中设置为 http(s)://IP:3000/emby ，接受Emby消息通知。

4) 根据以下目录结构建好目录，在Emby中对应每个目录建好媒体库，路径与程序中配置的一致。有使用ResilioSync的话，在同步目录也与本程序中的配置对应。

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


## 使用
1) WEB UI界面（3000端口），可以修改配置、手工启动服务、修改资源订阅关键字等
![image](https://user-images.githubusercontent.com/51039935/153745209-b86b593e-9234-4b59-82e4-2f0481838bd7.png)
![image](https://user-images.githubusercontent.com/51039935/153745181-6ca745da-c3f9-4f8b-9282-7bc5e79a6cd3.png)

2) 手机端通知和控制界面，实时接收程序运行状态，控制服务运行

![image](https://user-images.githubusercontent.com/51039935/151723777-14eb0252-4838-4bdb-9089-75393e6af277.png)

3) 效果（这些分类都是程序自动维护的）

![image](https://user-images.githubusercontent.com/51039935/153733308-498fd68c-4a24-4238-820d-10a1cd1025d1.png)
![image](https://user-images.githubusercontent.com/51039935/151723518-5ee68798-bd24-459a-b99f-43ebe27857e7.png)

4) 推荐使用1T以上的SSD做为PT下载盘和Resilio Sync的同步盘，大容量硬盘则为存储盘（当前没有也行，分开目录即可）。结合这套程序的PT自动下载转移和定期删种，实现作种和媒体存放分离，Emby/Plex完美搜刮，同时避免PT损伤存储硬盘。可以做到无人值守自动媒体库维护，且资源变化情况均有通知一目了然。


## TODO
1) 支持link方式保种（目前只支持复制转移方式，需要下载和存储分离）
2) 接入豆瓣自动拉取关注电影、电视剧，自动维护订阅关键字
3) PT站资源全局检索（目前依赖RSS订阅，仅支持增量发布内容）
