
// 进度条配置
NProgress.configure({ showSpinner: false });

// Ajax主方法
function ajax_post(cmd, params, handler, aync=true, show_progress=true) {
    if (show_progress) {
        NProgress.start();
    }
    let data = {
        cmd: cmd,
        data: JSON.stringify(params)
    };
    $.ajax({
        type: "POST",
        url: "do?random=" + Math.random(),
        dataType: "json",
        data: data,
        cache: false,
        async: aync,
        timeout: 0,
        success: function (data) {
            if (show_progress) {
                NProgress.done();
            }
            if (handler) {
                handler(data);
            }
        },
        error: function (xhr, textStatus, errorThrown) {
            if (show_progress) {
                NProgress.done();
            }
            if (xhr && xhr.status === 200) {
                handler({code: 0});
            } else {
                handler({code: -99, msg: "网络错误"});
            }
        }
    });
}

// 备份文件下载
function ajax_backup(handler) {
    const downloadURL = "/backup";
    let xhr = new XMLHttpRequest()
    xhr.open('POST', downloadURL, true);
    xhr.responseType = 'arraybuffer';
    xhr.onload = function () {
        if (this.status === 200) {
            let type = xhr.getResponseHeader('Content-Type')
            let fileName = xhr.getResponseHeader('Content-Disposition')
                .split(';')[1]
                .split('=')[1]
                .replace(/\"/g, '')

            let blob = new Blob([this.response], {type: type})
            if (typeof window.navigator.msSaveBlob !== 'undefined') {
                /*
                 * IE workaround for "HTML7007: One or more blob URLs were revoked by closing
                 * the blob for which they were created. These URLs will no longer resolve as
                 * the data backing the URL has been freed."
                 */
                window.navigator.msSaveBlob(blob, fileName);
            } else {
                let URL = window.URL || window.webkitURL;
                let objectUrl = URL.createObjectURL(blob);
                console.log(objectUrl);
                if (fileName) {
                    const a = document.createElement('a');
                    // safari doesn't support this yet
                    if (typeof a.download === 'undefined') {
                        window.location = objectUrl
                    } else {
                        a.href = objectUrl;
                        a.download = fileName;
                        document.body.appendChild(a);
                        a.click();
                        a.remove();
                    }
                } else {
                    window.location = objectUrl;
                }
            }
        }
        if (handler) {
            handler();
        }
    };
    xhr.send();
}

// 获取链接参数
function getQueryVariable(variable) {
    const query = window.location.search.substring(1);
    const vars = query.split("&");
    for (let i = 0; i < vars.length; i++) {
        const pair = vars[i].split("=");
        if (pair[0] == variable) {
            return pair[1];
        }
    }
    return false;
}

// 鼠标提示等待
function make_cursor_busy() {
    const body = document.querySelector("body");
    body.style.cursor = "wait";
}

// 鼠标取消等待
function cancel_cursor_busy() {
    const body = document.querySelector("body");
    body.style.cursor = "default";
}

// 是否触摸屏设备
function is_touch_device() {
    return 'ontouchstart' in window;
}

// replaceAll浏览器兼容
String.prototype.replaceAll = function (s1, s2) {
    return this.replace(new RegExp(s1, "gm"), s2)
}

function select_name(name) {
    if (name.startsWith("\^")) {
        return `name^=${name.substring(1)}`;
    } else {
        return `name=${name}`;
    }
}

/**
 * 全选按钮绑定
 * @param: btnobj 按钮对象
 * @param: name 被管理checkbox的name
 **/
function select_btn_SelectALL(btnobj, name) {
    if ($(btnobj).text() === "全选") {
        $(`input[${select_name(name)}][type=checkbox]`).prop("checked", true);
        $(btnobj).text("全不选");
    } else {
        $(`input[${select_name(name)}][type=checkbox]`).prop("checked", false);
        $(btnobj).text("全选");
    }
}

/**
 * 全选事件
 * @param: status 全选框状态
 * @param: name 被管理checkbox的name
 **/
function select_SelectALL(status, name) {
    $(`input[${select_name(name)}][type=checkbox]`).prop("checked", status);
}

/**
 * 部分选定事件
 * @param: status 全选框状态
 * @param: name 被管理checkbox的name
 **/
function select_SelectPart(condition, name) {
    $(`input[${select_name(name)}][type=checkbox]`).each(function () {
        if (condition && condition.includes($(this).val())) {
            $(this).prop("checked", true);
        } else {
            $(this).prop("checked", false);
        }
    });
}

/**
 * 获取选中input元素value
 * @param: name 被管理checkbox的name
 **/
function select_GetSelectedVAL(name) {
    let selectedVAL = [];
    $(`input[${select_name(name)}][type=checkbox]`).each(function () {
        if ($(this).prop("checked")) {
        selectedVAL.push($(this).val());
        }
    });
    return selectedVAL;
}

/**
 * 获取隐藏input元素value
 * @param: name 被管理checkbox的name
 **/
function select_GetHiddenVAL(name) {
    let hiddenVAL = [];
    $(`input[${select_name(name)}][type=hidden]`).each(function () {
        hiddenVAL.push($(this).val());
    });
    return hiddenVAL;
}

/**
 * 获取元素下input设置
 * @param: id 元素id
 **/
function input_select_GetVal(id, prefix=null) {
    let params = {};
    $(`#${id} input`).each(function () {
        let key = $(this).attr("id");
        if (key) {
            params[(prefix) ? key.replace(prefix, "") : key] = ($(this).attr("type") === "checkbox") ? !!$(this).prop("checked") : $(this).val();
        }
    });
    $(`#${id} select`).each(function () {
        let key = $(this).attr("id");
        if (key) {
            params[(prefix) ? key.replace(prefix, "") : key] = $(this).val();
        }
    });
    return params;
}

/**
 * 对象数组排序，针对纯英文、数字或纯中文的排序
 * @param: objArr 需要排序的对象数组
 * @param: sortKey  需要进行排序的键
 * @param: sortType asc升序(默认)  desc 降序
 **/
function dictArraySorting(objArr,sortKey,sortType="asc") {
    return objArr.sort(function (obj1, obj2) {
        let val1 = obj1[sortKey];
        let val2 = obj2[sortKey];
        if (!isNaN(Number(val1)) && !isNaN(Number(val2))) {
            val1 = Number(val1);
            val2 = Number(val2);
        }
        if (sortType === "asc") {
            return val1 - val2;
        } else if (sortType === "desc") {
            return val2 - val1;
        }
    })
}

/**
 * bytes转换为size
 * @param: bytes 字节数
 **/
function bytesToSize(bytes) {
    let size = ''
    if (bytes < 0.1 * 1024) { // 小于0.1KB 则转化成B
        size = bytes + ' B'
    }
    else if (bytes < 0.1 * 1024 * 1024) { // 小于0.1MB 则转换成KB
        size = (bytes / 1024).toFixed(2) + ' KB'
    }
    else if (bytes < 0.1 * 1024 * 1024 * 1024) { // 小于0.1GB 则转换成MB
        size = (bytes / (1024 * 1024)).toFixed(2) + ' MB'
    }
    else if (bytes < 0.1 * 1024 * 1024 * 1024 * 1024) { // 小于0.1TB 则转换成GB
        size = (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
    }
    else if (bytes < 0.1 * 1024 * 1024 * 1024 * 1024 * 1024) { // 小于0.1PB 则转换成TB
        size = (bytes / (1024 * 1024 * 1024 * 1024)).toFixed(2) + ' TB'
    }
    else if (bytes < 0.1 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024) { // 小于0.1EB 则转换成PB
        size = (bytes / (1024 * 1024 * 1024 * 1024 * 1024)).toFixed(2) + ' PB'
    }
    return size
}

/**
 * 暂停
 * @param: ms 暂停毫秒数
 **/
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 比较版本号大小，v1大于v2时返回1，相等返回0，否则返回-1
 */
function compareVersion(version1, version2) {
    version1 = version1.split(' ');
    version2 = version2.split(' ');
    const c1= version1[1];
    const c2= version2[1];
    const v1 = version1[0].replace('v', '').split('.');
    const v2 = version2[0].replace('v', '').split('.');
    const len = Math.max(v1.length, v2.length);

    while (v1.length < len) {
        v1.push('0');
    }
    while (v2.length < len) {
        v2.push('0');
    }

    for (let i = 0; i < len; i++) {
        const num1 = parseInt(v1[i]);
        const num2 = parseInt(v2[i]);

        if (num1 > num2) {
            return 1;
        } else if (num1 < num2) {
            return -1;
        }
    }
    
    if (c1 && c2) {
        if (c1 === c2) {
            return 0;
        } else {
            return 2;
        }
    } else {
        return 0;
    }
}