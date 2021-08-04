$(document).ready(function(){
    //初始化编辑器
    var editor = ace.edit("editor");
	editor.setTheme("ace/theme/github");
	editor.session.setMode("ace/mode/ini");
	editor.setFontSize(14);

	$("#rmt_path").change(function(){
	    path = $("#rmt_path").val();
	    pos = path.lastIndexOf("/")
	    name = path.substring(pos + 1);
	    $("#rmt_name").val(name);
	});

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
	        $("#" + item).removeAttr("disabled");
	        $("#" + item).text("启动");
	    })
	});

    // qBittorrent转移按钮
	$("#rmt_btn").click(function(){
	    var cmd = "rmt";
	    var data = {
	            "name": $("#rmt_name").val(),
	            "path": $("#rmt_path").val(),
	            "hash": $("#rmt_hash").val()
	        };
	   	$("#rmt_btn").text("正在处理...");
	    $("#rmt_btn").attr("disabled", "true");
	    ajax_post(cmd, data, function(ret){
	        rmt_stderr = ret.rmt_stderr;
	        rmt_stdout = ret.rmt_stdout;
	        rmt_paths = ret.rmt_paths;
	        rmt_hashs = ret.rmt_hashs;
	        $("#rmt_ret").show();
            if (rmt_stderr != ""){
                $("#rmt_ret").text(rmt_stderr)
            }else{
                $("#rmt_ret").text(rmt_stdout)
            }

            $("#rmt_path").empty();
            $("#rmt_path").append("<option value =\"\">全部</option>");
            for(var i=0; i<rmt_paths.length; i++){
                $("#rmt_path").append("<option value=\"" + rmt_paths[i] + "\">" + rmt_paths[i] + "</option>");
            }

            $("#rmt_hash").empty();
            $("#rmt_hash").append("<option value =\"\">全部</option>");
            for(var i=0; i<rmt_hashs.length; i++){
                value = rmt_hashs[i].split("|")[1];
                $("#rmt_hash").append("<option value=\"" + value + "\">" + rmt_hashs[i] + "</option>");
            }

            $("#rmt_btn").removeAttr("disabled");
	        $("#rmt_btn").text("转移");
	    });
	});

    // 发送消息按钮
	$("#msg_btn").click(function(){
	    var cmd = "msg";
	    var data = {
	            "title": $("#msg_title").val(),
	            "text": $("#msg_text").val()
	        };
	    $("#msg_btn").text("正在处理...");
	    $("#msg_btn").attr("disabled", "true");
	    ajax_post(cmd, data, function(ret){
	        msg_code = ret.msg_code;
	        msg_msg = ret.msg_msg;
	        $("#msg_ret").show();
	        $("#msg_ret").text("{\"msg_code\": " + msg_code + ", \"msg_msg\": " + msg_msg + "}");
	        $("#msg_btn").removeAttr("disabled");
	        $("#msg_btn").text("发送");
	    });
	});

    // 配置文件按钮
	$("#set_btn").click(function(){
	    var cmd = "set";
	    var data = {
	            "editer_str": editor.getSession().getValue()
	        };
	    $("#set_btn").text("正在处理...");
	    $("#set_btn").attr("disabled", "true");
	    ajax_post(cmd, data, function(ret){
	        config_str = ret.config_str;
	        editor.getSession().setValue(config_str)
	        $("#set_btn").removeAttr("disabled");
	        $("#set_btn").text("保存");
	    });
	});

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

});