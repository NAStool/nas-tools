$(document).ready(function(){
    // 初始化编辑器
    var editor = ace.edit("editor");
	editor.setTheme("ace/theme/github");
	editor.session.setMode("ace/mode/ini");
	editor.setFontSize(14);

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

    // qBittorrent下拉选择变化
	$("#rmt_path").change(function(){
	    path = $("#rmt_path").val().split('|')[0];
	    pos = path.lastIndexOf("/")
	    name = path.substring(pos + 1);
	    $("#rmt_name").val(name);
	});

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
	        $("#" + item).removeAttr("disabled");
	        $("#" + item).text("启动");
	    })
	});

    // 获取qBittorrent下拉框内容
    $("#rmt_tab").click(function(){
	    var cmd = "rmt_qry";
	    var data = {};
	    ajax_post(cmd, data, function(ret){
	        rmt_paths = ret.rmt_paths;
            $("#rmt_path").empty();
            $("#rmt_path").append("<option value =\"\">全部</option>");
            for(var i=0; i<rmt_paths.length; i++){
                path = rmt_paths[i].split("|")[0];
                $("#rmt_path").append("<option value=\"" + rmt_paths[i] + "\">" + path + "</option>");
            }
	    });
	});

    // qBittorrent转移按钮
	$("#rmt_btn").click(function(){
	    var cmd = "rmt";
	    var data = {
	            "name": $("#rmt_name").val(),
	            "path": $("#rmt_path").val(),
	            "year": $("#rmt_year").val(),
	            "type": $("#rmt_type").val(),
	            "season": $("#rmt_season").val()
	        };
	   	$("#rmt_btn").text("正在处理...");
	    $("#rmt_btn").attr("disabled", "true");
	    ajax_post(cmd, data, function(ret){
	        rmt_stderr = ret.rmt_stderr;
	        rmt_stdout = ret.rmt_stdout;
	        rmt_paths = ret.rmt_paths;
	        $("#rmt_ret").show();
            $("#rmt_ret").text(rmt_stdout)

            $("#rmt_name").val("");
            $("#rmt_year").val("");
            $("#rmt_type").val("");
            $("#rmt_season").val("");
            $("#rmt_path").empty();
            $("#rmt_path").append("<option value =\"\">全部</option>");
            for(var i=0; i<rmt_paths.length; i++){
                path = rmt_paths[i].split("|")[0];
                $("#rmt_path").append("<option value=\"" + rmt_paths[i] + "\">" + path + "</option>");
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
	        msg_msg = ret.msg_msg;
	        $("#msg_ret").show();
	        $("#msg_ret").text(msg_msg);
	        $("#msg_btn").removeAttr("disabled");
	        $("#msg_btn").text("发送");
	    });
	});

	// 保存RSS按钮
	$("#rss_btn").click(function(){
	    var cmd = "rss";
	    var job_str = ""
	    var data = {
                "job": job_str,
                ""
	        };
	    $("#rss_btn").text("正在处理...");
	    $("#rss_btn").attr("disabled", "true");
	    ajax_post(cmd, data, function(ret){
	        $("#form_rss_form_notice").show();
	        $("#form_rss_form_notice").text(ret.msg_msg);
	        $("#rss_btn").removeAttr("disabled");
	        $("#rss_btn").text("保存");
	    });
	});

	// 获取配置文件
    $("#set_tab").click(function(){
        var cmd = "set_qry";
        var data = {}
        ajax_post(cmd, data, function(ret){
	        config_str = ret.config_str;
	        editor.getSession().setValue(config_str)
	    });
    });

    // 配置文件保存按钮
	$("#set_btn").click(function(){
	    var cmd = "set";
	    var data = {
	            "editer_str": editor.getSession().getValue()
	        };
	    $("#set_btn").text("正在处理...");
	    $("#set_btn").attr("disabled", "true");
	    ajax_post(cmd, data, function(ret){
	        $("#set_btn").removeAttr("disabled");
	        $("#set_btn").text("保存");
	    });
	});

	// 显示日志
    $("#log_tab").click(function(){
	    var cmd = "log_qry";
	    var data = {};
	    ajax_post(cmd, data, function(ret){
	        log_list = ret.log_list;
	        $("#log_table").empty();
	        $("#log_table").append("<caption>日志</caption><thead><tr><th>序号</th><th>级别</th><th>名称</th><th>内容</th><th>时间</th></tr></thead>");
            for(log_item in log_list){
                $("#log_table").append("<tbody><tr>");
                $("#log_table").append("<td>" + log_item[0] + "</td>");
                $("#log_table").append("<td>" + log_item[1] + "</td>");
                $("#log_table").append("<td>" + log_item[2] + "</td>");
                $("#log_table").append("<td>" + log_item[3] + "</td>");
                $("#log_table").append("<td>" + log_item[4] + "</td>");
                $("#log_table").append("</tr><tbody>");
            }
	    });
	});

    $("#rmt_tab").click();
});