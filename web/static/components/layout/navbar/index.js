import { LayoutNavbarButton } from "./button.js"; export { LayoutNavbarButton };

import { html, nothing } from "../../utility/lit-core.min.js";
import { CustomElement } from "../../utility/utility.js";

// name: 服务原名
// page: 导航路径
// icon: 项目图标
// also: 显示别名 (可选)
const navbar_list = [
  {
    name: "我的媒体库",
    page: "index",
    icon: html`
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-home" width="24" height="24"
          viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
          stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
        <polyline points="5 12 3 12 12 3 21 12 19 12"></polyline>
        <path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7"></path>
        <path d="M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6"></path>
      </svg>
    `,
  },
  {
    name: "推荐",
    icon: html`
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-star" width="24" height="24"
          viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
          stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
        <path d="M12 17.75l-6.172 3.245l1.179 -6.873l-5 -4.867l6.9 -1l3.086 -6.253l3.086 6.253l6.9 1l-5 4.867l1.179 6.873z"></path>
      </svg>
    `,
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
    icon: html`
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-search" width="24" height="24"
          viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
          stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
        <circle cx="10" cy="10" r="7"></circle>
        <line x1="21" y1="21" x2="15" y2="15"></line>
      </svg>
    `,
  },
  {
    name: "站点管理",
    icon: html`
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-server-2" width="24" height="24"
          viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
          stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
        <rect x="3" y="4" width="18" height="8" rx="3"></rect>
        <rect x="3" y="12" width="18" height="8" rx="3"></rect>
        <line x1="7" y1="8" x2="7" y2="8.01"></line>
        <line x1="7" y1="16" x2="7" y2="16.01"></line>
        <path d="M11 8h6"></path>
        <path d="M11 16h6"></path>
      </svg>
    `,
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
    icon: html`
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-checkbox" width="24" height="24"
          viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
          stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
        <polyline points="9 11 12 14 20 6"></polyline>
        <path d="M20 12v6a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2v-12a2 2 0 0 1 2 -2h9"></path>
      </svg>
    `,
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
    icon: html`
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-download" width="24" height="24"
          viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
          stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
        <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"></path>
        <polyline points="7 11 12 16 17 11"></polyline>
        <line x1="12" y1="4" x2="12" y2="16"></line>
      </svg>
    `,
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
    icon: html`
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-movie" width="24" height="24"
          viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
          stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
        <rect x="4" y="4" width="16" height="16" rx="2"></rect>
        <line x1="8" y1="4" x2="8" y2="20"></line>
        <line x1="16" y1="4" x2="16" y2="20"></line>
        <line x1="4" y1="8" x2="8" y2="8"></line>
        <line x1="4" y1="16" x2="8" y2="16"></line>
        <line x1="4" y1="12" x2="20" y2="12"></line>
        <line x1="16" y1="8" x2="20" y2="8"></line>
        <line x1="16" y1="16" x2="20" y2="16"></line>
      </svg>
    `,
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
    icon: html`
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-layout-2" width="24" height="24"
          viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
          stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
        <rect x="4" y="4" width="6" height="5" rx="2"></rect>
        <rect x="4" y="13" width="6" height="7" rx="2"></rect>
        <rect x="14" y="4" width="6" height="7" rx="2"></rect>
        <rect x="14" y="15" width="6" height="5" rx="2"></rect>
      </svg>
    `,
  },
  {
    name: "系统设置",
    icon: html`
      <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-settings" width="24" height="24"
          viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
          stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
        <path d="M10.325 4.317c.426 -1.756 2.924 -1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543 -.94 3.31 .826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756 .426 1.756 2.924 0 3.35a1.724 1.724 0 0 0 -1.066 2.573c.94 1.543 -.826 3.31 -2.37 2.37a1.724 1.724 0 0 0 -2.572 1.065c-.426 1.756 -2.924 1.756 -3.35 0a1.724 1.724 0 0 0 -2.573 -1.066c-1.543 .94 -3.31 -.826 -2.37 -2.37a1.724 1.724 0 0 0 -1.065 -2.572c-1.756 -.426 -1.756 -2.924 0 -3.35a1.724 1.724 0 0 0 1.066 -2.573c-.94 -1.543 .826 -3.31 2.37 -2.37c1 .608 2.296 .07 2.572 -1.065z"></path>
        <circle cx="12" cy="12" r="3"></circle>
      </svg>
    `,
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

export class LayoutNavbar extends CustomElement {
  static properties = {
    layout_userpris: { attribute: "layout-userpris", type: Array },
    _is_update: { state: true },
  };

  constructor() {
    super();
    this.layout_userpris = navbar_list.map((item) => (item.name));
    this._is_update = false;
    this.classList.add("navbar","navbar-vertical","navbar-expand-lg","navbar-dark","lit-navbar-fixed","lit-navbar","lit-navbar-hide-scrollbar");
  }

  firstUpdated() {
    
  }

  render() {
    return html`
      <style>
        .lit-navbar-fixed {
          position:fixed;
          top:0;
          left:0;
          z-index:1031
        }

        .lit-navbar-canvas {
          width:calc(var(--tblr-offcanvas-width) - 80px)!important;
          border-right: var(--tblr-offcanvas-border-width) solid #243049!important;
        }

        .lit-navar-close {
          position:fixed;
          top:0;
          left:calc(var(--tblr-offcanvas-width) - 80px);
          z-index:var(--tblr-offcanvas-zindex);
          width: 80px;
        }

        .lit-navbar-hide-scrollbar {
          overflow-y: scroll!important;
          overscroll-behavior-y: contain!important;
          scrollbar-width: none!important;
          -ms-overflow-style: none!important;
        }

        .lit-navbar-hide-scrollbar::-webkit-scrollbar {
          display: none;
        }

        .lit-navbar-nav {
          max-height:none!important;
        }

        /* 屏蔽lg以下顶栏 */
        @media (max-width: 992px) {
          .lit-navbar {
            max-height:0px!important;
            min-height:0px!important;
            padding:0px!important;
            margin:0px!important;
          }
        }
        
      </style>
      <div class="container-fluid">
        <div class="offcanvas offcanvas-start d-flex bg-dark lit-navbar-canvas" tabindex="-1" id="litLayoutNavbar">
          <div class="lit-navar-close d-lg-none">
            <button type="button" class="btn btn-lg btn-ghost-light" data-bs-dismiss="offcanvas" aria-label="Close">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-x m-0" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                <path d="M18 6l-12 12"></path>
                <path d="M6 6l12 12"></path>
              </svg>
            </button>
          </div>
          <div class="d-flex flex-row flex-grow-1 lit-navbar-hide-scrollbar">
            <div class="d-flex flex-column flex-grow-1">
              <h1 class="mt-3" style="text-align:center;filter:brightness(0) invert(1)">
                <a href="javascript:ScrollToTop()">
                  <img src="../static/img/logo-blue.png" alt="NAStool" style="height:3rem;width:auto;">
                </a>
              </h1>
              <div class="navbar-collapse py-2" id="navbar-menu">
                <ul class="navbar-nav lit-navbar-nav">
                  ${navbar_list.map((item) => ( html`
                    ${this.layout_userpris.includes(item.name)
                    ? html`
                      <li class="nav-item">
                        ${item.list?.length > 0
                        ? html`
                          <a class="nav-link dropdown-toggle" href="javascript:void(0)" data-bs-toggle="dropdown" data-bs-auto-close="false"
                            role="button" aria-expanded="false">
                            <span class="nav-link-icon">
                              ${item.icon ?? nothing}
                            </span>
                            <span class="nav-link-title">
                              ${item.also ?? item.name}
                            </span>
                          </a>
                          <div class="dropdown-menu">
                            ${item.list.map((drop) => (
                            html`
                              <a class="dropdown-item" href="javascript:void(0)" data-bs-dismiss="offcanvas" aria-label="Close"
                                @click=${ () => { navmenu(drop.page) }}>
                                ${drop.also ?? drop.name}
                              </a>`
                            ))}
                          </div>`
                        : html`
                          <a class="nav-link" href="javascript:void(0)" data-bs-dismiss="offcanvas" aria-label="Close"
                            @click=${ () => { navmenu(item.page) }}>
                            <span class="nav-link-icon">
                              ${item.icon ?? nothing}
                            </span>
                            <span class="nav-link-title">
                              ${item.also ?? item.name}
                            </span>
                          </a>`
                        }
                      </li>`
                    : nothing }
                  `))}
                </ul>
              </div>
              <div class="align-items-end align-self-center nav-item btn-list pb-3">
                <a href="https://github.com/jxxghp/nas-tools" class="btn ${this._is_update ? "btn-yellow text-yellow-fg" : "btn-dark text-muted"}" target="_blank" rel="noreferrer">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-brand-github" width="24" height="24"
                      viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
                      stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                    <path d="M9 19c-4.3 1.4 -4.3 -2.5 -6 -3m12 5v-3.5c0 -1 .1 -1.4 -.5 -2c2.8 -.3 5.5 -1.4 5.5 -6a4.6 4.6 0 0 0 -1.3 -3.2a4.2 4.2 0 0 0 -.1 -3.2s-1.1 -.3 -3.5 1.3a12.3 12.3 0 0 0 -6.2 0c-2.4 -1.6 -3.5 -1.3 -3.5 -1.3a4.2 4.2 0 0 0 -.1 3.2a4.6 4.6 0 0 0 -1.3 3.2c0 4.6 2.7 5.7 5.5 6c-.6 .6 -.6 1.2 -.5 2v3.5"></path>
                  </svg>
                  V2.8.2 e704d14
                  ${this._is_update
                  ? html`
                    <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-arrow-big-up-lines-filled ms-2" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                      <path d="M9 12h-3.586a1 1 0 0 1 -.707 -1.707l6.586 -6.586a1 1 0 0 1 1.414 0l6.586 6.586a1 1 0 0 1 -.707 1.707h-3.586v3h-6v-3z" fill="currentColor"></path>
                      <path d="M9 21h6"></path>
                      <path d="M9 18h6"></path>
                    </svg>`
                  : nothing }
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

}


window.customElements.define("layout-navbar", LayoutNavbar);