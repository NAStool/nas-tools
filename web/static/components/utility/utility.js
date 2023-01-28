import { LitElement } from "./lit-core.min.js";

export class CustomElement extends LitElement {

  // 兼容前进后退时重载
  connectedCallback() {
    super.connectedCallback();
    this.innerHTML = "";
  }

  // 过滤空字符
  attributeChangedCallback(name, oldValue, newValue) {
    super.attributeChangedCallback(name, oldValue, Golbal.repNull(newValue));
  }

  // 不使用影子dom
  createRenderRoot() {
    return this;
  }

}

export class Golbal {

  // 没有图片时
  static noImage = "../static/img/no-image.png";
  static noImage_person = "../static/img/person.png";

  // 转换传值的空字符情况
  static repNull(value) {
    if (!value || value == "None" || value == "null" || value == "undefined") {
      return "";
    } else {
      return value;
    }
  }

  // 是否触摸屏设备
  static is_touch_device() {
    return "ontouchstart" in window;
  }

  static convert_mediaid(tmdbid) {
    if (typeof(tmdbid) === "number") {
      tmdbid = tmdbid + "";
    }
    return tmdbid
  }

  // 订阅按钮被点击时
  static lit_love_click(title, year, page_type, tmdb_id, fav, remove_func, add_func) {
    if (fav == "1"){
      show_ask_modal("是否确定将 " + title + " 从订阅中移除？", function () {
        hide_ask_modal();
        remove_rss_media(title, year, page_type, "", "", tmdb_id, remove_func);
      });
    } else {
      show_ask_modal("是否确定订阅： " + title + "？", function () {
        hide_ask_modal();
        const mediaid = Golbal.convert_mediaid(tmdb_id);
        if (page_type == "MOV") {
          add_rss_media(title, year, page_type, mediaid, "", "", add_func);
        } else {
          ajax_post("get_tvseason_list", {tmdbid: mediaid, title: title}, function (ret) {
            if (ret.seasons.length === 1) {
              add_rss_media(title, year, "TV", mediaid, "", ret.seasons[0].num, add_func);
            } else if (ret.seasons.length > 1) {
              show_rss_seasons_modal(title, year, "TV", mediaid, ret.seasons, add_func);
            } else {
              show_fail_modal(title + " 添加RSS订阅失败：未查询到季信息！");
            }
          });
        }
      });
    }
  }

  // 保存额外的页面数据
  static save_page_data(name, value) {
    const extra = window.history.state?.extra ?? {};
    extra[name] = value;
    window_history(false, extra);
  }

  // 获取额外的页面数据
  static get_page_data(name) {
    return window.history.state?.extra ? window.history.state.extra[name] : undefined;
  }
  
  // 判断直接获取缓存或ajax_post
  static get_cache_or_ajax(api, name, data, func) {
    const ret = Golbal.get_page_data(api + name);
    //console.log("读取:", api + name, ret);
    if (ret) {
      func(ret);
    } else {
      const page = window.history.state?.page;
      ajax_post(api, data, (ret) => {
        // 页面已经变化, 丢弃该请求
        if (page !== window.history.state?.page) {
          //console.log("丢弃:", api + name, ret);
          return
        }
        Golbal.save_page_data(api + name, ret);
        //console.log("缓存:", api + name, ret);
        func(ret)
      });
    }
  }

  // 共用的fav数据更改时刷新缓存
  static update_fav_data(api, name, func=undefined) {
    const key = api + name;
    let extra = Golbal.get_page_data(key);
    if (extra && func) {
      extra = func(extra);
      Golbal.save_page_data(key, extra);
      //console.log("更新fav", extra);
    }
  }


}