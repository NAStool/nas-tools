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
    this._is_expand = false;
    this.classList.add("navbar","navbar-vertical","navbar-expand-lg","lit-navbar-fixed","lit-navbar","lit-navbar-hide-scrollbar");
    // 加载菜单
    Golbal.get_cache_or_ajax("get_user_menus", "usermenus", {},
      (ret) => {
        if (ret.code === 0) {
          this.navbar_list = ret.menus;
        }
      },false
    );
  }

  firstUpdated() {
    // 初始化页面
    this._init_page();
  }

  _init_page() {
    // 加载页面
    if (this.layout_gopage) {
      navmenu(this.layout_gopage);
    } else if (window.history.state?.page) {
      window_history_refresh();
    } else {
      // 打开地址链锚点页面
      let page = this._get_page_from_url();
      if (page) {
        navmenu(page);
      } else {
        // 打开第一个页面
        const page = this.navbar_list[0].page ?? this.navbar_list[0].list[0].page
        this._add_page_to_url(page);
        navmenu(page);
      }
      // 默认展开探索
      if (!this._is_expand) {
        this.show_collapse("ranking");
      }
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

  _get_page_from_url() {
    const pages = window.location.href.split('#');
    if (pages.length > 1) {
      return pages[pages.length - 1]
    }

  }

  _add_page_to_url(page){
    if (window.location.href.indexOf("?") > 0) {
      window.location.href = `${window.location.href.split('?')[0]}#${page}`;
    }else {
      window.location.href = `${window.location.href.split('#')[0]}#${page}`;
    }
  }

  update_active(page) {
    this._active_name = page ?? window.history.state?.page;
    this.show_collapse(this._active_name);
  }

  show_collapse(page) {
    for (const item of this.querySelectorAll("div[id^='lit-navbar-collapse-']")) {
      for (const a of item.querySelectorAll("a")) {
        if (page === a.getAttribute("data-lit-page")) {
          item.classList.add("show");
          this.querySelectorAll(`button[data-bs-target='#${item.id}']`)[0].classList.remove("collapsed");
          this._is_expand = true;
          return;
        }
      }
    }
  }

  render() {
    return html`
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
      href="#${item.page}" data-bs-dismiss="offcanvas" aria-label="Close"
      style="${child ? "font-size:1rem" : "font-size:1.1rem;"}"
      data-lit-page=${item.page}
      @click=${ () => { 
        this._add_page_to_url(item.page);
        navmenu(item.page);
      }}>
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