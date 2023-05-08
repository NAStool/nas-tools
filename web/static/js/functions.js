/**
 * 公共变量区
 */

// 刷新订阅站点列表
let RssSitesLength = 0;
// 刷新搜索站点列表
let SearchSitesLength = 0;
// 种子上传控件
let TorrentDropZone;
// 默认转移模式
let DefaultTransferMode;
// 默认路径
let DefaultPath;
// 页面正在加载中的标志
let NavPageLoading = false;
// 加载中页面的字柄
let NavPageXhr;
// 是否允许打断弹窗
let GlobalModalAbort = true;
// 进度刷新EventSource
let ProgressES;
// 日志来源筛选时关掉之前的刷新日志计时器
let LoggingSource = "";
// 日志EventSource
let LoggingES;
// 是否存量消息刷新
let OldMessageFlag = true;
// 消息WebSocket
let MessageWS;
// 当前协议
let WSProtocol = "ws://";
if (window.location.protocol === "https:") {
  WSProtocol = "wss://"
}


/**
 * 公共函数区
 */

// 导航菜单点击
function navmenu(page, newflag = false) {
  if (!newflag) {
    // 更新当前历史记录
    window_history();
  }
  // 修复空格问题
  page = page.replaceAll(" ", "%20");
  // 主动点击时清除页码, 刷新页面也需要清除
  sessionStorage.removeItem("CurrentPage");
  // 展开菜单
  document.querySelector("#navbar-menu").update_active(page);
  // 解除滚动事件
  $(window).unbind('scroll');
  // 显示进度条
  NProgress.start();
  // 停止上一次加载
  if (NavPageXhr && NavPageLoading) {
    NavPageXhr.abort();
  }
  // 加载新页面
  NavPageLoading = true;
  NavPageXhr = $.ajax({
    url: page,
    dataType: 'html',
    success: function (data) {
      // 演染
      let page_content = $("#page_content");
      page_content.html(data);
      // 加载完成
      NavPageLoading = false;
      // 隐藏进度条
      NProgress.done();
      // 修复登录页面刷新问题
      if (page_content.find("title").first().text() === "登录 - NAStool") {
        // 刷新页面
        window.location.reload();
      } else {
        // 关掉已经打开的弹窗
        if (GlobalModalAbort) {
          $(".modal").modal("hide");
        }
        // 刷新tooltip
        fresh_tooltip();
        // 刷新filetree控件
        init_filetree_element();
      }
      if (page !== CurrentPageUri) {
        // 切换页面时滚动到顶部
        $(window).scrollTop(0);
        // 记录当前页面ID
        CurrentPageUri = page;
      }
      // 并记录当前历史记录
      window_history(!newflag);
    }
  });
}

// 搜索
function media_search(tmdbid, title, type) {
  const param = {"tmdbid": tmdbid, "search_word": title, "media_type": type};
  show_refresh_progress("正在搜索 " + title + " ...", "search");
  ajax_post("search", param, function (ret) {
    hide_refresh_process();
    if (ret.code === 0) {
      navmenu('search?s=' + title)
    } else {
      show_fail_modal(ret.msg);
    }
  }, true, false);
}

// 显示全局加载蒙版
function show_wait_modal(blur) {
  if (blur) {
    $('#modal-wait').addClass('modal-blur');
  } else {
    $('#modal-wait').removeClass('modal-blur');
  }
  $("#modal-wait").modal("show");
}

// 关闭全局加载蒙版
function hide_wait_modal() {
  $("#modal-wait").modal("hide");
}

// 停止日志服务
function stop_logging() {
  if (LoggingES) {
    LoggingES.close();
    LoggingES = undefined;
  }
}

// 连接日志服务
function start_logging() {
  stop_logging();
  LoggingES = new EventSource(`stream-logging?source=${LoggingSource}`);
  LoggingES.onmessage = function (event) {
    render_logging(JSON.parse(event.data))
  };
}

// 刷新日志
function render_logging(log_list) {
  if (log_list) {
    let tdstyle = "padding-top: 0.5rem; padding-bottom: 0.5rem";
    let tbody = "";
    for (let log of log_list) {
      let text = log.text;
      const source = log.source;
      const time = log.time;
      const level = log.level;
      let tcolor = '';
      let bgcolor = '';
      let tstyle = '-webkit-line-clamp:4; display: -webkit-box; -webkit-box-orient:vertical; overflow:hidden; text-overflow: ellipsis;';
      if (level === "WARN") {
        tcolor = "text-warning";
        bgcolor = "bg-warning";
      } else if (level === "ERROR") {
        tcolor = "text-danger";
        bgcolor = "bg-danger";
      } else if (source === "System") {
        tcolor = "text-info";
        bgcolor = "bg-info";
      } else {
        tcolor = "text";
      }
      if (["Rmt", "Plugin"].includes(source) && text.includes(" 到 ")) {
        tstyle = `${tstyle} white-space: pre;`
        text = text.replace(/\s到\s/, "\n=> ")
      }
      if (text.includes("http") || text.includes("magnet")) {
        tstyle = `${tstyle} word-break: break-all;`
        text = text.replace(/：((?:http|magnet).+?)(?:\s|$)/g, "：<a href='$1' target='_blank'>$1</a>")
      }
      tbody = `${tbody}
                  <tr>
                  <td style="${tdstyle}"><span class="${tcolor}">${time}</span></td>
                  <td style="${tdstyle}"><span class="badge ${bgcolor}">${source}</span></td>
                  <td style="${tdstyle}"><span class="${tcolor}" style="${tstyle}" title="${text}">${text}</span></td>
                  </tr>`;
    }
    if (tbody) {
      let logging_table_obj = $("#logging_table");
      let bool_ToScrolTop = (logging_table_obj.scrollTop() + logging_table_obj.prop("offsetHeight")) >= logging_table_obj.prop("scrollHeight");
      let logging_content = $("#logging_content");
      if (logging_content.text().indexOf("刷新中...") !== -1) {
        logging_content.empty();
      }
      logging_content.append(tbody);
      if (bool_ToScrolTop) {
        setTimeout(function () {
          logging_table_obj.scrollTop(logging_table_obj.prop("scrollHeight"));
        }, 500);
      }
    }
  }
  if ($("#modal-logging").is(":hidden")) {
    stop_logging();
  }
}

// 暂停实时日志
function pause_logging() {
  let btn = $("#logging_stop_btn")
  if (btn.text() === "开始") {
    btn.text("暂停")
    start_logging()
  } else {
    btn.text("开始");
    stop_logging();
  }
}

// 显示实时日志
function show_logging_modal() {
  // 显示窗口
  $("#logging_stop_btn").text("暂停");
  $('#modal-logging').modal('show');
  // 连接日志服务
  start_logging();
}

// 日志来源筛选
function logger_select(source) {
  LoggingSource = source
  if (LoggingSource === "All") {
    LoggingSource = "";
  }
  let logtype = `刷新中...`;
  if (LoggingSource) {
    logtype = `【${LoggingSource}】刷新中...`;
  }
  $("#logging_content").html(`<tr><td colspan="3" class="text-center">${logtype}</td></tr>`);
  // 拉取新日志
  start_logging();
}

// 连接消息服务
function connect_message() {
  MessageWS = new ReconnectingWebSocket(WSProtocol + window.location.host + '/message');
  MessageWS.onmessage = function (event) {
    render_message(JSON.parse(event.data))
  };
  MessageWS.onopen = function (event) {
    get_message('');
  };
  MessageWS.onerror = function (event) {
    MessageWS.close();
    MessageWS = undefined;
  }

}

// 刷新消息中心
function render_message(ret) {
  let lst_time = ret.lst_time;
  const msgs = ret.message;
  if (msgs) {
    for (let msg of msgs) {
      // 消息UI
      let html_text = `<div class="list-group-item">
            <div class="row align-items-center">
              <div class="col-auto">
                <span class="avatar">NT</span>
              </div>
              <div class="col text-truncate">
                <span class="text-wrap">${msg.title}</span>
                <div class="d-block text-muted text-truncate mt-n1 text-wrap">${msg.content}</div>
                <div class="d-block text-muted text-truncate mt-n1 text-wrap">${msg.time}</div>
              </div>
            </div>
          </div>`;
      $("#system-messages").prepend(html_text);
      // 滚动到顶部
      $(".offcanvas-body").animate({scrollTop: 0}, 300);
      // 浏览器消息提醒
      if (!OldMessageFlag && !$("#offcanvasEnd").is(":hidden")) {
        browserNotification(msg.title, msg.content);
      }
    }
    // 非旧消息
    OldMessageFlag = false;
  }
  // 下一次处理
  if (lst_time) {
    setTimeout(`get_message('${lst_time}')`, 3000);
  } else if (msgs) {
    setTimeout(`get_message('')`, 3000);
  }
}

//发送拉取消息的请求
function get_message(lst_time) {
  if (!MessageWS) {
    return;
  }
  MessageWS.send(JSON.stringify({"lst_time": lst_time}));
}

//检查系统是否在线
function check_system_online() {
  ajax_post("refresh_process", {type: "restart"}, function (ret) {
    if (ret.code === -1) {
      logout();
    } else {
      setTimeout("check_system_online()", 1000);
    }
  }, true, false)
}

//注销
function logout() {
  ajax_post("logout", {}, function (ret) {
    window.location.href = "/";
  });
}

//重启
function restart() {
  show_confirm_modal("立即重启系统？", function () {
    hide_confirm_modal();
    ajax_post("restart", {}, function (ret) {
    }, true, false);
    show_wait_modal(true);
    setTimeout("check_system_online()", 5000);
  });
}

//更新
function update(version) {
  let title;
  if (version) {
    title = "是否确认更新到 " + version + " 版本？";
  } else {
    title = "将从Github拉取最新程序代码并重启，是否确认？";
  }
  show_confirm_modal(title, function () {
    hide_confirm_modal();
    ajax_post("update_system", {}, function (ret) {
    }, true, false)
    show_wait_modal(true);
    setTimeout("check_system_online()", 5000);
  });
}

// 显示配置不完整提示
function show_init_alert_modal() {
  GlobalModalAbort = false;
  show_fail_modal("请先配置TMDB API Key，并修改登录密码！", function () {
    GlobalModalAbort = true;
    navmenu('basic');
  });
}

// 显示用户认证对话框
function show_user_auth_modal() {
  GlobalModalAbort = false;
  $("#modal-user-auth").modal("show");
}

// 用户认证
function user_auth() {
  $("#user_auth_btn").text("认证中...").prop("disabled", true);
  let siteid = $("#user_auth_site").val();
  let params = input_select_GetVal(`user_auth_${siteid}_params`, `${siteid}_`);
  ajax_post("auth_user_level", {site: siteid, params: params}, function (ret) {
    GlobalModalAbort = true;
    $("#modal-user-auth").modal("hide");
    $("#user_auth_btn").prop("disabled", false).text("认证");
    if (ret.code === 0) {
      window.location.reload();
    } else {
      show_fail_modal(ret.msg);
    }
  }, true, false);
}

// 初始化tomselect
function init_tomselect() {
  let el;
  window.TomSelect && (new TomSelect(el = document.getElementById('user_auth_site'), {
    copyClassesToDropdown: false,
    dropdownClass: 'dropdown-menu ts-dropdown',
    optionClass: 'dropdown-item',
    controlInput: '<input>',
    render: {
      item: function (data, escape) {
        if (data.customProperties) {
          return '<div><span class="dropdown-item-indicator">' + data.customProperties + '</span>' + escape(data.text) + '</div>';
        }
        return '<div>' + escape(data.text) + '</div>';
      },
      option: function (data, escape) {
        if (data.customProperties) {
          return '<div><span class="dropdown-item-indicator">' + data.customProperties + '</span>' + escape(data.text) + '</div>';
        }
        return '<div>' + escape(data.text) + '</div>';
      },
    },
  }));
}

// TomSelect响应事件
function switch_cooperation_sites(obj) {
  let siteid = $(obj).val();
  $(".user_auth_params").hide();
  $(`#user_auth_${siteid}_params`).show();
}

// 停止刷新进度条
function stop_progress() {
  if (ProgressES) {
    ProgressES.close();
    ProgressES = undefined;
  }
}

// 刷新进度条
function start_progress(type) {
  stop_progress();
  ProgressES = new EventSource(`stream-progress?type=${type}`);
  ProgressES.onmessage = function (event) {
    render_progress(JSON.parse(event.data))
  };
}

// 渲染进度条
function render_progress(ret) {
  if (ret.code === 0 && ret.value <= 100) {
    $("#modal_process_bar").attr("style", "width: " + ret.value + "%").attr("aria-valuenow", ret.value);
    $("#modal_process_text").text(ret.text);
  }
  if ($("#modal-process").is(":hidden")) {
    stop_progress();
  }
}

// 显示全局进度框
function show_refresh_progress(title, type) {
  // 显示对话框
  if (title) {
    $("#modal_process_title").text(title);
  } else {
    $("#modal_process_title").hide();
  }
  $("#modal_process_bar").attr("style", "width: 0%").attr("aria-valuenow", 0);
  $("#modal_process_text").text("请稍候...");
  $("#modal-process").modal("show");
  // 开始刷新进度条
  setTimeout(`start_progress('${type}')`, 1000);
}

// 关闭全局进度框
function hide_refresh_process() {
  $("#modal-process").modal("hide");
}

// 显示确认提示框
function show_confirm_modal(title, func) {
  $("#system_confirm_message").text(title);
  $("#system_confirm_btn").unbind('click').click(func);
  $("#system-confirm-modal").modal("show");
}

// 隐藏确认提示框
function hide_confirm_modal() {
  $("#system-confirm-modal").modal("hide");
}

// 显示询问提示框
function show_ask_modal(title, func) {
  $("#system_ask_message").text(title);
  $("#system_ask_btn").unbind('click').click(func);
  $("#system-ask-modal").modal("show");
}

// 隐藏询问提示框
function hide_ask_modal() {
  $("#system-ask-modal").modal("hide");
}

// 显示成功提示
function show_success_modal(title, func) {
  $("#system_success_message").text(title);
  if (func) {
    $("#system_success_modal_btn").unbind('click').click(func);
  } else {
    $("#system_success_modal_btn").unbind('click');
  }
  $("#system-success-modal").modal("show");
}

// 显示失败提示
function show_fail_modal(title, func) {
  $("#system_fail_message").text(title);
  if (func) {
    $("#system_fail_modal_btn").unbind('click').click(func);
  } else {
    $("#system_fail_modal_btn").unbind('click');
  }
  $("#system-fail-modal").modal("show");
}

// 显示警告提示
function show_warning_modal(title, func) {
  $("#system_warning_message").text(title);
  if (func) {
    $("#system_warning_modal_btn").unbind('click').click(func);
  } else {
    $("#system_warning_modal_btn").unbind('click');
  }
  $("#system-warning-modal").modal("show");
}

//显示媒体详情弹窗
function show_mediainfo_modal(rtype, name, year, mediaid, page, rssid) {
  if (!page) {
    page = "";
  }
  if (!rssid) {
    rssid = "";
  }
  ajax_post("media_info", {
    "id": mediaid,
    "title": name,
    "year": year,
    "type": rtype,
    "page": page,
    "rssid": rssid
  }, function (ret) {
    if (ret.code === 0) {
      //显示信息
      $("#system_media_name").text(ret.title);
      $("#system_release_date").text(ret.release_date)
      if (ret.poster_path) {
        $("#system_media_poster").attr("img-src", ret.poster_path);
      } else {
        $("#system_media_poster").attr("img-src", "../static/img/no-image.png");
      }
      if (ret.overview && ret.overview.length > 200) {
        $("#system_media_overview").text(ret.overview.substr(0, 200) + " ...");
      } else {
        $("#system_media_overview").text(ret.overview);
      }
      if (!ret.vote_average || ret.vote_average == "0") {
        $("#system_media_vote").hide();
      } else {
        $("#system_media_vote").text(ret.vote_average).show();
      }
      //订阅按钮、搜索按钮
      if ($("#system_media_rss_dropdown").hasClass("show")) {
        $("#system_media_rss_btn").dropdown("toggle");
      }
      //先隐藏所有按钮，有需要再显示
      $("#system_media_rss_btn").hide();
      $("#system_media_search_btn").hide();
      $("#system_media_refresh_btn").hide();
      $("#system_media_url_btn").hide();
      if (ret.rssid) {
        //取消订阅按钮
        $("#system_media_rss_btn").text("取消订阅")
            .removeAttr("data-bs-toggle")
            .removeClass("dropdown-toggle")
            .attr("href", 'javascript:remove_rss_media("' + ret.title + '","' + ret.year + '","' + ret.type + '","' + ret.rssid + '","' + ret.page + '")')
            .show();
        //搜索按钮
        $("#system_media_search_btn").text("搜索")
            .attr("href", 'javascript:search_mediainfo_media("' + ret.tmdbid + '", "' + ret.title + '", "' + ret.type_str + '")')
            .show();
        //刷新和编辑按钮
        if (ret.page.startsWith("movie_rss") || ret.page.startsWith("tv_rss")) {
          //编辑
          $("#system_media_url_btn").text("编辑")
              .attr("href", "javascript:show_edit_rss_media_modal('" + ret.rssid + "', '" + ret.type_str + "')")
              .show();
          //刷新
          $("#system_media_refresh_btn").text("刷新")
              .attr("href", 'javascript:refresh_rss_media("' + ret.type + '","' + ret.rssid + '","' + ret.page + '")')
              .show();
        } else {
          //详情按钮
          $("#system_media_url_btn").text("详情")
              .attr("href", 'javascript:navmenu("media_detail?type=' + ret.type + '&id=' + ret.tmdbid + '")')
              .show();
        }
      } else {
        //详情按钮
        $("#system_media_url_btn").text("详情")
            .attr("href", 'javascript:navmenu("media_detail?type=' + ret.type + '&id=' + ret.tmdbid + '")')
            .show();
        //订阅按钮
        $("#system_media_rss_btn").text("订阅");
        $("#system_media_rss_dropdown").empty();
        if (ret.seasons.length === 0) {
          $("#system_media_rss_btn").removeAttr("data-bs-toggle")
              .removeClass("dropdown-toggle")
              .attr("href", 'javascript:add_rss_media("' + ret.title + '","' + ret.year + '","' + ret.type + '","' + ret.tmdbid + '","' + ret.page + '","")')
        } else {
          $("#system_media_rss_btn").prop("data-bs-toggle", "dropdown")
              .addClass("dropdown-toggle")
              .attr("href", 'javascript:$("#system_media_rss_btn").dropdown("toggle")')
          //订阅季的下拉框
          for (let i = 0; i < ret.seasons.length; i++) {
            $("#system_media_rss_dropdown").append('<a class="dropdown-item" href=\'javascript:add_rss_media("' + ret.title + '","' + ret.year + '","' + ret.type + '","' + ret.tmdbid + '","' + ret.page + '","' + ret.seasons[i].num + '")\'>' + ret.seasons[i].text + '</a>');
          }
        }
        $("#system_media_rss_btn").show();
        //搜索按钮
        $("#system_media_search_btn").text("搜索")
            .attr("href", 'javascript:search_mediainfo_media("' + ret.tmdbid + '", "' + ret.title + '", "' + ret.type_str + '")')
            .show();
      }
      $("#system_media_name_link").attr("href", ret.link_url);
      //弹窗
      $("#system-media-modal").modal("show");
    } else if (ret.code === 1) {
      if (ret.rssid) {
        show_edit_rss_media_modal(ret.rssid, ret.type_str);
      } else {
        show_fail_modal(`${name} 未查询到TMDB媒体信息！`);
      }
    }
  });
}

//隐藏媒体详情
function hide_mediainfo_modal() {
  $("#system-media-modal").modal("hide");
}

//新增订阅
function add_rss_media(name, year, type, mediaid, page, season, func) {
  hide_mediainfo_modal();
  let data = {
    "name": name,
    "type": type,
    "year": year,
    "mediaid": mediaid,
    "page": page,
    "season": season
  };
  ajax_post("add_rss_media", data, function (ret) {
    if (ret.code === 0) {
      if (ret.page) {
        navmenu(ret.page);
      } else {
        if (func) {
          func();
        }
        show_rss_success_modal(ret.rssid, type, name + " 添加订阅成功！")
      }
    } else {
      show_fail_modal(`${ret.name} 添加订阅失败：${ret.msg}！`);
    }
  });
}

// 取消订阅
function remove_rss_media(name, year, type, rssid, page, tmdbid, func) {
  hide_mediainfo_modal();
  let data = {"name": name, "type": type, "year": year, "rssid": rssid, "page": page, "tmdbid": tmdbid};
  ajax_post("remove_rss_media", data, function (ret) {
    if (func) {
      func();
    } else if (ret.page) {
      window_history_refresh();
    } else {
      show_success_modal(ret.name + " 已从订阅中移除！");
    }
  });
}

// 刷新订阅
function refresh_rss_media(type, rssid, page) {
  hide_mediainfo_modal();
  ajax_post("refresh_rss", {"type": type, "rssid": rssid, "page": page}, function (ret) {
    if (ret.page) {
      window_history_refresh();
    } else {

    }
  });
}

//显示订阅季选择框
function show_rss_seasons_modal(name, year, type, mediaid, seasons, func) {
  let system_rss_seasons_content = "";
  for (let season of seasons) {
    system_rss_seasons_content += `<label class="form-selectgroup-item">
                                    <input type="checkbox" name="system_rss_season" value="${season.num}" class="form-selectgroup-input">
                                    <span class="form-selectgroup-label">${season.text}</span>
                                   </label>`;
  }
  $("#system_rss_seasons_group").empty().append(system_rss_seasons_content)
  $("#system_rss_seasons_btn").unbind('click').click(function () {
    $("#system-rss-seasons").modal('hide');
    let rss_seasons = select_GetSelectedVAL("system_rss_season");
    if (rss_seasons.length > 0) {
      add_rss_media(name, year, type, mediaid, '', rss_seasons, func);
    }
  });
  $("#system-rss-seasons").modal('show');
}

//搜索
function search_mediainfo_media(tmdbid, title, typestr) {
  hide_mediainfo_modal();
  const param = {"tmdbid": tmdbid, "search_word": title, "media_type": typestr};
  show_refresh_progress("正在搜索 " + title + " ...", "search");
  ajax_post("search", param, function (ret) {
    hide_refresh_process();
    if (ret.code === 0) {
      navmenu('search?s=' + title);
    } else {
      show_fail_modal(ret.msg);
    }
  }, true, false);
}

//新增订阅
function add_rss_manual(flag) {
  const mtype = $("#rss_type").val();
  const name = $("#rss_name").val();
  const year = $("#rss_year").val();
  const keyword = $("#rss_keyword").val();
  const season = $("#rss_season").val();
  const fuzzy_match = $("#fuzzy_match").prop("checked");
  const mediaid = $("#rss_tmdbid").val();
  const over_edition = $("#over_edition").prop("checked");
  const filter_restype = $("#rss_restype").val();
  const filter_pix = $("#rss_pix").val();
  const filter_team = $("#rss_team").val();
  const filter_rule = $("#rss_rule").val();
  const filter_include = $("#rss_include").val();
  const filter_exclude = $("#rss_exclude").val();
  const save_path = get_savepath("rss_save_path", "rss_save_path_manual");
  const download_setting = $("#rss_download_setting").val();
  const total_ep = $("#rss_total_ep").val();
  const current_ep = $("#rss_current_ep").val();
  const rssid = $("#rss_id").val();
  if (!name) {
    $("#rss_name").addClass("is-invalid");
    return;
  } else {
    $("#rss_name").removeClass("is-invalid");
  }
  if (year && isNaN(year)) {
    $("#rss_year").addClass("is-invalid");
    return;
  } else {
    $("#rss_year").removeClass("is-invalid");
  }
  if (!fuzzy_match && !season && (mtype == "TV" || mtype == "电视剧")) {
    $("#rss_season").addClass("is-invalid");
    return;
  } else {
    $("#rss_season").removeClass("is-invalid");
  }
  if (total_ep && isNaN(total_ep)) {
    $("#rss_total_ep").addClass("is-invalid");
    return;
  } else {
    $("#rss_total_ep").removeClass("is-invalid");
  }
  if (current_ep && isNaN(current_ep)) {
    $("#rss_current_ep").addClass("is-invalid");
    return;
  } else {
    $("#rss_current_ep").removeClass("is-invalid");
  }
  //订阅站点
  let rss_sites = select_GetSelectedVAL("rss_sites");
  if (rss_sites.length === RssSitesLength) {
    rss_sites = [];
  }
  //搜索站点
  let search_sites = [];
  if (!fuzzy_match) {
    search_sites = select_GetSelectedVAL("search_sites");
    if (search_sites.length === SearchSitesLength) {
      search_sites = [];
    }
  }
  // 储存订阅设置
  const rss_setting = {
    "filter_restype": filter_restype,
    "filter_pix": filter_pix,
    "filter_team": filter_team,
    "filter_rule": filter_rule,
    "filter_include": filter_include,
    "filter_exclude": filter_exclude,
    "save_path": save_path,
    "download_setting": download_setting,
    "rss_sites": rss_sites,
    "search_sites": search_sites
  };
  if (mtype === "TV") {
    localStorage.setItem("RssSettingTV", JSON.stringify(rss_setting));
  } else if (mtype === "MOV") {
    localStorage.setItem("RssSettingMOV", JSON.stringify(rss_setting));
  }
  const data = {
    ...{
      "type": mtype,
      "name": name,
      "year": year,
      "season": season,
      "fuzzy_match": fuzzy_match,
      "mediaid": mediaid,
      "over_edition": over_edition,
      "total_ep": total_ep,
      "current_ep": current_ep,
      "rssid": rssid,
      "keyword": keyword,
      "in_form": "manual"
    }, ...rss_setting
  };
  $("#modal-manual-rss").modal("hide");
  ajax_post("add_rss_media", data, function (ret) {
    if (ret.code === 0) {
      if (CurrentPageUri.startsWith("tv_rss") || CurrentPageUri.startsWith("movie_rss")) {
        window_history_refresh();
      } else {
        show_rss_success_modal(ret.rssid, type, name + " 添加订阅成功！");
      }
      if (flag) {
        show_add_rss_media_modal(mtype);
      }
    } else {
      if (CurrentPageUri.startsWith("tv_rss") || CurrentPageUri.startsWith("movie_rss")) {
        show_fail_modal(`${ret.name} 订阅失败：${ret.msg}！`, function () {
          $("#modal-manual-rss").modal("show");
        });
      } else {
        show_fail_modal(`${ret.name} 订阅失败：${ret.msg}！`);
      }
    }
  });
}

// 选择模糊匹配
function change_match_check(obj) {
  if ($(obj).prop("checked")) {
    $("#rss_search_sites_div").hide();
    $("#over_edition").prop("checked", false);
  } else {
    $("#rss_search_sites_div").show();
  }
}

// 选择洗版
function change_over_edition_check(obj) {
  if ($(obj).prop("checked")) {
    $("#fuzzy_match").prop("checked", false);
    $("#rss_search_sites_div").show();
  }
}

//取消订阅
function remove_rss_manual(type, name, year, rssid) {
  $("#modal-manual-rss").modal('hide');
  let page;
  if (CurrentPageUri.startsWith("tv_rss")) {
    page = "tv_rss";
  } else if (CurrentPageUri.startsWith("movie_rss")) {
    page = "movie_rss";
  } else {
    page = undefined
  }
  remove_rss_media(name, year, type, rssid, page);
}

// 新增订阅
function show_add_rss_media_modal(mtype) {
  // 刷新下拉框
  refresh_rss_download_setting_dirs();
  // 界面初始化
  $("#rss_id").val("");
  $("#rss_modal_title").text("新增订阅");
  $("#rss_name").val("").attr("readonly", false);
  $("#rss_year").val("").attr("readonly", false);
  $("#rss_keyword").val("");
  $("#rss_tmdbid").val("");
  $("#fuzzy_match").prop("checked", false);
  $("#over_edition").prop("checked", false);
  $("#rss_season").val("");
  $("#rss_total_ep").val("");
  $("#rss_current_ep").val("");
  let rss_setting;
  if (mtype === "TV") {
    $("#rss_type").val("TV");
    $("#rss_tv_season_div").show();
    rss_setting = localStorage.getItem("RssSettingTV");
  } else if (mtype === "MOV") {
    $("#rss_type").val("MOV");
    $("#rss_tv_season_div").hide();
    rss_setting = localStorage.getItem("RssSettingMOV");
  }
  if (rss_setting) {
    rss_setting = JSON.parse(rss_setting);
    $("#rss_restype").val(rss_setting.filter_restype);
    $("#rss_pix").val(rss_setting.filter_pix);
    $("#rss_team").val(rss_setting.filter_team);
    $("#rss_rule").val(rss_setting.filter_rule);
    $("#rss_include").val(rss_setting.filter_include);
    $("#rss_exclude").val(rss_setting.filter_exclude);
    $("#rss_download_setting").val(rss_setting.download_setting);
    refresh_savepath_select('rss_save_path', false, rss_setting.download_setting);
    check_manual_input_path("rss_save_path", "rss_save_path_manual", rss_setting.save_path);
    if (rss_setting.search_sites.length === 0) {
      select_SelectALL(true, 'search_sites');
    } else {
      select_SelectPart(rss_setting.search_sites, 'search_sites');
    }
    if (rss_setting.rss_sites.length === 0) {
      select_SelectALL(true, 'rss_sites');
    } else {
      select_SelectPart(rss_setting.rss_sites, 'rss_sites');
    }
  } else {
    $("#rss_restype").val('');
    $("#rss_pix").val('');
    $("#rss_team").val('');
    $("#rss_rule").val('');
    $("#rss_include").val('');
    $("#rss_exclude").val('');
    $("#rss_save_path").val('');
    $("#rss_save_path_manual").val('');
    $("#rss_download_setting").val('');
    select_SelectALL(false, "rss_sites");
    select_SelectALL(false, "search_sites");
  }
  $("[name='rss_edit_btn']").hide();
  $("[name='rss_add_btn']").show();
  $("#rss_delete_btn").hide();
  $("#modal-manual-rss").modal('show');
}

// 显示默认订阅设置页面
function show_default_rss_setting_modal(mtype) {
  refresh_rsssites_select("default_rss_setting_rss_sites_group", "default_rss_sites", false);
  refresh_searchsites_select("default_rss_setting_search_sites_group", "default_search_sites", false);
  refresh_filter_select("default_rss_setting_rule", false);
  refresh_downloadsetting_select("default_rss_setting_download_setting", false)

  // 查询已保存配置
  ajax_post("get_default_rss_setting", {mtype: mtype}, function (ret) {
    if (ret.code === 0 && ret.data) {
      $("#default_rss_setting_restype").val(ret.data.restype);
      $("#default_rss_setting_pix").val(ret.data.pix);
      $("#default_rss_setting_team").val(ret.data.team);
      $("#default_rss_setting_rule").val(ret.data.rule);
      $("#default_rss_setting_include").val(ret.data.include);
      $("#default_rss_setting_exclude").val(ret.data.exclude);
      $("#default_rss_setting_download_setting").val(ret.data.download_setting);
      $("#default_rss_setting_over_edition").val(ret.data.over_edition);
      if (ret.data.rss_sites.length === 0) {
        select_SelectALL(false, 'default_rss_sites');
      } else {
        select_SelectPart(ret.data.rss_sites, 'default_rss_sites')
      }
      if (ret.data.search_sites.length === 0) {
        select_SelectALL(false, 'default_search_sites');
      } else {
        select_SelectPart(ret.data.search_sites, 'default_search_sites')
      }
    } else {
      $("#default_rss_setting_restype").val('');
      $("#default_rss_setting_pix").val('');
      $("#default_rss_setting_team").val('');
      $("#default_rss_setting_rule").val('');
      $("#default_rss_setting_include").val('');
      $("#default_rss_setting_exclude").val('');
      $("#default_rss_setting_download_setting").val('');
      $("#default_rss_setting_over_edition").val('0');
      select_SelectALL(false, "default_rss_sites");
      select_SelectALL(false, "default_search_sites");
    }
    $("#default_rss_setting_mtype").val(mtype);
    $("#modal-default-rss-setting").modal('show');
  });
}

// 保存默认订阅设置
function save_default_rss_setting() {
  const rss_sites = select_GetSelectedVAL("default_rss_sites");
  const search_sites = select_GetSelectedVAL("default_search_sites");
  const sites = {
    rss_sites: (rss_sites.length === RssSitesLength) ? [] : rss_sites,
    search_sites: (search_sites.length === SearchSitesLength) ? [] : search_sites
  };
  const common = input_select_GetVal("modal-default-rss-setting", "default_rss_setting_");
  const key = common.mtype === "MOV" ? "DefaultRssSettingMOV" : "DefaultRssSettingTV";
  const value = {...common, ...sites};
  $("#modal-default-rss-setting").modal("hide");
  ajax_post("set_system_config", {key: key, value: value}, function (ret) {
    if (ret.code === 0) {
      show_success_modal("设置订阅默认配置成功！");
    } else {
      show_fail_modal(`设置订阅默认配置失败：${ret.msg}！`);
    }
  });
}

// 显示编辑订阅
function show_edit_rss_media_modal(rssid, type) {
  $("#system-media-modal").modal('hide');
  $("#rss_id").val(rssid);
  $("#rss_type").val(type);
  $("#rss_modal_title").text("编辑订阅");

  // 刷新下拉框
  refresh_rss_download_setting_dirs();

  // 获取订阅信息
  ajax_post("rss_detail", {"rssid": rssid, "rsstype": type}, function (ret) {
    if (ret.code === 0) {
      $("#rss_tmdbid").val(ret.detail.tmdbid);
      $("#rss_name").val(ret.detail.name).attr("readonly", true);
      $("#rss_year").val(ret.detail.year).attr("readonly", true);
      $("#rss_keyword").val(ret.detail.keyword);
      if (type == "MOV" || type == "电影") {
        $("#rss_tv_season_div").hide();
        $("#rss_season").val("");
        $("#rss_total_ep").val("");
        $("#rss_current_ep").val("");
      } else {
        $("#rss_tv_season_div").show();
        if (ret.detail.season) {
          $("#rss_season").val(parseInt(ret.detail.season.replace("S", "")));
        } else {
          $("#rss_season").val("");
        }
        if (ret.detail.total_ep) {
          $("#rss_total_ep").val(ret.detail.total_ep);
        } else {
          $("#rss_total_ep").val("");
        }
        if (ret.detail.current_ep) {
          $("#rss_current_ep").val(ret.detail.current_ep);
        } else {
          $("#rss_current_ep").val("");
        }
      }
      if (!ret.detail.fuzzy_match) {
        $("#fuzz_match").prop("checked", false);
        $("#rss_search_sites_div").show();
      } else {
        $("#fuzzy_match").prop("checked", true);
        $("#rss_search_sites_div").hide();
      }
      if (ret.detail.over_edition) {
        $("#over_edition").prop("checked", true);
      } else {
        $("#over_edition").prop("checked", false);
      }
      $("#rss_restype").val(ret.detail.filter_restype);
      $("#rss_pix").val(ret.detail.filter_pix);
      $("#rss_team").val(ret.detail.filter_team);
      $("#rss_rule").val(ret.detail.filter_rule);
      $("#rss_include").val(ret.detail.filter_include);
      $("#rss_exclude").val(ret.detail.filter_exclude);
      $("#rss_download_setting").val(ret.detail.download_setting);
      refresh_savepath_select('rss_save_path', false, ret.detail.download_setting);
      check_manual_input_path("rss_save_path", "rss_save_path_manual", ret.detail.save_path);
      if (ret.detail.rss_sites.length === 0) {
        select_SelectALL(true, 'rss_sites');
      } else {
        select_SelectPart(ret.detail.rss_sites, 'rss_sites')
      }
      if (ret.detail.search_sites.length === 0) {
        select_SelectALL(true, 'search_sites');
      } else {
        select_SelectPart(ret.detail.search_sites, 'search_sites')
      }
      $("[name='rss_add_btn']").hide();
      $("[name='rss_edit_btn']").show();
      $("#rss_delete_btn").attr("href",
          `javascript:remove_rss_manual('${ret.detail.type}','${ret.detail.name}','${ret.detail.year}','${rssid}')`)
          .show();
      $("#modal-manual-rss").modal('show');
    }
  });
}

// 显示订阅成功（带后续操作）
function show_rss_success_modal(rssid, type, text) {
  $("#system_success_action_message").text(text);
  if (rssid) {
    $("#system_success_action_btn").text("编辑订阅")
        .unbind('click').click(function () {
      $("#system-success-action-modal").modal('hide');
      show_edit_rss_media_modal(rssid, type);
    });
    ;
    $("#system_success_action_div").show();
  } else {
    $("#system_success_action_div").hide();
  }
  $("#system-success-action-modal").modal('show');
}

// 刷新规则下拉框
function refresh_filter_select(obj_id, aync = true) {
  ajax_post("get_filterrules", {}, function (ret) {
    if (ret.code === 0) {
      let rule_select = $(`#${obj_id}`);
      let rule_select_content = `<option value="">站点规则</option>`;
      for (let ruleGroup of ret.ruleGroups) {
        rule_select_content += `<option value="${ruleGroup.id}">${ruleGroup.name}</option>`;
      }
      rule_select.empty().append(rule_select_content);
    }
  }, aync);
}

// 刷新RSS站点下拉框
function refresh_rsssites_select(obj_id, item_name, aync = true) {
  ajax_post("get_sites", {rss: true, basic: true}, function (ret) {
    if (ret.code === 0) {
      let rsssites_select = $(`#${obj_id}`);
      let rsssites_select_content = "";
      RssSitesLength = ret.sites.length;
      if (ret.sites.length > 0) {
        rsssites_select.parent().parent().show();
      } else {
        rsssites_select.parent().parent().hide();
      }
      for (let site of ret.sites) {
        rsssites_select_content += `
        <label class="form-selectgroup-item">
          <input type="checkbox" name="${item_name}" value="${site.name}" class="form-selectgroup-input">
          <span class="form-selectgroup-label">${site.name}</span>
        </label>`;
      }
      rsssites_select.empty().append(rsssites_select_content);
    }
  }, aync);
}

// 刷新搜索站点列表
function refresh_searchsites_select(obj_id, item_name, aync = true) {
  ajax_post("get_indexers", {check: true, basic: true}, function (ret) {
    if (ret.code === 0) {
      let searchsites_select = $(`#${obj_id}`);
      let searchsites_select_content = "";
      SearchSitesLength = ret.indexers.length;
      if (ret.indexers.length > 0) {
        searchsites_select.parent().parent().show();
      } else {
        searchsites_select.parent().parent().hide();
      }
      for (let indexer of ret.indexers) {
        searchsites_select_content += `
        <label class="form-selectgroup-item">
          <input type="checkbox" name="${item_name}" value="${indexer.name}" class="form-selectgroup-input">
          <span class="form-selectgroup-label">${indexer.name}</span>
        </label>`;
      }
      searchsites_select.empty().append(searchsites_select_content);
    }
  }, aync);
}

// 刷新搜索站点下拉框
function refresh_site_options(obj_id, show_all = false) {
  ajax_post("get_indexers", {check: true, basic: true}, function (ret) {
    if (ret.code === 0) {
      let site_options = '';
      if (show_all) {
        site_options += `<option value="">全部</option>`;
      }
      for (let indexer of ret.indexers) {
        site_options += `<option value="${indexer.name}">${indexer.name}</option>`;
      }
      $(`#${obj_id}`).empty().append(site_options);
    }
  });
}

// 刷新保存路径
function refresh_savepath_select(obj_id, aync = true, sid = "", is_default = false, site = "") {
  let savepath_select = $(`#${obj_id}`);
  let savepath_input_manual = $(`#${obj_id}_manual`);
  let savepath_select_content = `<option value="" selected>自动</option>`;
  if (!sid && !is_default && !site) {
    savepath_select_content += `<option value="manual">--手动输入--</option>`;
    savepath_select.empty().append(savepath_select_content);
    savepath_input_manual.hide();
    savepath_select.show();
  } else {
    ajax_post("get_download_dirs", {sid: sid, site: site}, function (ret) {
      if (ret.code === 0) {
        for (let path of ret.paths) {
          savepath_select_content += `<option value="${path}">${path}</option>`;
        }
        savepath_select_content += `<option value="manual">--手动输入--</option>`;
        savepath_select.empty().append(savepath_select_content);
        savepath_input_manual.hide();
        savepath_select.show();
      }
    }, aync);
  }

}

// 切换手动输入
function check_manual_input_path(select_id, input_id, manual_path = null) {
  let savepath_select = $(`#${select_id}`);
  let savepath_input_manual = $(`#${input_id}`);
  if (manual_path !== null) {
    savepath_select.val(manual_path)
    if (manual_path !== "" && savepath_select.val() === null) {
      savepath_input_manual.val(manual_path);
      savepath_select.val("manual");
      savepath_select.hide();
      savepath_input_manual.show();
    } else {
      savepath_input_manual.val("");
    }
  } else if (savepath_select.val() === "manual") {
    savepath_select.hide();
    savepath_input_manual.show();
  }
}

// 获取保存路径
function get_savepath(select_id, input_id) {
  let savepath = $(`#${select_id}`).val();
  if (savepath === "manual" || savepath === null) {
    return $(`#${input_id}`).val();
  } else {
    return savepath;
  }
}

// 刷新下载设置
function refresh_downloadsetting_select(obj_id, aync = true, is_default = false) {
  let default_content = (!is_default) ? "站点设置" : "默认";
  ajax_post("get_download_setting", {}, function (ret) {
    if (ret.code === 0) {
      let downloadsetting_select = $(`#${obj_id}`);
      let downloadsetting_select_content = `<option value="" selected>${default_content}</option>`;
      for (let downloadsetting of ret.data) {
        downloadsetting_select_content += `<option value="${downloadsetting.id}">${downloadsetting.name}</option>`;
      }
      downloadsetting_select.empty().append(downloadsetting_select_content);
    }
  }, aync);
}

// 刷新订阅框的下载设置及目录等选项
function refresh_rss_download_setting_dirs() {
  refresh_rsssites_select("rss_sites_group", "rss_sites", false);
  refresh_searchsites_select("rss_search_sites_group", "search_sites", false);
  refresh_filter_select("rss_rule", false);
  refresh_downloadsetting_select("rss_download_setting", false);
  refresh_savepath_select("rss_save_path", false, $("#rss_download_setting").val());
}

// 刷新下载框的下载设置及目录选项
function refresh_search_download_setting_dirs(is_default, site = "") {
  refresh_downloadsetting_select("search_download_setting", false, is_default);
  refresh_savepath_select("search_download_dir", true, $("#search_download_setting").val(), is_default, site);
}

// 显示下载提示框
function show_download_modal(id, name, site = undefined, func = undefined, show_type = undefined) {
  $("#search_download_id").val(id);
  $("#search_download_name").val(name);
  $("#search_download_message").text(`新增下载 ${name}`);
  // 根据下载设置刷新下载目录选项
  // 正在下载页面新增下载添加默认而非站点设置
  if (show_type) {
    refresh_search_download_setting_dirs(true);
    $("#search_download_setting").attr("onchange", "refresh_savepath_select('search_download_dir', true, $(this).val(), true)")
  } else if (site) {
    refresh_search_download_setting_dirs(false, site);
    $("#search_download_setting").attr("onchange", `refresh_savepath_select('search_download_dir', true, $(this).val(), false, "${site}")`)
  } else {
    refresh_search_download_setting_dirs(false);
    $("#search_download_setting").attr("onchange", "refresh_savepath_select('search_download_dir', true, $(this).val(), false)")
  }

  $("#torrent_urls").val("");
  if (show_type === 'torrent') {
    $("#torrent_files").show();
    $("#torrent_urls").hide();
  } else if (show_type === 'url') {
    $("#torrent_urls").show();
    $("#torrent_files").hide();
  } else {
    $("#torrent_files").hide();
    $("#torrent_urls").hide();
  }

  // 绑定下载按钮事件
  if (func) {
    $("#search_download_btn").unbind("click").click(func);
  } else {
    $("#search_download_btn").unbind("click").click(download_link);
  }
  // 清空
  TorrentDropZone.removeAllFiles();

  $("#modal-search-download").modal('show');
}

//点击链接下载
function download_link() {
  const id = $("#search_download_id").val();
  const name = $("#search_download_name").val();
  const dir = get_savepath("search_download_dir", "search_download_dir_manual");
  const setting = $("#search_download_setting").val();
  $("#modal-search-download").modal('hide');
  ajax_post("download", {"id": id, "dir": dir, "setting": setting}, function (ret) {
    if (ret.retcode === 0) {
      show_success_modal(`${name} 添加下载成功！`);
    } else {
      show_fail_modal(`${name} 添加下载失败 ${ret.retmsg}！`);
    }
  });
}

// 显示高级搜索框
function show_search_advanced_modal() {
  refresh_site_options("advanced_search_site", true);
  refresh_filter_select("advanced_search_rule");
  $("#modal-search-advanced").modal("show");
}

// 开始高级搜索
function search_media_advanced() {
  let keyword;
  // 读取数据
  const search_name = $("#advanced_search_name").val();
  if (!search_name) {
    $("#advanced_search_name").addClass("is-invalid");
    return;
  } else {
    $("#advanced_search_name").removeClass("is-invalid");
  }
  const search_type = $("#advanced_search_type").val();
  const search_season = $("#advanced_search_season").val();
  const search_year = $("#advanced_search_year").val();
  const search_site = $("#advanced_search_site").val();
  const search_restype = $("#advanced_search_restype").val();
  const search_pix = $("#advanced_search_pix").val();
  const sp_state = $("#advanced_sp_state").val();
  const search_rule = $("#advanced_search_rule").val();
  // 拼装请求
  if (search_type) {
    keyword = search_type + " " + search_name;
  } else {
    keyword = search_name;
  }
  if (search_year) {
    keyword = keyword + " " + search_year;
  }
  if (search_season) {
    keyword = keyword + " " + search_season;
  }
  const filters = {
    "site": search_site,
    "restype": search_restype,
    "pix": search_pix,
    "sp_state": sp_state,
    "rule": search_rule
  };
  const param = {"search_word": keyword, "filters": filters, "unident": true};
  $("#modal-search-advanced").modal("hide");
  show_refresh_progress(`正在搜索 ${keyword} ...`, "search");
  ajax_post("search", param, function (ret) {
    hide_refresh_process();
    if (ret.code === 0) {
      navmenu(`search?s=${keyword}`);
    } else {
      show_fail_modal(ret.msg, function () {
        $("#modal-search-advanced").modal("show");
      });
    }
  }, true, false);
}

//刷新tooltip
function fresh_tooltip() {
  const tooltipTriggerList = Array.prototype.slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl)
  });
}

//打开路径选择框
function openFileBrowser(el, root, filter, on_folders, on_files, close_on_select) {
  if (on_folders === undefined) on_folders = true;
  if (on_files === undefined) on_files = true;
  if (!filter && !on_files) filter = 'HIDE_FILES_FILTER';
  if (!root.trim()) root = "";
  let p = $(el);
  // Skip is fileTree is already open
  if (p.next().hasClass('fileTree')) return null;
  // create a random id
  const r = Math.floor((Math.random() * 1000) + 1);
  // Add a new span and load fileTree
  p.after("<div id='fileTree" + r + "' class='fileTree card shadow-sm' style='z-index: 99999;'></div>");
  const ft = $('#fileTree' + r);
  ft.fileTree({
        script: 'dirlist',
        root: root,
        filter: filter,
        allowBrowsing: true
      },
      function (file) {
        if (on_files) {
          p.val(file);
          p.trigger('change');
          if (close_on_select) {
            ft.slideUp('fast', function () {
              ft.remove();
            });
          }
        }
      },
      function (folder) {
        if (on_folders) {
          p.val(folder);
          p.trigger('change');
          if (close_on_select) {
            $(ft).slideUp('fast', function () {
              $(ft).remove();
            });
          }
        }
      });
  // Format fileTree according to parent position, height and width
  ft.css({'left': p.position().left, 'top': (p.position().top + p.outerHeight()), 'width': (p.parent().width())});
  // close if click elsewhere
  $(document).mouseup(function (e) {
    if (!ft.is(e.target) && ft.has(e.target).length === 0) {
      ft.slideUp('fast', function () {
        $(ft).remove();
      });
    }
  });
  // close if parent changed
  p.bind("keydown", function () {
    ft.slideUp('fast', function () {
      $(ft).remove();
    });
  });
  // Open fileTree
  ft.slideDown('fast');
}

//初始化目录选择控件
function init_filetree_element() {
  $('.filetree-folders-only').each(function () {
    $(this).attr("onclick", "openFileBrowser(this,$(this).val(),'',true,false);");
  });
  $('.filetree-files-only').each(function () {
    $(this).attr("onclick", "openFileBrowser(this,$(this).val(),'',false,true);");
  });
}

// 名称识别测试
function media_name_test(name, result_div, func, subtitle) {
  if (!name) {
    return;
  }
  ajax_post("name_test", {"name": name, "subtitle": subtitle || ""}, function (ret) {
    if (func) {
      func();
    }
    if (ret.code === 0) {
      media_name_test_ui(ret.data, result_div);
    }
  });
}

// 处理识别结果UI
function media_name_test_ui(data, result_div) {
  // 希望chips按此数组的顺序生成..
  $(`#${result_div}`).empty();
  const sort_array = ["rev_string", "ignored_words", "replaced_words", "offset_words",
    "type", "category", "name", "title", "tmdbid", "year", "season_episode", "part",
    "restype", "effect", "pix", "video_codec", "audio_codec", "team", "customization"]
  // 调用组件实例的自定义方法.. 一次性添加chips
  document.querySelector(`#${result_div}`).add_chips_all(sort_array, data);
}

// 显示手动识别转移框
// manual_type: 1-未识别手动识别，2-历史记录手动识别，3-自定义识别
// media_type: 电影，电视剧，动漫
function show_manual_transfer_modal(manual_type, inpath, syncmod, media_type, unknown_id, transferlog_id) {
  // 初始化类型
  if (!syncmod) {
    syncmod = DefaultTransferMode;
  }
  let source = CurrentPageUri;
  $("#rename_source").val(source);
  $("#rename_manual_type").val(manual_type);
  if (manual_type === 3) {
    $('#rename_header').text("自定义识别");
    $('#rename_path_div').hide();
    $('#rename_inpath_div').show();
    $('#rename_outpath_div').show();
    if (inpath) {
      $("#rename_inpath").val(inpath);
    } else {
      $("#rename_inpath").val(DefaultPath);
    }
    $("#rename_outpath").val('');
    $("#rename_syncmod_customize").val(syncmod);
    $("#unknown_id").val("");
    $("#transferlog_id").val("");
  } else {
    $('#rename_header').text("手动识别");
    $('#rename_path_div').show();
    $('#rename_inpath_div').hide();
    $('#rename_outpath_div').hide();
    $("#rename_path").val(inpath);
    $("#rename_syncmod_manual").val(syncmod);
    $("#unknown_id").val(unknown_id);
    $("#transferlog_id").val(transferlog_id);
  }

  // 初始化媒体类型
  if (media_type === "电视剧") {
    $("#rename_type_tv").prop("checked", true);
    $("#rename_type_mov").removeProp("checked");
    $("#rename_type_anime").removeProp("checked");
    $("#rename_season_div").show();
    $("#rename_specify_episode_div").show();
    $("#rename_episode_div").show();
  } else if (media_type === "动漫") {
    $("#rename_type_anime").prop("checked", true);
    $("#rename_type_tv").removeProp("checked");
    $("#rename_type_mov").removeProp("checked");
    $("#rename_season_div").show();
    $("#rename_specify_episode_div").show();
    $("#rename_episode_div").show();
  } else {
    $("#rename_type_mov").prop("checked", true);
    $("#rename_type_tv").removeProp("checked");
    $("#rename_type_anime").removeProp("checked");
    $("#rename_season_div").hide();
    $("#rename_specify_episode_div").hide();
    $("#rename_episode_div").hide();
    $("#rename_season").val("");
  }

  // 清空输入框
  $("#rename_min_filesize").val("");
  $("#rename_specify_episode").val("");
  $("#rename_specify_part").val("");
  $("#rename_episode").val("");
  $("#rename_episode_details").val("");
  $("#rename_episode_offset").val("");
  $("#rename_season").val("");
  $("#rename_tmdb").val("");

  // 显示窗口
  $("#modal-media-identification").modal("show");

}

// 重新识别
function re_identification(flag, ids) {
  ajax_post("re_identification", {"flag": flag, "ids": ids}, function (ret) {
    if (ret.retcode == 0) {
      navmenu(flag);
    } else {
      show_fail_modal(`重新识别失败：${ret.retmsg}！`);
    }
  });
}

// 选择手动转移类型
function switch_rename_type(obj) {
  if (obj.value === 'MOV') {
    $("#rename_season_div").hide();
    $("#rename_specify_episode_div").hide();
    $("#rename_episode_div").hide();
    $("#rename_season").val('');
  } else {
    $("#rename_season_div").show();
    $("#rename_specify_episode_div").show();
    $("#rename_episode_div").show();
  }
}

// 执行手动识别转移
function manual_media_transfer() {
  let syncmod;
  const source = $("#rename_source").val();
  const manual_type = $("#rename_manual_type").val();
  const type = $('input:radio[name=rename_type]:checked').val();
  const path = $("#rename_path").val();
  const inpath = $("#rename_inpath").val();
  const outpath = $("#rename_outpath").val();
  if (manual_type == '3') {
    syncmod = $("#rename_syncmod_customize").val();
  } else {
    syncmod = $("#rename_syncmod_manual").val();
  }
  const tmdb = $("#rename_tmdb").val();
  const season = $("#rename_season").val();
  const specify_episode = $("#rename_specify_episode").val();
  const specify_episode_part = $("#rename_specify_part").val();
  const episode_format = $("#rename_episode").val();
  const episode_details = $("#rename_episode_details").val();
  const episode_offset = $("#rename_episode_offset").val();
  const min_filesize = $("#rename_min_filesize").val();
  const logid = $("#transferlog_id").val();
  const unknown_id = $('#unknown_id').val();

  if (manual_type == '1' && !unknown_id) {
    return;
  }

  if (manual_type == '2' && !logid) {
    return;
  }

  if (manual_type == '3') {
    if (!inpath) {
      $("#rename_inpath").addClass("is-invalid");
      return;
    } else {
      $("#rename_inpath").removeClass("is-invalid");
    }
  } else {
    if (!path) {
      $("#rename_path").addClass("is-invalid");
      return;
    } else {
      $("#rename_path").removeClass("is-invalid");
    }
  }

  if (min_filesize && isNaN(min_filesize)) {
    $("#rename_min_filesize").addClass("is-invalid");
    return;
  } else {
    $("#rename_min_filesize").removeClass("is-invalid");
  }

  if (specify_episode && !/^\d{1,5}(-\d{1,5})?$/.test(specify_episode)) {
    $("#rename_specify_episode").addClass("is-invalid");
    return;
  } else {
    $("#rename_specify_episode").removeClass("is-invalid");
  }

  if (specify_episode_part && !/^PART[0-9ABI]{0,2}$|^CD[0-9]{0,2}$|^DVD[0-9]{0,2}$|^DISK[0-9]{0,2}$|^DISC[0-9]{0,2}$/i.test(specify_episode_part)) {
    $("#rename_specify_part").addClass("is-invalid");
    return;
  } else {
    $("#rename_specify_part").removeClass("is-invalid");
  }

  if (episode_details && !/^\d{1,5},\d{1,5}$/.test(episode_details)) {
    $("#rename_episode_details").addClass("is-invalid");
    return;
  } else {
    $("#rename_episode_details").removeClass("is-invalid");
  }

  if (episode_offset && !/^-?\d{1,5}$/.test(episode_offset)) {
    $("#rename_episode_offset").addClass("is-invalid");
    return;
  } else {
    $("#rename_episode_offset").removeClass("is-invalid");
  }

  // 开始处理
  const data = {
    "inpath": inpath,
    "outpath": outpath,
    "syncmod": syncmod,
    "type": type,
    "tmdb": tmdb,
    "season": season,
    "episode_format": episode_format,
    "episode_details": spaceTrim(specify_episode) === '' ? episode_details : specify_episode,
    "episode_part": specify_episode_part,
    "episode_offset": episode_offset,
    "min_filesize": min_filesize,
    "unknown_id": unknown_id,
    "path": path,
    "logid": logid
  };
  $('#modal-media-identification').modal('hide');
  show_refresh_progress("手动转移 " + inpath, "filetransfer");
  let cmd = (manual_type === '3') ? "rename_udf" : "rename"
  ajax_post(cmd, data, function (ret) {
    hide_refresh_process();
    if (ret.retcode === 0) {
      show_success_modal(inpath + "处理成功！", function () {
        navmenu(source);
      });
    } else {
      //处理失败
      show_fail_modal(ret.retmsg, function () {
        $('#modal-media-identification').modal('show');
      });
    }
  });
}

// 查示查询TMDBID的对话框
function show_search_tmdbid_modal(val_obj, modal_id) {
  $("#" + modal_id).modal("hide");
  $("#search_tmdbid_btn").unbind("click").click(function () {
    let tmdbid = $("#search_tmdbid_list input:radio[name=search_tmdbid_check]:checked").val();
    $("#" + val_obj).val(tmdbid);
    $("#search-tmdbid-modal").modal("hide");
    $("#" + modal_id).modal("show");
  });
  $("#search-tmdbid-modal").modal("show");
}

//根据名称查询TMDBID
function search_tmdbid_by_name(keyid, resultid) {
  let name = $("#" + keyid).val();
  if (!name) {
    $("#" + keyid).addClass("is-invalid");
    return;
  } else {
    $("#" + keyid).removeClass("is-invalid");
  }
  $("#" + keyid).prop("disabled", true);
  ajax_post("search_media_infos", {"keyword": name, "searchtype": "tmdb"}, function (ret) {
    $("#" + keyid).prop("disabled", false);
    if (ret.code == 0) {
      let data = ret.result;
      let html = '';
      if (data.length > 0) {
        for (let i = 0; i < data.length; i++) {
          html += `<div class="list-group-item" onclick="$(this).find('input:radio').prop('checked', true);"><div class="row align-items-center">`;
          html += `<div class="col-auto"><input type="radio" name="search_tmdbid_check" value="${data[i].tmdb_id}" class="form-check-input"></div>`;
          html += `<div class="col-auto"><img class="rounded w-5 shadow-sm" src="${data[i].image}" onerror="this.src='../static/img/no-image.png'"></div>`;
          html += `<div class="col text-truncate"><a href="${data[i].link}" target="_blank" class="text-reset d-block">${data[i].title} (${data[i].year})</a><div class="text-muted mt-n1 text-wrap" style="-webkit-line-clamp:3; display: -webkit-box; -webkit-box-orient:vertical; overflow:hidden; text-overflow: ellipsis;">${data[i].overview}</div></div>`;
          html += `</div></div>`;
        }
        $("#" + resultid).html(html);
      } else {
        $("#" + resultid).html('<div class="list-group-item text-center text-muted">未找到相关信息</div>');
      }
    } else {
      $("#" + resultid).html(`<div class="list-group-item text-center text-muted">${ret.msg}</div>`);
    }
  });
}

//WEB页面发送消息
function send_web_message(obj) {
  if (!obj) {
    return
  }
  let text;
  // 如果是jQuery对像
  if (obj instanceof jQuery) {
    text = obj.val();
    obj.val("");
  } else {
    text = obj;
  }
  // 消息交互
  if (!MessageWS) {
    return;
  }
  MessageWS.send(JSON.stringify({"text": text}));
  // 显示自己发送的消息
  $("#system-messages").prepend(`<div class="list-group-item">
      <div class="row align-items-center">
        <div class="col text-truncate text-end">
          <span class="text-wrap">${text}</span>
          <div class="d-block text-muted text-truncate mt-n1 text-wrap text-end">${new Date().format("yyyy-MM-dd hh:mm:ss")}</div>
        </div>
        <div class="col-auto">
          <span class="avatar">
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-user" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
               <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
               <path d="M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0"></path>
               <path d="M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"></path>
            </svg>
          </span>
        </div>
      </div>
    </div>`);
  // 滚动到顶部
  $(".offcanvas-body").animate({scrollTop:0}, 300);
}

// 初始化DropZone
function init_dropzone() {
  TorrentDropZone = new Dropzone("#torrent_files");
  TorrentDropZone.options.acceptedFiles = ".torrent";
}
