diff build-windows.yml compare/build-windows.yml.bak > /dev/null
if [  "$?" == "0" ]; then #"$?"是上一执行命令的返回值。
    echo "nothing to change"
    else
    sudo snap install yq
    cp build-windows.yml build-windows-2.yml #制作实时更新的带有修改记录的action文件
    cp build-windows.yml compare/build-windows.yml.bak #为下次比较否有变化做准备
    myenv=$(cat compare/tags-build) yq -i '.jobs.Create-release_Send-message=env(myenv)' build-windows-2.yml  # 把生成修改记录的action放入build-2.yml
    yq -i '.name="Build NAStool Windows-2"' build-windows-2.yml
    cat build-windows-2.yml
    git add .
    git commit -m "update build-windows-2.yml"
    fi
