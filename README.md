![logo-blue](https://user-images.githubusercontent.com/51039935/197520391-f35db354-6071-4c12-86ea-fc450f04bc85.png)
# NAS媒体库管理工具

[![GitHub stars](https://img.shields.io/github/stars/NAStool/nas-tools?style=plastic)](https://github.com/NAStool/nas-tools/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/NAStool/nas-tools?style=plastic)](https://github.com/NAStool/nas-tools/network/members)
[![GitHub issues](https://img.shields.io/github/issues/NAStool/nas-tools?style=plastic)](https://github.com/NAStool/nas-tools/issues)
[![GitHub license](https://img.shields.io/github/license/NAStool/nas-tools?style=plastic)](https://github.com/NAStool/nas-tools/blob/master/LICENSE.md)
[![Docker pulls](https://img.shields.io/docker/pulls/jxxghp/nas-tools?style=plastic)](https://hub.docker.com/r/jxxghp/nas-tools)
[![Platform](https://img.shields.io/badge/platform-amd64/arm64-pink?style=plastic)](https://hub.docker.com/r/jxxghp/nas-tools)


Docker：https://hub.docker.com/repository/docker/jxxghp/nas-tools

TG频道：https://t.me/nastool_official

Wiki：https://t.me/NAStool_wiki

API: http://localhost:3000/api/v1/


## 功能：

NAS媒体库管理工具。


## 安装
### 1、Docker
```
docker pull jxxghp/nas-tools:latest
```
教程见 [这里](docker/readme.md) 。

如无法连接Github，注意不要开启自动更新开关(NASTOOL_AUTO_UPDATE=false)，将NASTOOL_CN_UPDATE设置为true可使用国内源加速安装依赖。

### 2、本地运行
python3.10版本，需要预安装cython，如发现缺少依赖包需额外安装：
```
git clone -b master https://github.com/NAStool/nas-tools --recurse-submodule 
python3 -m pip install -r requirements.txt
export NASTOOL_CONFIG="/xxx/config/config.yaml"
nohup python3 run.py & 
```

### 3、可执行文件
下载打包好的执行文件运行即可，会自动生成配置文件目录：

https://github.com/NAStool/nas-tools/releases

### 4、群晖套件
添加矿神群晖SPK套件源直接安装：

https://spk.imnks.com/

https://spk7.imnks.com/

## 免责声明
1) 本软件仅供学习交流使用，软件本身不提供任何内容，仅作为辅助工具简化用户手工操作，对用户的行为及内容毫不知情，使用本软件产生的任何责任需由使用者本人承担。
2) 本软件代码开源，基于开源代码进行修改，人为去除相关限制导致软件被分发、传播并造成责任事件的，需由代码修改发布者承担全部责任。同时按AGPL-3.0开源协议要求，基于此软件代码的所有修改必须开源。
3) 本项目没有在任何地方发布捐赠信息页面，也不会接受任何捐赠，请仔细辨别避免误导。