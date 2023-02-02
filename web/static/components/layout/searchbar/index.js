import { html, nothing } from "../../utility/lit-core.min.js";
import { CustomElement } from "../../utility/utility.js";

const search_source_icon = {
  tmdb: html`
    <!-- http://tabler-icons.io/i/square-letter-t -->
    <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-square-letter-t text-blue" width="24" height="24"
       viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
       stroke-linejoin="round">
      <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
      <path d="M4 4m0 2a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2z"></path>
      <path d="M10 8h4"></path>
      <path d="M12 8v8"></path>
    </svg>`,
  douban: html`
    <!-- http://tabler-icons.io/i/circle-letter-d -->
    <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-circle-letter-d text-green" width="24" height="24"
        viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
        stroke-linejoin="round">
      <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
      <path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"></path>
      <path d="M10 8v8h2a2 2 0 0 0 2 -2v-4a2 2 0 0 0 -2 -2h-2z"></path>
    </svg>
  `
}

export class LayoutSearchbar extends CustomElement {
  static properties = {
    layout_systemflag: { attribute: "layout-systemflag" },
    layout_username: { attribute: "layout-username" },
    layout_search_source: { attribute: "layout-search-source" },
    layout_userpris: { attribute: "layout-userpris", type: Array },
    _search_source: { state: true },
    _chang_color: { state: true },
  };

  constructor() {
    super();
    this.layout_systemflag = "Docker";
    this.layout_username = "admin";
    this.layout_userpris = ["系统设置"];
    this.layout_search_source = "tmdb";
    this._search_source = "tmdb";
    this._chang_color = false;
    this.classList.add("navbar", "fixed-top", "lit-searchbar");
  }

  firstUpdated() {
    this._search_source = localStorage.getItem("SearchSource") ?? this.layout_search_source;
    // 当前屏幕类型
    let screen_lg = document.documentElement.clientWidth || document.body.clientWidth >= 992;
    // 当前状态：是否模糊
    let blur = false;
    let blur_filter = "backdrop-filter: blur(10px);-webkit-backdrop-filter:blur(10px);";
    let bg_black = "29,39,59";
    let bg_white = "200,200,200";
    // 当前状态：是否黑色
    let dark = localStorage.getItem("tablerTheme") === "dark";
    const page_wrapper = document.querySelector(".page-wrapper");

    const _change_blur = () => {
      // 滚动发生时改变模糊状态
      if (!blur && page_wrapper.scrollTop >= 5) {
        // 模糊状态
        blur = true;
        // 背景色要根据是否黑色决定
        const bg_color = dark ? `rgba(${bg_black},0.8)` : `rgba(${bg_white},0.8)`
        this.setAttribute("style",`background-color: ${bg_color} !important; ${blur_filter}`);
      } else if (blur && page_wrapper.scrollTop < 5) {
        // 非模糊状态
        blur = false
        if (!dark) {
          this.removeAttribute("style");
        } else {
          if (screen_lg) {
            this.removeAttribute("style");
          } else {
            this.setAttribute("style",`background-color: rgba(${bg_black},1)!important; ${blur_filter}`);
          }
        }
      }
    };
    page_wrapper.addEventListener("scroll", _change_blur);

    // 修改顶栏颜色
    const _changeColor = () => {
      // 调整窗口大小时改变背景颜色
      const window_width = document.documentElement.clientWidth || document.body.clientWidth;
      // 当前非模糊状态时不透明，否则透明
      const opacity = blur ? 0.8 : 1;
      if (window_width < 992 && !dark) {
        // lg以下
        screen_lg = false;
        this.classList.add("theme-dark");
        // 强制为dark
        dark = true;
        this._chang_color = true;
        this.setAttribute("style",`background-color: rgba(${bg_black},${opacity})!important; ${blur_filter}`);
      } else if (window_width >= 992 && dark) {
        // lg及以上
        screen_lg = true;
        this.classList.remove("theme-dark");
        this._chang_color = false;
        // 是否dark由主题决定
        dark = localStorage.getItem("tablerTheme") === "dark";
        if (!blur) {
          this.removeAttribute("style");
        } else {
          if (dark) {
            this.setAttribute("style",`background-color: rgba(${bg_black},0.8)!important; ${blur_filter}`);
          } else {
            this.setAttribute("style",`background-color: rgba(${bg_white},0.8)!important; ${blur_filter}`);
          }
        }
      }
    }
    _changeColor();
    // 窗口大小发生改变时
    this._changeColor_resize = () => { _changeColor() }; // 防止无法卸载事件
    window.addEventListener("resize", this._changeColor_resize);
  }

  // 卸载事件
  disconnectedCallback() {
    window.removeEventListener("resize", this._changeColor_resize);
    super.disconnectedCallback();
  }

  get input() {
    return this.querySelector(".home_search_bar") ?? null;
  }

  render() {
    return html`
      <style>
        .lit-searchbar {
          background-color: rgba(0,0,0,0)!important;
          border-right: none!important;
          box-shadow: none!important;
        }
      </style>
      <div class="container-fluid nav-search-bar">
        <div class="d-flex flex-row flex-grow-1 align-items-center py-1">
          <!-- 导航展开按钮 -->
          <layout-navbar-button></layout-navbar-button>
          <!-- 搜索栏 -->
          <div class="input-group input-group-flat mx-2">
            <span class="input-group-text form-control-rounded">
              <a href="#" class="link-secondary"
                @click=${ () => {
                  this._search_source = this._search_source === "tmdb" ? "douban" : "tmdb";
                  localStorage.setItem("SearchSource", this._search_source);
                }}>
                ${search_source_icon[this._search_source]}
              </a>
            </span>
            <input type="text" class="home_search_bar form-control form-control-rounded" placeholder="搜索电影、电视剧" autocomplete="new-password"
              @keypress=${ (e) => {
                if(e.which === 13 && this.input.value){
                  navmenu("recommend?type=SEARCH&title=搜索结果&subtitle=" + this.input.value + "&keyword=" + this.input.value + "&source=" + this._search_source);
                }
              }}>
            <span class="input-group-text form-control-rounded">
              <a href="javascript:show_search_advanced_modal()" class="link-secondary">
                <!-- http://tabler-icons.io/i/adjustments -->
                <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2"
                    stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                  <circle cx="6" cy="10" r="2"></circle>
                  <line x1="6" y1="4" x2="6" y2="8"></line>
                  <line x1="6" y1="12" x2="6" y2="20"></line>
                  <circle cx="12" cy="16" r="2"></circle>
                  <line x1="12" y1="4" x2="12" y2="14"></line>
                  <line x1="12" y1="18" x2="12" y2="20"></line>
                  <circle cx="18" cy="7" r="2"></circle>
                  <line x1="18" y1="4" x2="18" y2="5"></line>
                  <line x1="18" y1="9" x2="18" y2="20"></line>
                </svg>
              </a>
            </span>
          </div>
          <!-- 头像 -->
          <div class="nav-item dropdown me-3">
              <a href="#" class="nav-link d-flex lh-1 text-reset ms-1 p-0" data-bs-toggle="dropdown">
                <!-- http://tabler-icons.io/i/user -->
                <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-user"
                    width="24" height="24" viewBox="0 0 24 24"
                    stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                  <circle cx="12" cy="7" r="4"></circle>
                  <path d="M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"></path>
                </svg>
              </a>
              <div class="dropdown-menu dropdown-menu-end dropdown-menu-arrow">
                <a class="dropdown-item ${!this._chang_color ? "hide-theme-dark" : ""}" href="?theme=dark" role="button">暗黑风格</a>
                <a class="dropdown-item hide-theme-light" href="?theme=light" role="button">明亮风格</a>
                <div class="dropdown-divider"></div>
                ${this.layout_userpris.includes("系统设置")
                ? html`
                    <a class="dropdown-item" data-bs-toggle="offcanvas" href="#offcanvasEnd" role="button"
                      aria-controls="offcanvasEnd">消息中心</a>
                    <a class="dropdown-item" href="javascript:show_logging_modal()" role="button">实时日志</a>
                    <div class="dropdown-divider"></div>
                    ${["Docker", "Synology"].includes(this.layout_systemflag)
                    ? html`
                      <a href="javascript:restart()" class="dropdown-item">重启</a>
                      <a href="javascript:update()" class="dropdown-item">更新</a>`
                    : nothing }
                  `
                : nothing }
                <a href="javascript:logout()" class="dropdown-item">
                  注销 <span class="text-muted mx-3">${this.layout_username}</span>
                </a>
              </div>
            </div>
          </div>
      </div>
    `;
  }

}


window.customElements.define("layout-searchbar", LayoutSearchbar);