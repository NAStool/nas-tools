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
            alert("错误信息:"+xhr.responseText);
        }
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

// 保存关键字设置
function save_rss_keys(id){
    var cmd = "key";
    if(id == "movie_keys"){
        var param = {"movie_keys": $("#movie_keys").val()};
    }else{
        var param = {"tv_keys": $("#tv_keys").val()};
    }
    $("#"+id+"_btn").text("正在保存...");
    $("#"+id+"_btn").attr("disabled", "true");
    ajax_post(cmd, param, function(ret){
        $("#"+id+"_btn").removeAttr("disabled");
        $("#"+id+"_btn").text("保存");
    });

}

//绑定事件
$(document).ready(function(){
    // 搜索按钮
	$("#search_btn").click(function(){
	    var cmd = "search";
	    var keyword = $("#search_word").val();
	    if(keyword == ""){
	        return;
	    }
	    $("#search_btn").val("正在搜索...");
	    $("#search_btn").attr("disabled", "true");
	    var param = {"search_word": keyword};
	    ajax_post(cmd, param, function(ret){
            //刷新页面
            window.location.reload();
	    });
	});

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
});

function show_service_modal(id, name) {
     $("#service_start_id").val(id);
     $("#service_start_name").val(name);
     $("#service_start_message").text($("#service_start_message").text().replace("${SERVICE_NAME}", name));
     $('#service-modal').modal('show');
}

function show_download_modal(id, name){
    $("#download_start_id").val(id);
     $("#download_start_name").val(name);
     $("#download_start_message").text($("#download_start_message").text().replace("${MEDIA_NAME}", name));
     $('#download-modal').modal('show');
}