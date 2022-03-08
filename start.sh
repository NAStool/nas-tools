# 自动更新和启动程序
# 获取版本号
online_file="https://github.com/jxxghp/nas-tools/raw/master/version.py"
local_file="/nas-tools/version.py"
local_version=$(cat $local_file)

if test 0"${NASTOOL_AUTO_UPDATE}" != 0
  then
  echo "开始检查版本更新..."
  online_version=$(wget $online_file -q -O -)
  # 是否获取到最新版本
  if test "${online_version}"
  then
    #判断字符串是否相等
    if test "${online_version}" != "${local_version}"
    then
      echo "最新版本：${online_version}，开始升级..."
      #检查是不是有进程在运行
      running_pids=$(/bin/ps -ef | sed -e 's/^[ \t]*//' | grep -v grep | grep run.py | awk '{print $2}' | cut -f1 -d' ')
      if test "${running_pids}"
      then
        for pid in ${running_pids}
        do
          echo "Try to Kill the $1 process [ ${pid} ]"
          kill -9 "${pid}"
        done
      fi
      # 重新git clone代码
      cd /
      git clone https://github.com/jxxghp/nas-tools new_nas-tools
      # 判断是否升级成功
      if test "$?" == 0
      then
        rm -rf /nas-tools
        mv new_nas-tools nas-tools
        echo "恭喜，升级成功！"
      else
        echo "git clone出现错误，升级版本失败！"
      fi
    else
      echo "当前已是最新版本"
    fi
  else
    echo "获取最新版本号失败，使用当前版本启动"
  fi
else
  echo "程序自动升级已关闭，如需打开请设置环境变量：NASTOOL_AUTO_UPDATE 为任意值"
fi
# 运行程序
echo "正在启动程序..."
python3 /nas-tools/run.py