yq '.jobs.create-release' build.yml>create-build-new.txt
diff build.yml build.bak.yml > /dev/null
if [  "$?" == "0" ]; then #"$?"是上一执行命令的返回值。
    echo "nothing to change"
    else
    cp build.yml build-2.yml
    cp build.yml build.bak.yml #为下次比较否有变化做准备
    myenv=$(cat tags-build.txt) yq -i '.jobs.create-release=env(myenv)' build-2.yml
    yq -i '.name="Nas-tools Build-2"' build-2.yml
    cat build-2.yml
    git add .
    git commit -m "recreate build-2.yml"
    fi
