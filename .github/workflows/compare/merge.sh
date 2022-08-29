diff build.yml compare/build.yml.bak > /dev/null
if [  "$?" == "0" ]; then #"$?"是上一执行命令的返回值。
    echo "nothing to change"
    else
    cp build.yml build-2.yml #制作实时更新的带有修改记录的action文件
    cp build.yml compare/build.yml.bak #为下次比较否有变化做准备
    myenv=$(cat compare/tags-build.txt) yq -i '.jobs.create-release=env(myenv)' build-2.yml  # 把生成修改记录的action放入build-2.yml
    yq -i '.name="Nas-tools Build-2"' build-2.yml
    cat build-2.yml
    git add .
    git commit -m "update build-2.yml"
    fi
