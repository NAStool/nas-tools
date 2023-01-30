import { html } from "../../utility/lit-core.min.js";
import { CustomElement, Golbal } from "../../utility/utility.js";


const navbar_list = [
  {
    name: "我的媒体库",
    page: "index",
  },
  {
    name: "流行趋势",
    list: [
      {
        name: "电影",
        page: "discovery_movie",
      },
      {
        name: "电视剧",
        page: "discovery_tv",
      },
      {
        name: "BANGUMI",
        page: "discovery_bangumi",
      },
    ],
  },
  {
    name: "资源搜索",
    page: "search",
  },
  {
    name: "站点管理",
    list: [
      {
        name: "站点维护",
        page: "site",
      },
      {
        name: "数据统计",
        page: "statistics",
      },
      {
        name: "刷流任务",
        page: "brushtask",
      },
      {
        name: "站点资源",
        page: "sitelist",
      },
    ],
  },
  {
    name: "订阅管理",
    list: [
      {
        name: "电影订阅",
        page: "movie_rss",
      },
      {
        name: "电视剧订阅",
        page: "tv_rss",
      },
      {
        name: "自定义订阅",
        page: "user_rss",
      },
      {
        name: "订阅日历",
        page: "rss_calendar",
      },
    ],
  },
  {
    name: "下载管理",
    list: [
      {
        name: "正在下载",
        page: "downloading",
      },
      {
        name: "近期下载",
        page: "downloaded",
      },
      {
        name: "自动删种",
        page: "torrent_remove",
      },
    ],
  },
  {
    name: "媒体整理",
    list: [
      {
        name: "文件管理",
        page: "mediafile",
      },
      {
        name: "手动识别",
        page: "unidentification",
      },
      {
        name: "历史记录",
        page: "history",
      },
      {
        name: "TMDB缓存",
        page: "tmdbcache",
      },
    ],
  },
  {
    name: "服务",
    page: "search",
  },
  {
    name: "系统设置",
    list: [
      {
        name: "基础设置",
        page: "basic",
      },
      {
        name: "用户管理",
        page: "users",
      },
      {
        name: "媒体库",
        page: "library",
      },
      {
        name: "目录同步",
        page: "directorysync",
      },
      {
        name: "消息通知",
        page: "notification",
      },
      {
        name: "过滤规则",
        page: "filterrule",
      },
      {
        name: "自定义识别词",
        page: "customwords",
      },
      {
        name: "索引器",
        page: "indexer",
      },
      {
        name: "下载器",
        page: "downloader",
      },
      {
        name: "媒体服务器",
        page: "mediaserver",
      },
      {
        name: "字幕",
        page: "subtitle",
      },
      {
        name: "豆瓣",
        page: "douban",
      },
    ],
  },
];

class LayoutNavbar extends CustomElement {
  static properties = {
    
  };

  constructor() {
    super();
  }

  firstUpdated() {
    
  }

  render() {
    return html`
      <aside class="navbar navbar-vertical navbar-expand-lg navbar-dark sticky-top">
        
      </aside>
    `;
  }

}


window.customElements.define("layout-navbar", LayoutNavbar);