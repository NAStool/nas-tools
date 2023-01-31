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
  };

  constructor() {
    super();
    this.layout_systemflag = "Docker";
    this.layout_username = "admin";
    this.layout_userpris = ["系统设置"];
    this.layout_search_source = "tmdb";
    this._search_source = "tmdb";
    this.classList.add("navbar", "fixed-top");
  }

  firstUpdated() {
    this._search_source = localStorage.getItem("SearchSource") ?? this.layout_search_source;
  }

  get input() {
    return this.querySelector(".home_search_bar") ?? null;
  }

  render() {
    return html`
      <div class="container-fluid">
        <div class="d-flex flex-row flex-grow-1 align-items-center">
          <!-- 导航展开按钮 -->
          <layout-navbar-button></layout-navbar-button>
          <!-- 搜索栏 -->
          <div class="input-group input-group-flat mx-2">
            <span class="input-group-text form-control-rounded">
              <a href="#" class="link-secondary" data-bs-toggle="tooltip" title="切换搜索源（豆瓣/TMDB）" aria-label="切换搜索源（豆瓣/TMDB）" data-bs-original-title="切换搜索源（豆瓣/TMDB）"
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
              <a href="javascript:show_search_advanced_modal()" class="link-secondary" data-bs-toggle="tooltip" title="高级搜索" aria-label="高级搜索" data-bs-original-title="高级搜索">
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
          <div class="nav-item dropdown">
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
                <a class="dropdown-item hide-theme-dark" href="?theme=dark" role="button">暗黑风格</a>
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