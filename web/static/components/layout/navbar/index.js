import { LayoutNavbarButton } from "./button.js"; export { LayoutNavbarButton };
import { html, nothing, unsafeHTML } from "../../utility/lit-core.min.js";
import {CustomElement, Golbal} from "../../utility/utility.js";

export class LayoutNavbar extends CustomElement {
  static properties = {
    navbar_list: {type: Array },
    layout_gopage: { attribute: "layout-gopage" },
    layout_appversion: { attribute: "layout-appversion"},
    layout_userlevel: { attribute: "layout-userlevel"},
    layout_useradmin: { attribute: "layout-useradmin"},
    _active_name: { state: true},
    _update_appversion: { state: true },
    _update_url: { state: true },
    _is_update: { state: true },
  };

  constructor() {
    super();
    this.navbar_list = [];
    this.layout_gopage = "";
    this.layout_appversion = "v3.0.0";
    this._active_name = "";
    this._update_appversion = "";
    this._update_url = "https://github.com/NAStool/nas-tools";
    this._is_update = false;
    this.classList.add("navbar","navbar-vertical","navbar-expand-lg","lit-navbar-fixed","lit-navbar","lit-navbar-hide-scrollbar");

    // 加载菜单
    Golbal.get_cache_or_ajax("get_user_menus", "usermenus", {},
      (ret) => {
        if (ret.code === 0) {
          this.navbar_list = ret.menus;
          this._init_page();
        }
      }
    );
  }

  _init_page() {
    // 加载页面
    if (this.layout_gopage) {
      navmenu(this.layout_gopage);
    } else if (window.history.state?.page) {
      window_history_refresh();
    } else {
      // 打开第一个页面
      navmenu(this.navbar_list[0].page ?? this.navbar_list[0].list[0].page);
      // 默认展开探索
      setTimeout(() => { this.show_collapse("ranking") }, 200);
    }

    // 删除logo动画 加点延迟切换体验好
    setTimeout(() => {
      document.querySelector("#logo_animation").remove();
      this.removeAttribute("hidden");
      document.querySelector("#page_content").removeAttribute("hidden");
      document.querySelector("layout-searchbar").removeAttribute("hidden");
    }, 200);

    // 检查更新
    if (this.layout_userlevel > 1 && this.layout_useradmin === "1") {
      this._check_new_version();
    }
  }

  _check_new_version() {
    ajax_post("version", {}, (ret) => {
      if (ret.code === 0) {
        let url = null;
        switch (compareVersion(ret.version, this.layout_appversion)) {
          case 1:
            url = ret.url;
            break;
          case 2:
            url = "https://github.com/NAStool/nas-tools/commits/master"
            break;
        }
        if (url) {
          this._update_url = url;
          this._update_appversion = ret.version;
          this._is_update = true;
        }
      }
    });
  }

  update_active(page) {
    this._active_name = page ?? window.history.state?.page;
    this.show_collapse(this._active_name);
  }

  show_collapse(page) {
    for (const item of this.querySelectorAll("[id^='lit-navbar-collapse-']")) {
      for (const a of item.querySelectorAll("a")) {
        if (page === a.getAttribute("data-lit-page")) {
          item.classList.add("show");
          this.querySelectorAll(`button[data-bs-target='#${item.id}']`)[0].classList.remove("collapsed");
          return;
        }
      }
    }
  }

  render() {
    return html`
      <style>
        
        .navbar {
          min-height: 3rem !important;
        }
        
        .navbar .input-group-flat:focus-within {
          box-shadow: none;
        }
        
        .nav-search-bar {
          padding-top: calc(env(safe-area-inset-top) + var(--safe-area-inset-top)) !important;
          padding-left: env(safe-area-inset-left) !important;
        }
        
        .lit-navar-close {
            margin-top: calc(env(safe-area-inset-top) + var(--safe-area-inset-top)) !important;
        }

        .lit-navbar-fixed {
          position:fixed;
          top:0;
          left:0;
          z-index:1031
        }

        .lit-navbar-canvas {
          width:calc(var(--tblr-offcanvas-width) - 120px)!important;
        }

        .theme-light .lit-navbar-canvas {
          background-color: rgb(231, 235, 239);
        }

        .lit-navar-close {
          position:fixed;
          top:0;
          left:calc(var(--tblr-offcanvas-width) - 120px);
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

        .theme-light .lit-navbar {
          background-color: rgb(231, 235, 239, 0.5);
        }
        
        .lit-navbar-logo {
          height:3rem;
          width:auto;
        }

        .theme-dark .lit-navbar-logo {
          filter: invert(1) grayscale(100%) brightness(200%);
        }

        /* 屏蔽lg以下顶栏 */
        @media (max-width: 992px) {
          .lit-navbar {
            max-height:0!important;
            min-height:0!important;
            padding:0!important;
            margin:0!important;
          }
        }

        .theme-dark .lit-navbar-accordion-button {

        }
        .theme-light .lit-navbar-accordion-button {

        }
        .lit-navbar-accordion-button::after {
          
        }

        .lit-navbar-accordion-item, .lit-navbar-accordion-item-active {
          border-radius:0.75rem;
        }

        .theme-dark .lit-navbar-accordion-item:hover {
          background-color: #2a3551ca!important;
        }
        .theme-light .lit-navbar-accordion-item:hover {
          background-color: #fcfafec5!important;
        }

        .theme-dark .lit-navbar-accordion-item-active {
          background-color: #414d6dca!important;
        }
        .theme-light .lit-navbar-accordion-item-active {
          background-color: rgba(123, 178, 233, 0.5)!important;
          color: #000!important;
        }

      </style>
      <div class="container-fluid">
        <div class="offcanvas offcanvas-start d-flex lit-navbar-canvas shadow" tabindex="-1" id="litLayoutNavbar">
          <div class="d-flex flex-row flex-grow-1 lit-navbar-hide-scrollbar">
            <div class="d-flex flex-column flex-grow-1">
              <h1 class="mt-3" style="text-align:center;">
                <img src="../static/img/logo/logo-blue.png" alt="NAStool" class="lit-navbar-logo">
              </h1>
              <div class="accordion px-2 py-2 flex-grow-1">
                ${this.navbar_list.map((item, index) => ( html`
                  ${item.list?.length > 0
                  ? html`
                    <button class="accordion-button lit-navbar-accordion-button collapsed ps-2 pe-1 py-2" style="font-size:1.1rem;" data-bs-toggle="collapse" data-bs-target="#lit-navbar-collapse-${index}" aria-expanded="false">
                      ${item.also??item.name}
                    </button>
                    <div class="accordion-collapse collapse" id="lit-navbar-collapse-${index}">
                      ${item.list.map((drop) => (this._render_page_item(drop, true)))}
                    </div>`
                  : this._render_page_item(item, false)
                  } `
                ))}
              </div>
              <div class="d-flex align-items-end">
                ${this.layout_useradmin === "1" ? html`
                  ${this.layout_userlevel > 1 ? html`
                  <!-- 升级提示 -->
                  <span class="d-flex flex-grow-1 justify-content-center border rounded-3 m-3 p-2 ${this._is_update ? "bg-yellow" : ""}">
                    <a href=${this._update_url} class="${this._is_update ? "text-yellow-fg" : "text-muted"}" target="_blank" rel="noreferrer">
                      <strong>
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-brand-github" width="24" height="24"
                            viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
                            stroke-linejoin="round">
                          <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                          <path d="M9 19c-4.3 1.4 -4.3 -2.5 -6 -3m12 5v-3.5c0 -1 .1 -1.4 -.5 -2c2.8 -.3 5.5 -1.4 5.5 -6a4.6 4.6 0 0 0 -1.3 -3.2a4.2 4.2 0 0 0 -.1 -3.2s-1.1 -.3 -3.5 1.3a12.3 12.3 0 0 0 -6.2 0c-2.4 -1.6 -3.5 -1.3 -3.5 -1.3a4.2 4.2 0 0 0 -.1 3.2a4.6 4.6 0 0 0 -1.3 3.2c0 4.6 2.7 5.7 5.5 6c-.6 .6 -.6 1.2 -.5 2v3.5"></path>
                        </svg>
                        ${!this._is_update ? this.layout_appversion : html`<del>${this.layout_appversion}</del>`}
                      </strong>
                    </a>
                    ${this._is_update
                    ? html`
                      <svg xmlns="http://www.w3.org/2000/svg" class="cursor-pointer icon icon-tabler icon-tabler-arrow-big-up-lines-filled ms-2 text-red" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"
                        @click=${ (e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          update(this._update_appversion);
                          return false;
                        }}>
                        <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                        <path d="M9 12h-3.586a1 1 0 0 1 -.707 -1.707l6.586 -6.586a1 1 0 0 1 1.414 0l6.586 6.586a1 1 0 0 1 -.707 1.707h-3.586v3h-6v-3z" fill="currentColor"></path>
                        <path d="M9 21h6"></path>
                        <path d="M9 18h6"></path>
                      </svg>`
                    : nothing }
                  </span>
                  ` : html`
                    <!-- 用户认证 -->
                    <button class="btn btn-outline-secondary w-100 m-3 p-2" onclick="show_user_auth_modal()">
                      <strong>
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-user-check" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                           <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                           <path d="M9 7m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0"></path>
                           <path d="M3 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"></path>
                           <path d="M16 11l2 2l4 -4"></path>
                        </svg> 
                        用户认证
                      </strong>
                    </button>
                  ` }
                ` : nothing }
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _render_page_item(item, child) {
    return html`
    <a class="nav-link lit-navbar-accordion-item${this._active_name === item.page ? "-active" : ""} my-1 p-2 ${child ? "ps-3" : "lit-navbar-accordion-button"}" 
      href="javascript:void(0)" data-bs-dismiss="offcanvas" aria-label="Close"
      style="${child ? "font-size:1rem" : "font-size:1.1rem;"}"
      data-lit-page=${item.page}
      @click=${ () => { navmenu(item.page) }}>
      <span class="nav-link-icon" ?hidden=${!child} style="color:var(--tblr-body-color);">
        ${item.icon ? unsafeHTML(item.icon) : nothing}
      </span>
      <span class="nav-link-title">
        ${item.also ?? item.name}
      </span>
    </a>`    
  }

}


window.customElements.define("layout-navbar", LayoutNavbar);