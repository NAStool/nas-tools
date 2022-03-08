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
        $("#search_ret").text("添加下载成功！")
        $("#search_ret").show()
	})
}

$(document).ready(function(){
    // 触发定时服务按钮
	$(".sch_action_btn").click(function(){
	    var cmd = "sch";
	    var data = {
	            "item": $(this).attr("id")
	        };
	    $(this).text("正在执行...");
	    $(this).attr("disabled", "true");
	    ajax_post(cmd, data, function(ret){
            item = ret.item
	        retmsg = ret.retmsg;
	        $("#sch_ret").show();
	        $("#sch_ret").text(retmsg);
	        $("#"+item).removeAttr("disabled");
	        $("#"+item).text("启动");
	    })
	});

	// 保存RSS按钮
	$("#rss_btn").click(function(){
	    var cmd = "rss";
	    var param = {};
	    $("#rss_form").find('input,textarea').each(function(){
	        if($(this).attr('name')){
	            param[$(this).attr('name')] = $(this).val();
	        }
        });
	    $("#rss_btn").text("正在处理...");
	    $("#rss_btn").attr("disabled", "true");
	    ajax_post(cmd, param, function(ret){
	        $("#rss_btn").removeAttr("disabled");
	        $("#rss_btn").text("保存");
	    });
	});

	// 保存KEY按钮
	$("#key_btn").click(function(){
	    var cmd = "key";
	    var param = {"movie_keys": $("#movie_keys").val(), "tv_keys": $("#tv_keys").val()};
	    $("#key_btn").text("正在处理...");
	    $("#key_btn").attr("disabled", "true");
	    ajax_post(cmd, param, function(ret){
	        $("#key_btn").removeAttr("disabled");
	        $("#key_btn").text("保存");
	    });
	});

	// 搜索按钮
	$("#search_btn").click(function(){
	    var cmd = "search";
	    var keyword = $("#search_word").val()
	    if(keyword == ""){
	        return
	    }
	    $("#search_btn").text("正在搜索...");
	    $("#search_btn").attr("disabled", "true");
	    var param = {"search_word": keyword};
	    ajax_post(cmd, param, function(ret){
            //显示数据到页面
            if(ret.code == 0){
                //没有查询到数据
                $("#search_results").html("<tr><td>没有检索到资源！</td><td></td><td></td><td></td></tr>")
	        }else{
	            all_html = ""
	            for(var i=0; i< ret.data.length; i++){
	                html = "<tr><td><a href=\"javascript:download_link('" + ret.data[i][0] + "')\">" + ret.data[i][1] + "</a></td><td>" + ret.data[i][2] + "</td><td>" + (ret.data[i][3]/1024/1024/1024).toFixed(2) + "GB</td><td>" + ret.data[i][4] + "</td></tr>"
	                all_html = all_html + html
	            }
	            $("#search_results").html(all_html)
	        }
	        $("#search_btn").removeAttr("disabled");
            $("#search_btn").text("搜索");
	    });
	});

});
