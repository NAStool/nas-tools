// Ajax主方法
function ajax_post(cmd, data, handler){
    var data = {
        cmd: cmd,
        data: JSON.stringify(data)
    };
    $.ajax({
        type: "POST",
        url: "do",
        dataType: "json",
        data: data,
        timeout: 180000,
        success: handler,
        error: function(xhr, textStatus, errorThrown){
            alert("系统未响应，请稍后重试！");
        }
    });
}

//获取链接参数
function getQueryVariable(variable)
{
    var query = window.location.search.substring(1);
    var vars = query.split("&");
    for (var i=0;i<vars.length;i++) {
        var pair = vars[i].split("=");
        if(pair[0] == variable){return pair[1];}
    }
    return(false);
}

// 搜索按钮
function search_media(){
    var cmd = "search";
    var keyword = $("#search_word").val();
    if(keyword == ""){
        return;
    }
    $("#search_btn").val("搜索中...");
    $("#search_btn").attr("disabled", "true");
    $("#search_tip_title").text("正在搜索，请稍后...");
    $("#search_tip_text").text("");
    var param = {"search_word": keyword};
    ajax_post(cmd, param, function(ret){
        //刷新页面
        window.location.href = window.location.href.split('?')[0];
    });
}

//点击链接下载
function download_link(id){
    var cmd = "download";
    var data = {"id": id};
	ajax_post(cmd, data, function(ret){
       item = $("#download_start_name").val();
        $("#download_finished_str").text(item + " 添加下载成功！");
        $("#download-modal-success").modal('show');
	});
}

// 运行服务
function run_scheduler(id){
    var cmd = "sch";
    var data = { "item": id };
    ajax_post(cmd, data, function(ret){
        item = $("#service_start_name").val();;
        $("#service_finished_str").text(item + " 已执行完成！");
        $("#service-modal-success").modal('show');
    });
}

// 添加订阅关键字
function add_rss_key(type, name){
    var cmd = "addrss";
    var data = { "name": name, "type": type};
    ajax_post(cmd, data, function(ret){
        name = $("#recommend_start_name").val();
        type =  $("#recommend_start_type").val();
        id = $("#recommend_start_id").val();
        $("#recommend_finished_str").text(name + " 添加RSS订阅成功！");
        $("#recommend-modal-success").modal('show');
        $("#recommend_svg_" + id).removeClass();
        $("#recommend_svg_" + id).addClass("icon icon-filled text-red");
        $("#recommend_link_" + id).attr("href", "javascript:remove_rss_key('" + type + "','" + name + "')")
    });

}

// 删除订阅关键字
function remove_rss_key(type, name){
    var cmd = "delrss";
    var data = { "name": name, "type": type};
    ajax_post(cmd, data, function(ret){
        name = $("#recommend_start_name").val();
        type =  $("#recommend_start_type").val();
        id = $("#recommend_start_id").val();
        $("#recommend_finished_str").text(name + " 已从RSS订阅中移除！");
        $("#recommend-modal-success").modal('show');
        $("#recommend_svg_" + id).removeClass();
        $("#recommend_svg_" + id).addClass("icon icon-tabler icon-tabler-heart");
        $("#recommend_link_" + id).attr("href", "javascript:add_rss_key('" + type + "','" + name + "')")
    });
}

// 保存关键字设置
function save_movie_rss_keys(id){
    var cmd = "moviekey";
    var param = {"movie_keys": $("#movie_keys").val()};
    $("#"+id+"_btn").text("正在保存...");
    $("#"+id+"_btn").attr("disabled", "true");
    ajax_post(cmd, param, function(ret){
        $("#"+id+"_btn").removeAttr("disabled");
        $("#"+id+"_btn").text("保存");
    });

}

// 保存关键字设置
function save_tv_rss_keys(id){
    var cmd = "tvkey";
    var param = {"tv_keys": $("#tv_keys").val()};
    $("#"+id+"_btn").text("正在保存...");
    $("#"+id+"_btn").attr("disabled", "true");
    ajax_post(cmd, param, function(ret){
        $("#"+id+"_btn").removeAttr("disabled");
        $("#"+id+"_btn").text("保存");
    });

}

// 下载控制
function start_pt_download(id){
    var cmd = "pt_start";
    var param = {"id": id};
    ajax_post(cmd, param, function(ret){
      setTimeout(window.location.reload(), 2000)
    });
}
function stop_pt_download(id){
    var cmd = "pt_stop";
    var param = {"id": id};
    ajax_post(cmd, param, function(ret){
      setTimeout(window.location.reload(), 2000)
    });
}
function remove_pt_download(id){
    var cmd = "pt_remove";
    var param = {"id": id};
    ajax_post(cmd, param, function(ret){
      setTimeout(window.location.reload(), 2000)
    });
}