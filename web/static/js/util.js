// Ajax主方法
function ajax_post(cmd, data, handler, aync=true) {
    var data = {
        cmd: cmd,
        data: JSON.stringify(data)
    };
    $.ajax({
        type: "POST",
        url: "do?random=" + Math.random(),
        dataType: "json",
        data: data,
        cache: false,
        async: aync,
        timeout: 0,
        success: handler,
        error: function (xhr, textStatus, errorThrown) {
        }
    });
}

// 备份文件下载
function ajax_backup(handler) {
    var downloadURL = "/backup";
    let xhr = new XMLHttpRequest()
    xhr.open('POST', downloadURL, true);
    xhr.responseType = 'arraybuffer';
    xhr.onload = function () {
        if (this.status === 200) {
            let type = xhr.getResponseHeader('Content-Type')
            let fileName = xhr.getResponseHeader('Content-Disposition').split(';')[1].split('=')[1].replace(/\"/g, '')

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
                    var a = document.createElement('a');
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
            eval(handler)();
        }
    };
    xhr.send();
}

//获取链接参数
function getQueryVariable(variable) {
    var query = window.location.search.substring(1);
    var vars = query.split("&");
    for (var i = 0; i < vars.length; i++) {
        var pair = vars[i].split("=");
        if (pair[0] == variable) {
            return pair[1];
        }
    }
    return (false);
}

