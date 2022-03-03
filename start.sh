# 自动更新和启动程序
# 获取版本号
online_file="https://github.com/jxxghp/nas-tools/raw/master/version.py"
local_file="/nas-tools/version.py"
online_version=$(wget $online_file -q -O -)
local_version=$(cat $local_file)

#判断字符串是否相等
if [ "$online_version" != "$local_version" ];then
  echo "最新版本：$online_version，开始升级..."
  #检查是不是有进程在运行
  running_pids=$(/bin/ps -ef | sed -e 's/^[ \t]*//' | grep -v grep | grep run.py | awk '{print $2}' | cut -f1 -d' ')
  if [ -z "${running_pids}" ];then
    for pid in ${running_pids}
    do
      echo "Try to Kill the $1 process [ ${pid} ]"
      kill -9 "${pid}"
    done
  fi
  # 重新git clone代码
  cd /
  rm -rf /nas-tools
  git clone https://github.com/jxxghp/nas-tools
  echo "恭喜，升级完成！"
else
  echo "当前已是最新版本"
fi

# 运行程序
echo "正在启动程序..."
python3 /nas-tools/run.py &