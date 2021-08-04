#!/usr/bin/env bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
# Usage:
## wget --no-check-certificate https://raw.githubusercontent.com/mixool/HiCnUnicom/master/CnUnicom.sh && chmod +x CnUnicom.sh && bash CnUnicom.sh
### bash <(curl -s https://raw.githubusercontent.com/mixool/HiCnUnicom/master/CnUnicom.sh) ${username} ${password}

# alias curl
alias curl='curl -m 10'

# user info: change them to yours or use parameters instead.
username="$1"
password="$2"
appid="$3"

# \u8054\u901AAPP\u7248\u672C
unicom_version=8.0100

# deviceId: \u968F\u673AIMEI
deviceId=$(shuf -i 123456789012345-987654321012345 -n 1)

# \u5B89\u5353\u624B\u673A\u7AEFAPP\u767B\u5F55\u8FC7\u7684\u4F7F\u7528\u8FD9\u4E2AUA
UA="Mozilla/5.0 (Linux; Android 6.0.1; oneplus a5010 Build/V417IR; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/52.0.2743.100 Mobile Safari/537.36; unicom{version:android@$unicom_version,desmobile:$username};devicetype{deviceBrand:Oneplus,deviceModel:oneplus a5010}"

# \u82F9\u679C\u624B\u673A\u7AEFAPP\u767B\u5F55\u8FC7\u7684\u4F7F\u7528\u8FD9\u4E2AUA
#UA="ChinaUnicom4.x/176 CFNetwork/1121.2.2 Darwin/19.2.0"

# workdir
workdir="$(pwd)/CnUnicom_tmp"
[[ ! -d "$workdir" ]] && mkdir $workdir

function rsaencrypt() {
    cat > $workdir/rsa_public.key <<-EOF
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDc+CZK9bBA9IU+gZUOc6
FUGu7yO9WpTNB0PzmgFBh96Mg1WrovD1oqZ+eIF4LjvxKXGOdI79JRdve9
NPhQo07+uqGQgE4imwNnRx7PFtCRryiIEcUoavuNtuRVoBAm6qdB0Srctg
aqGfLgKvZHOnwTjyNqjBUxzMeQlEC2czEMSwIDAQAB
-----END PUBLIC KEY-----
EOF

    crypt_username=$(echo -n $username | openssl rsautl -encrypt -inkey $workdir/rsa_public.key -pubin -out >(base64 | tr "\n" " " | sed s/[[:space:]]//g))
    crypt_password=$(echo -n $password | openssl rsautl -encrypt -inkey $workdir/rsa_public.key -pubin -out >(base64 | tr "\n" " " | sed s/[[:space:]]//g))
}

function urlencode() {
    local length="${#1}"
    for (( i = 0; i < length; i++ )); do
        local c="${1:i:1}"
        case $c in
            [a-zA-Z0-9.~_-]) printf "$c" ;;
            *) printf "$c" | xxd -p -c1 | while read x;do printf "%%%s" "$x";done
        esac
    done
}

# \u767B\u5F55\u5931\u8D25\u5C1D\u8BD5\u4FEE\u6539\u4EE5\u4E0B\u8FD9\u4E2AappId\u7684\u503C\u4E3A\u6293\u5305\u83B7\u53D6\u7684\u767B\u5F55\u8FC7\u7684\u8054\u901Aapp
function login() {
    rsaencrypt
    cat > $workdir/signdata <<-EOF
isRemberPwd=true
&deviceId=$deviceId
&password=$(urlencode $crypt_password)
&simCount=0
&netWay=Wifi
&mobile=$(urlencode $crypt_username)
&yw_code=
&timestamp=$(date +%Y%m%d%H%M%S)
&appId=$appid
&keyVersion=1
&deviceBrand=Oneplus
&pip=10.0.$(shuf -i 1-255 -n 1).$(shuf -i 1-255 -n 1)
&provinceChanel=general
&version=android%40$unicom_version
&deviceModel=oneplus%20a5010
&deviceOS=android6.0.1
&deviceCode=$deviceId
EOF

    # cookie
    #curl -X POST -sA "$UA" -b $workdir/cookie -c $workdir/cookie "https://m.client.10010.com/mobileService/customer/query/getMyUnicomDateTotle.htm?yw_code=&mobile=$username&version=android%40$unicom_version" | grep -oE "infoDetail" >/dev/null && status=0 || status=1
    #[[ $status == 0 ]] && echo "cookies\u767B\u5F551*******${username:0-4}\u6210\u529F"

    #if [[ $status == 1 ]]; then
        curl -X POST -sA "$UA" -c $workdir/cookie "https://m.client.10010.com/mobileService/logout.htm?&desmobile=$username&version=android%40$unicom_version" >/dev/null
        curl -sA "$UA" -b $workdir/cookie -c $workdir/cookie -d @$workdir/signdata "https://m.client.10010.com/mobileService/login.htm" >/dev/null
        token=$(cat $workdir/cookie | grep -E "a_token" | awk  '{print $7}')
        [[ "$token" = "" ]] && echo "Error, login failed." && echo "cmd for clean: rm -rf $workdir" && exit 1
        echo "\u5BC6\u7801\u767B\u5F551*******${username:0-4}\u6210\u529F"
    #fi
}

#function openChg() {
    # \u6BCF\u6708\u4E00\u53F7\u529E\u7406\u89E3\u966440G\u5C01\u9876\u4E1A\u52A1
    #[[ "$(date "+%d")" == "01" ]] || return 0
    #echo; echo $(date) starting dingding OpenChg...
    #curl -sA "$UA" -b $workdir/cookie --data "querytype=02&opertag=0" "https://m.client.10010.com/mobileService/businessTransact/serviceOpenCloseChg.htm" >/dev/null
#}

function membercenter() {
    echo; echo $(date) starting membercenter...

    #\u83B7\u53D6\u6587\u7AE0\u548C\u8BC4\u8BBA\u751F\u6210\u6570\u7EC4\u6570\u636E
    NewsListId=($(curl -X POST -sA "$UA" -b $workdir/cookie --data "pageNum=1&pageSize=10&reqChannel=00" https://m.client.10010.com/commentSystem/getNewsList | grep -oE "id\":\"[^\"]*" | awk -F[\"] '{print $NF}' | tr "\n" " "))
    comtId=($(curl -X POST -sA "$UA" -b $workdir/cookie --data "id=${NewsListId[0]}&pageSize=10&pageNum=1&reqChannel=quickNews" -e "https://img.client.10010.com/kuaibao/detail.html?pageFrom=newsList&id=${NewsListId[0]}" https://m.client.10010.com/commentSystem/getCommentList | grep -oE "id\":\"[^\"]*" | awk -F[\"] '{print $NF}' | tr "\n" " "))
    nickId=($(curl -X POST -sA "$UA" -b $workdir/cookie --data "id=${NewsListId[0]}&pageSize=10&pageNum=1&reqChannel=quickNews" -e "https://img.client.10010.com/kuaibao/detail.html?pageFrom=newsList&id=${NewsListId[0]}" https://m.client.10010.com/commentSystem/getCommentList | grep -oE "nickName\":\"[^\"]*" | awk -F[\"] '{print $NF}' | tr "\n" " "))
    Referer="https://img.client.10010.com/kuaibao/detail.html?pageFrom=${NewsListId[0]}"

    #\u8BC4\u8BBA\u70B9\u8D5E
    for((i = 0; i < ${#comtId[*]}; i++)); do
        curl -X POST -sA "$UA" -b $workdir/cookie --data "pointChannel=02&pointType=02&reqChannel=quickNews&reqId=${comtId[i]}&praisedMobile=${nickId[i]}&newsId=${NewsListId[0]}" -e "$Referer" https://m.client.10010.com/commentSystem/csPraise
        curl -X POST -sA "$UA" -b $workdir/cookie --data "pointChannel=02&pointType=01&reqChannel=quickNews&reqId=${comtId[i]}&praisedMobile=${nickId[i]}&newsId=${NewsListId[0]}" -e "$Referer" https://m.client.10010.com/commentSystem/csPraise | grep -oE "growScore\":\"0\"" >/dev/null && break
    done

    #\u6587\u7AE0\u70B9\u8D5E
    for((i = 0; i <= ${#NewsListId[*]}; i++)); do
        curl -X POST -sA "$UA" -b $workdir/cookie --data "pointChannel=01&pointType=02&reqChannel=quickNews&reqId=${NewsListId[i]}" https://m.client.10010.com/commentSystem/csPraise
        curl -X POST -sA "$UA" -b $workdir/cookie --data "pointChannel=01&pointType=01&reqChannel=quickNews&reqId=${NewsListId[i]}" https://m.client.10010.com/commentSystem/csPraise | grep -oE "growScore\":\"0\"" >/dev/null && break
    done

    #\u6587\u7AE0\u8BC4\u8BBA
    newsTitle="$(curl -X POST -sA "$UA" -b $workdir/cookie --data "newsId=${NewsListId[1]}&reqChannel=quickNews&isClientSide=0&pageFrom=newsList" -e "$Referer" https://m.client.10010.com/commentSystem/getNewsDetails | grep -oE "mainTitle\":\"[^\"]*" | awk -F[\"] '{print $NF}')"
    subTitle="$(curl -X POST -sA "$UA" -b $workdir/cookie --data "newsId=${NewsListId[1]}&reqChannel=quickNews&isClientSide=0&pageFrom=newsList" -e "$Referer" https://m.client.10010.com/commentSystem/getNewsDetails | grep -oE "subTitle\":\"[^\"]*" | awk -F[\"] '{print $NF}')"
    for((i = 0; i <= 5; i++)); do
        data="id=${NewsListId[1]}&newsTitle=$(urlencode $newsTitle)&commentContent=$RANDOM&upLoadImgName=&reqChannel=quickNews&subTitle=$(urlencode $subTitle)&belongPro=098"
        mycomtId="$(curl -X POST -sA "$UA" -b $workdir/cookie --data "$data" -e "$Referer" https://m.client.10010.com/commentSystem/saveComment | grep -oE "id\":\"[^\"]*" | awk -F[\"] '{print $NF}')"
        curl -X POST -sA "$UA" -b $workdir/cookie --data "type=01&reqId=$mycomtId&reqChannel=quickNews" -e "$Referer" https://m.client.10010.com/commentSystem/delDynamic
    done

    #\u6BCF\u6708\u4E00\u6B21\u8D26\u5355\u67E5\u8BE2
    if [[ "$(date "+%d")" == "01" ]]; then
        curl -sLA "$UA" -b $workdir/cookie -c $workdir/cookie.HistoryBill --data "yw_code=&desmobile=$username&version=android@$unicom_version" "https://m.client.10010.com/mobileService/common/skip/queryHistoryBill.htm?mobile_c_from=home" >/dev/null
        curl -sLA "$UA" -b $workdir/cookie.HistoryBill --data "operateType=0&bizCode=1000210003&height=889&width=480" "https://m.client.10010.com/mobileService/query/querySmartBizNew.htm?" >/dev/null
        curl -sLA "$UA" -b $workdir/cookie.HistoryBill --data "systemCode=CLIENT&transId=&userNumber=$username&taskCode=TA52554375&finishTime=$(date +%Y%m%d%H%M%S)" "https://act.10010.com/signinAppH/limitTask/limitTime" >/dev/null
    fi

    #\u6BCF\u65E5\u4E00\u6B21\u4F59\u91CF\u67E5\u8BE2
    curl -sLA "$UA" -b $workdir/cookie -c $workdir/cookie.LeavePackage --data "desmobile=$username&version=android@$unicom_version" "https://m.client.10010.com/mobileService/common/skip/queryLeavePackage.htm" >/dev/null
    curl -sLA "$UA" -b $workdir/cookie.LeavePackage --data "operateType=0&bizCode=1000210026&height=776&width=480" "https://m.client.10010.com/mobileService/query/querySmartBizNew.htm?" >/dev/null
    curl -sLA "$UA" -b $workdir/cookie.LeavePackage --data "type=0" "https://m.client.10010.com/mobileService/grow/marginCheck.htm"

    #\u7B7E\u5230
    Referer="https://img.client.10010.com/activitys/member/index.html"
    data="yw_code=&desmobile=$username&version=android@$unicom_version"
    curl -sLA "$UA" -b $workdir/cookie -c $workdir/cookie.SigninActivity -e "$Referer" "https://act.10010.com/SigninApp/signin/querySigninActivity.htm?$data" >/dev/null
    Referer="https://act.10010.com/SigninApp/signin/querySigninActivity.htm?$data"
    curl -X POST -sA "$UA" -b $workdir/cookie.SigninActivity -e "$Referer" "https://act.10010.com/SigninApp/signin/daySign?vesion=0.$(shuf -i 1234567890123456-9876543210654321 -n 1)"
    echo
    curl -X POST -sA "$UA" -b $workdir/cookie.SigninActivity -e "$Referer" "https://act.10010.com/SigninApp/signin/todaySign"
    echo
    curl -X POST -sA "$UA" -b $workdir/cookie.SigninActivity -e "$Referer" "https://act.10010.com/SigninApp/signin/addIntegralDA"

    ##\u4E09\u6B21\u91D1\u5E01\u62BD\u5956\uFF0C \u6BCF\u65E5\u6700\u591A\u53EF\u82B1\u8D39\u91D1\u5E01\u6267\u884C\u5341\u4E09\u6B21
    usernumberofjsp=$(curl -sA "$UA" -b $workdir/cookie.SigninActivity https://m.client.10010.com/dailylottery/static/textdl/userLogin | grep -oE "encryptmobile=\w*" | awk -F"encryptmobile=" '{print $2}'| head -n1)
    for((i = 1; i <= 3; i++)); do
        [[ $i -gt 3 ]] && curl -sA "$UA" -b $workdir/cookie.SigninActivity --data "goldnumber=10&banrate=10&usernumberofjsp=$usernumberofjsp" https://m.client.10010.com/dailylottery/static/doubleball/duihuan >/dev/null; sleep 1
        curl -sA "$UA" -b $workdir/cookie.SigninActivity --data "usernumberofjsp=$usernumberofjsp&flag=convert" https://m.client.10010.com/dailylottery/static/doubleball/choujiang | grep -qE "\u7528\u6237\u673A\u4F1A\u6B21\u6570\u4E0D\u8DB3" && break
    done
    echo; echo goldTotal\uFF1A$(curl -X POST -sA "$UA" -b $workdir/cookie.SigninActivity -e "$Referer" "https://act.10010.com/SigninApp/signin/getGoldTotal?vesion=0.$(shuf -i 1234567890123456-9876543210654321 -n 1)")

    ##\u79EF\u5206\u62BD\u5956\u9996\u6B21\u514D\u8D39\uFF0C\u4E4B\u540E\u9886300\u5956\u52B1\u79EF\u5206\u5151\u6362\u518D\u62BD\u5956,\u6700\u591A\u4E09\u5341\u6B21
    curl -sLA "$UA" -b $workdir/cookie "https://m.client.10010.com/welfare-mall-front/mobile/winter/getpoints/v1"
    curl -X POST -sLA "$UA" -b $workdir/cookie --data "from=$(shuf -i 12345678901-98765432101 -n 1)" "https://m.client.10010.com/welfare-mall-front/mobile/winterTwo/getIntegral/v1"

    curl -X POST -sA "$UA" -b $workdir/cookie.SigninActivity --data "usernumberofjsp=$usernumberofjsp&flag=convert" http://m.client.10010.com/dailylottery/static/integral/choujiang
    #for((i = 1; i <= 15; i++)); do
        #echo . && curl -sA "$UA" -b $workdir/cookie.SigninActivity --data "goldnumber=10&banrate=30&usernumberofjsp=$usernumberofjsp" http://m.client.10010.com/dailylottery/static/integral/duihuan >/dev/null; sleep 1
        #curl -X POST -sA "$UA" -b $workdir/cookie.SigninActivity --data "usernumberofjsp=$usernumberofjsp&flag=convert" http://m.client.10010.com/dailylottery/static/integral/choujiang | grep -qE "\u7528\u6237\u673A\u4F1A\u6B21\u6570\u4E0D\u8DB3" && break
    #done

    # \u6E38\u620F\u9891\u9053\u7B7E\u5230\u79EF\u5206 \u6BCF\u65E51\u79EF\u5206
    curl -X POST -sA "$UA" -b $workdir/cookie.SigninActivity --data "methodType=iOSIntegralGet&gameLevel=1&deviceType=iOS" "https://m.client.10010.com/producGameApp"

    # \u6E38\u620F\u5956\u52B1\u79EF\u5206\u7B7E\u5230
    echo; curl -X POST -sA "$UA" -b $workdir/cookie.SigninActivity --data "methodType=signin" https://m.client.10010.com/producGame_signin

    # \u6E38\u620F\u5B9D\u7BB1
    curl -X POST -sA "$UA"  -b $workdir/cookie.SigninActivity -c $workdir/cookie.xybx --data "thirdUrl=https%3A%2F%2Fimg.client.10010.com%2Fshouyeyouxi%2Findex.html%23%2Fyouxibaoxiang" https://m.client.10010.com/mobileService/customer/getShareRedisInfo.htm >/dev/null
    echo; curl -X POST -sA "$UA" -b $workdir/cookie.xybx --data "methodType=reward&deviceType=Android&clientVersion=$unicom_version&isVideo=N" https://m.client.10010.com/game_box
    #\u5B9D\u7BB1\u4EFB\u52A1100M
    echo; curl -sA "$UA" -b $workdir/cookie.xybx --data "methodType=taskGetReward&deviceType=Android&clientVersion=$unicom_version&taskCenterId=98" https://m.client.10010.com/producGameTaskCenter
    ##\u6E38\u620F\u5B9D\u7BB1\u7FFB\u500D
    echo; curl -X POST -sA "$UA" -b $workdir/cookie.xybx --data "methodType=reward&deviceType=Android&clientVersion=$unicom_version&isVideo=Y" https://m.client.10010.com/game_box

    #\u6C83\u4E4B\u6811\u6D47\u6C34
    curl -X POST -sA "$UA" -b $workdir/cookie.SigninActivity -c $workdir/cookie.wotree --data "thirdUrl=https%3A%2F%2Fimg.client.10010.com%2Fmactivity%2FwoTree%2Findex.html%23%2F" https://m.client.10010.com/mobileService/customer/getShareRedisInfo.htm >/dev/null
    Referer="https://img.client.10010.com/mactivity/woTree/index.html"
    curl -X POST -sA "$UA" -b $workdir/cookie.wotree -c $workdir/cookie.wotree -e "$Referer" https://m.client.10010.com/mactivity/mailb/isNewLetter.htm >/dev/null
    curl -X POST -sA "$UA" -b $workdir/cookie.wotree -c $workdir/cookie.wotree -e "$Referer" https://m.client.10010.com/mactivity/task/bord.htm >/dev/null
    curl -X POST -sA "$UA" -b $workdir/cookie.wotree -c $workdir/cookie.wotree -e "$Referer" https://m.client.10010.com/mactivity/arbordayJson/index.htm >/dev/null
    curl -X POST -sA "$UA" -b $workdir/cookie.wotree -c $workdir/cookie.wotree -e "$Referer" https://m.client.10010.com/mactivity/arbordayJson/getChanceByIndex.htm?index=0 >/dev/null
    curl -X POST -sA "$UA" -b $workdir/cookie.wotree -c $workdir/cookie.wotree -e "$Referer" https://m.client.10010.com/mactivity/stealingEnergy/engerSign.htm >/dev/null
    echo; curl -X POST -sA "$UA" -b $workdir/cookie.wotree -c $workdir/cookie.wotree -e "$Referer" https://m.client.10010.com/mactivity/arbordayJson/arbor/3/0/3/grow.htm | grep -oE "addedValue\":[0-9]"

    #\u83B7\u5F97\u6D41\u91CF
    for((i = 1; i <= 3; i++)); do
        curl -X POST -sA "$UA" -b $workdir/cookie --data "stepflag=22" https://act.10010.com/SigninApp/mySignin/addFlow >/dev/null; sleep 5
        curl -X POST -sA "$UA" -b $workdir/cookie --data "stepflag=23" https://act.10010.com/SigninApp/mySignin/addFlow | grep -oE "reason\":\"01\"" >/dev/null && break
    done
}

function jfdouble() {
    echo; echo $(date) \u5F00\u59CB \u79EF\u5206\u7FFB\u500D...

    #\u7B7E\u5230
    Referer="https://img.client.10010.com/activitys/member/index.html"
    data="yw_code=&desmobile=$username&version=android@$unicom_version"
    curl -sLA "$UA" -b $workdir/cookie -c $workdir/cookie.SigninActivity -e "$Referer" "https://act.10010.com/SigninApp/signin/querySigninActivity.htm?$data" >/dev/null
    Referer="https://act.10010.com/SigninApp/signin/querySigninActivity.htm?$data"
    ##\u7B7E\u5230\u89C6\u9891\u7FFB\u500D\u8D60\u9001\u79EF\u5206
    echo
    curl -X POST -sA "$UA" -b $workdir/cookie.SigninActivity -e "$Referer" "https://act.10010.com/SigninApp/signin/bannerAdPlayingLogo"
}

function main() {
    #sleep $(shuf -i 1-10800 -n 1)
    login
    membercenter
    jfdouble
    #openChg
    #rm -rf $workdir
    echo; echo $(date) 1*******${username:0-4} Accomplished.  Thanks!
}

main