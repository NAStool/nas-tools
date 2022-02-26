$(document).ready(function(){

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
            success: handler,
            error: function(xhr, textStatus, errorThrown){
                alert("错误信息:"+xhr.responseText);
            }
        });
    }

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

});