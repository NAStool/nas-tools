import { NormalCardPlaceholder } from "./placeholder.js"; export { NormalCardPlaceholder };

import { html, nothing } from "../utility/lit-core.min.js";
import { CustomElement, Golbal } from "../utility/utility.js";
import { observeState } from "../utility/lit-state.js";
import { cardState } from "./state.js";

export class NormalCard extends observeState(CustomElement) {

  static properties = {
    tmdb_id: { attribute: "card-tmdbid" },
    res_type: { attribute: "card-restype" },
    page_type: { attribute: "card-pagetype" },
    show_sub: { attribute: "card-showsub"},
    title: { attribute: "card-title" },
    fav: { attribute: "card-fav" , reflect: true},
    date: { attribute: "card-date" },
    vote: { attribute: "card-vote" },
    image: { attribute: "card-image" },
    overview: { attribute: "card-overview" },
    year: { attribute: "card-year" },
    site: { attribute: "card-site" },
    weekday: { attribute: "card-weekday" },
    lazy: {},
    _placeholder: { state: true },
    _card_id: { state: true },
  };

  constructor() {
    super();
    this.lazy = "0";
    this._placeholder = true;
    this._card_id = Symbol("normalCard_data_card_id");
  }

  _render_left_up() {
    if (this.weekday ||this.res_type) {
      let color;
      let text;
      if (this.weekday) {
        color = this.fav == "2" ? "bg-green" : "bg-orange";
        text = this.weekday;
      } else {
        color = this.res_type == "电影" ? "bg-green" : "bg-blue";
        text = this.res_type;
      }
      return html`
        <span class="badge badge-pill ${color}" style="position: absolute; top: 10px; left: 10px">
          ${text}
        </span>`;
    } else if (this.fav == "2") {
      return html`
        <div class="badge badge-pill bg-green" style="position:absolute;top:10px;left:10px;padding:0;">
          <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-check" width="24" height="24"
               viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
               stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
            <path d="M5 12l5 5l10 -10"></path>
          </svg>
        </div>`;
    } else {
      return nothing;
    }
  }

  _render_right_up() {
    if (this.vote && this.vote != "0.0" && this.vote != "0") {
      return html`
      <div class="badge badge-pill bg-purple"
           style="position: absolute; top: 10px; right: 10px">
        ${this.vote}
      </div>`;
    } else {
      return nothing;
    }
  }

  _render_bottom() {
    if (this.show_sub == "1") {
      return html`
        <div class="d-flex justify-content-between">
          <a class="text-muted" title="搜索资源" @click=${(e) => { e.stopPropagation() }}
             href='javascript:show_mediainfo_modal("${this.page_type}", "${this.title}", "${this.year}", "${this.tmdb_id}", "", "", true)'>
            <span class="icon-pulse text-white">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-search" width="24" height="24"
                  viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
                  stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                <circle cx="10" cy="10" r="7"></circle>
                <line x1="21" y1="21" x2="15" y2="15"></line>
              </svg>
            </span>
          </a>
          <div class="ms-auto">
            <div class="text-muted" title="加入/取消订阅" style="cursor: pointer" @click=${this._loveClick}>
              <span class="icon-pulse text-white">
                <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-heart ${this.fav == "1" ? "icon-filled text-red" : ""}" width="24" height="24"
                    viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
                    stroke-linejoin="round">
                  <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                  <path d="M19.5 12.572l-7.5 7.428l-7.5 -7.428m0 0a5 5 0 1 1 7.5 -6.566a5 5 0 1 1 7.5 6.572"></path>
                </svg>
              </span>
            </div>
          </div>
        </div>`;
    } else {
      return nothing;
    }
  }

  render() {
    return html`
      <style>
        .lit-person-card-scale:hover {
          transform:scale(1.05, 1.05);
          opacity:1
        }
      </style>
      <div class="card card-sm lit-person-card-scale rounded-4 border-1 shadow-sm"
           style="--tblr-border-opacity: 1;border-color: rgb(128, 128, 128);overflow: hidden;"
           @click=${() => { if (Golbal.is_touch_device()){ cardState.more_id = this._card_id } } }
           @mouseenter=${() => { if (!Golbal.is_touch_device()){ cardState.more_id = this._card_id } } }
           @mouseleave=${() => { if (!Golbal.is_touch_device()){ cardState.more_id = undefined } } }>
        ${this._placeholder ? NormalCardPlaceholder.render_placeholder() : nothing}
        <div ?hidden=${this._placeholder}>
          <div class="ratio" style="--tblr-aspect-ratio: 150%">
            <img class="card-img" alt=""
                 src=${this.lazy == "1" ? "" : this.image ?? Golbal.noImage}
                 @error=${() => { if (this.lazy != "1") {this.image = Golbal.noImage} }}
                 @load=${() => { this._placeholder = false }}/>
          </div>
          ${this._render_left_up()}
          ${this._render_right_up()}
        </div>
        <div ?hidden=${cardState.more_id != this._card_id}
             class="card-img-overlay ms-auto"
             style="background-color: rgba(0, 0, 0, 0.5)"
             @click=${() => { show_mediainfo_modal(this.page_type, this.title, this.year, this.tmdb_id) }}>
          <div style="cursor: pointer">
            ${this.year ? html`<div class="text-white"><strong>${this.site ? this.site : this.year}</strong></div>` : nothing }
            ${this.title
            ? html`
              <h2 class="lh-sm text-white"
                  style="margin-bottom: 5px; -webkit-line-clamp:3; display: -webkit-box; -webkit-box-orient:vertical; overflow:hidden; text-overflow: ellipsis;">
                <strong>${this.title}</strong>
              </h2>`
            : nothing }
            ${this.overview
            ? html`
              <p class="lh-sm text-white"
                 style="margin-bottom: 5px; -webkit-line-clamp:4; display: -webkit-box; -webkit-box-orient:vertical; overflow:hidden; text-overflow: ellipsis;">
                ${this.overview}
              </p>`
            : nothing }
            ${this.date
            ? html`
              <p class="lh-sm text-white"
                style="margin-bottom: 5px; -webkit-line-clamp:4; display: -webkit-box; -webkit-box-orient:vertical; overflow:hidden; text-overflow: ellipsis;">
                <small>${this.date}</small>
              </p>`
            : nothing }
          </div>
          ${this._render_bottom()}
        </div>
      </div>
    `;
  }

  _loveClick(e) {
    e.stopPropagation();
    const self = this;
    if (self.fav == "1"){
      show_ask_modal("是否确定将 " + self.title + " 从订阅中移除？", function () {
        hide_ask_modal();
        remove_rss_media(self.title, self.year, self.page_type, "", "", self.tmdb_id, function () {
          self.fav = "0";
        });
      });
    } else {
      show_ask_modal("是否确定订阅： " + self.title + "？", function () {
        hide_ask_modal();
        function add_red_heart(){
          self.fav = "1";
          window_history();
        }
        let tid;
        let did;
        if (self.tmdb_id && self.tmdb_id.startsWith("DB:")) {
          did = self.tmdb_id.replace("DB:", "");
          tid = "";
        } else if (isNaN(self.tmdb_id)) {
          did = "";
          tid = "";
        } else {
          did = "";
          tid = self.tmdb_id;
        }
        if (!tid || ["hm", "nm", "dbom", "dbnm", "dbhm", "dbtop"].includes(self.page_type)) {
          add_rss_media(self.title, self.year, self.page_type, tid, did, "", "", add_red_heart);
        } else {
          ajax_post("get_tvseason_list", { tmdbid: tid }, function (ret) {
            if (ret.seasons.length === 1) {
              add_rss_media(self.title, self.year, "TV", tid, did, "", "", add_red_heart);
            } else if (ret.seasons.length > 1) {
              show_rss_seasons_modal(self.title, self.year, "TV", tid, did, ret.seasons, add_red_heart);
            } else {
              show_fail_modal(self.title + " 添加RSS订阅失败：未查询到季信息！");
            }
          });
        }
      });
    }
  }

}

window.customElements.define("normal-card", NormalCard);