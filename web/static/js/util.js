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

//绑定事件
$(document).ready(function(){
	//服务模态框事件
    $("#service_start_btn").click(function(){
        $('#service-modal').modal('hide');
        run_scheduler($("#service_start_id").val());
    });

    // 下载模态框事件
    $("#download_start_btn").click(function(){
        $('#download-modal').modal('hide');
        download_link($("#download_start_id").val());
    });

    // 加入RSS订阅模枋框事件
    $("#recommend_start_btn").click(function(){
        $('#recommend-modal').modal('hide');
        dotype = $("#recommend_do_type").val()
        if(dotype == "ADD"){
            add_rss_key($("#recommend_start_type").val(), $("#recommend_start_name").val());
        }else{
            remove_rss_key($("#recommend_start_type").val(), $("#recommend_start_name").val());
        }
    });
});

// 显示服务提示框
function show_service_modal(id, name) {
     $("#service_start_id").val(id);
     $("#service_start_name").val(name);
     $("#service_start_message").text("是否立即运行服务：" + name + "？");
     $('#service-modal').modal('show');
}

// 显示下载提示框
function show_download_modal(id, name){
    $("#download_start_id").val(id);
    $("#download_start_name").val(name);
    $("#download_start_message").text("是否立即下载该资源：？" + name + "？");
    $('#download-modal').modal('show');
}

// 显示添加订阅
function show_recommend_add_modal(id, type, name){
    $("#recommend_start_id").val(id);
    $("#recommend_start_type").val(type);
    $("#recommend_start_name").val(name);
    $("#recommend_do_type").val("ADD")
    $("#recommend_start_message").text("是否确定将 " + name + " 加入RSS订阅？");
    $('#recommend-modal').modal('show');
}
// 显示删除订阅
function show_recommend_del_modal(id, type, name){
    $("#recommend_start_id").val(id);
    $("#recommend_start_type").val(type);
    $("#recommend_start_name").val(name);
    $("#recommend_do_type").val("DEL")
    $("#recommend_start_message").text("是否确定将 " + name + " 从RSS订阅中移除？");
    $('#recommend-modal').modal('show');
}