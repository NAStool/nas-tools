import { html, nothing } from "../utility/lit-core.min.js";
import { CustomElement, Golbal } from "../utility/utility.js";

class PageMediainfo extends CustomElement {
  static properties = {
    // 类型
    media_type: { attribute: "media-type" },
    // TMDBID/DB:豆瓣ID
    tmdbid: { attribute: "media-tmdbid" },
    // 是否订阅/下载
    fav: {},
    // 媒体信息
    media_info: { type: Object },
    // 类似影片
    similar_media: { type: Array },
    // 推荐影片
    recommend_media: { type: Array },
  };

  constructor() {
    super();
    this.media_info = {};
    this.similar_media = [];
    this.recommend_media = [];
    this.fav = undefined;
  }

  firstUpdated() {
    // 媒体信息、演员阵容
    Golbal.get_cache_or_ajax("media_detail", "info", { "type": this.media_type, "tmdbid": this.tmdbid},
      (ret) => {
        if (ret.code === 0) {
          this.media_info = ret.data;
          this.tmdbid = ret.data.tmdbid;
          this.fav = ret.data.fav;
          // 类似
          Golbal.get_cache_or_ajax("get_recommend", "sim", { "type": this.media_type, "subtype": "sim", "tmdbid": ret.data.tmdbid, "page": 1},
            (ret) => {
              if (ret.code === 0) {
                this.similar_media = ret.Items;
              }
            }
          );
          // 推荐
          Golbal.get_cache_or_ajax("get_recommend", "more", { "type": this.media_type, "subtype": "more", "tmdbid": ret.data.tmdbid, "page": 1},
            (ret) => {
              if (ret.code === 0) {
                this.recommend_media = ret.Items;
              }
            }
          );
        } else {
          show_fail_modal("未查询到TMDB媒体信息！");
          window.history.go(-1);
        }
      }
    );
  }

  _render_placeholder(width, height, col, num) {
    return Array(num ?? 1).fill(html`
      <div class="placeholder ${col}"
        style="min-width:${width};min-height:${height};">
      </div>
    `);
  }

  render() {
    return html`
      <style>
        .lit-media-info-background {
          background-image:
            linear-gradient(180deg, rgba(var(--tblr-body-bg-rgb),0.5) 50%, rgba(var(--tblr-body-bg-rgb),1) 100%),
            linear-gradient(90deg, rgba(var(--tblr-body-bg-rgb),0) 90%, rgba(var(--tblr-body-bg-rgb),1) 100%),
            linear-gradient(270deg, rgba(var(--tblr-body-bg-rgb),0) 90%, rgba(var(--tblr-body-bg-rgb),1) 100%);
          box-shadow:0 0 0 2px rgb(var(--tblr-body-bg-rgb));
        }
        .lit-media-info-image {
          width:233px;
          height:350px;
        }

        @media (max-width: 767.98px) {
          .lit-media-info-image {
            width:150px;
            height:225px;
          }
        }
      </style>
      <div class="container-xl placeholder-glow">
        <!-- 渲染媒体信息 -->
        <div class="card rounded-0 lit-media-info-background" style="border:none;height:490px;">
          <custom-img style="border:none;height:490px;"
            div-style="display:inline;"
            img-placeholder="0"
            img-error="0"
            .img_src_list=${this.media_info.background}
            img-class="card-img rounded-0"
            img-style="padding-bottom: 1px; display: block; width: 0px; height: 0px; min-width: 100%; max-width: 100%; min-height: 100%; max-height: 100%; object-fit: cover;">
          </custom-img>
          <div class="card-img-overlay rounded-0 lit-media-info-background">
            <div class="d-md-flex flex-md-row mb-4">
              <custom-img class="d-flex justify-content-center"
                img-class="rounded-4 object-cover lit-media-info-image"
                img-error=${Object.keys(this.media_info).length === 0 ? "0" : "1"}
                img-src=${this.media_info.image}>
              </custom-img>
              <div class="d-flex justify-content-center">
                <div class="d-flex flex-column justify-content-end ms-2 mt-2">
                  ${this.fav == "2"
                  ? html`
                    <div class="align-self-center align-self-md-start me-1 mb-1">
                      <strong class="badge badge-pill bg-green text-white">已下载</strong>
                    </div>`
                  : nothing }
                  <h1 class="align-self-center align-self-md-start display-6">
                    <strong>${this.media_info.title ?? this._render_placeholder("200px")}</strong>
                    <strong class="h1" ?hidden=${!this.media_info.year}>(${this.media_info.year})</strong>
                  </h1>
                  <div class="align-self-center align-self-md-start">
                    <a href="${this.media_info.link}" target="_blank" ?hidden=${!this.media_info.tmdbid}><span class="badge badge-outline text-green">${this.media_info.tmdbid}</span></a>
                    <span class="ms-1" ?hidden=${!this.media_info.runtime}>${this.media_info.runtime}</span>
                    <span ?hidden=${!this.media_info.genres}>| ${this.media_info.genres}</span>
                    ${Object.keys(this.media_info).length === 0 ? this._render_placeholder("205px") : nothing }
                  </div>
                  <div class="align-self-center align-self-md-start me-1 mt-2">
                    ${Object.keys(this.media_info).length !== 0
                    ? html`
                      <span class="btn btn-primary btn-pill me-1"
                        @click=${(e) => {
                          e.stopPropagation();
                          media_search(this.tmdbid + "", this.media_info.title, this.media_type);
                        }}>
                        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-search" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"></path><circle cx="10" cy="10" r="7"></circle><line x1="21" y1="21" x2="15" y2="15"></line></svg>
                        搜索资源
                      </span>
                      ${this.fav == "1"
                      ? html`
                        <span class="btn btn-pill btn-pinterest"
                          @click=${this._loveClick}>
                          <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><line x1="4" y1="7" x2="20" y2="7" /><line x1="10" y1="11" x2="10" y2="17" /><line x1="14" y1="11" x2="14" y2="17" /><path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12" /><path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3" /></svg>
                          删除订阅
                        </span>`
                      : html`
                        <span class="btn btn-pill btn-purple"
                          @click=${this._loveClick}>
                          <svg xmlns="http://www.w3.org/2000/svg" class="icon" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M19.5 12.572l-7.5 7.428l-7.5 -7.428m0 0a5 5 0 1 1 7.5 -6.566a5 5 0 1 1 7.5 6.572" /></svg>
                          添加订阅
                        </span>`
                      }`
                    : html`
                      <span class="me-1">${this._render_placeholder("100px", "30px")}</span>
                      <span class="me-1">${this._render_placeholder("100px", "30px")}</span>
                      `
                    }
                  </div>
                </div>
              </div>
            </div>
            <h1 class="d-flex">
              <strong>${Object.keys(this.media_info).length === 0 ? "加载中.." : "简介"}</strong>
            </h1>
          </div>
        </div>
        <div class="row">
          <div class="col-lg-8">
            <h2 class="text-muted ms-4 me-2">
              <small>${this.media_info.overview ?? this._render_placeholder("200px", "", "col-12", 7)}</small>
            </h2>
            <div class="row mx-2 mt-4">
              ${this.media_info.crews
              ? this.media_info.crews.map((item, index) => ( html`
                <div class="col-12 col-md-6 col-lg-4">
                  <h2 class="">
                    <strong>${Object.keys(item)[0]}</strong>
                  </h2>
                  <p class="text-muted mb-4">
                    <strong>${Object.values(item)[0]}</strong>
                  </p>
                </div>
                `) )
              : nothing }
            </div>
          </div>
          <div class="col-lg-4">
            ${this.media_info.fact
            ? html`
              <div class="ms-3 me-2 mt-1">
                <div class="card rounded-3" style="background: none">
                  ${this.media_info.fact.map((item) => ( html`
                    <div class="card-body p-2">
                      <div class="d-flex justify-content-between">
                        <div class="align-self-center" style="min-width:25%;">
                          <strong>${Object.keys(item)[0]}</strong>
                        </div>
                        <div class="text-break text-muted" style="text-align:end;">
                          ${Object.values(item)[0]}
                        </div>
                      </div>
                    </div>
                    `) ) }
                </div>
              </div>`
            : this._render_placeholder("200px", "200px", "col-12") }
          </div>
        </div>

        <!-- 渲染演员阵容 -->
        ${this.media_info.actors && this.media_info.actors.length
        ? html`
          <custom-slide
            slide-title="演员阵容"
            slide-click='javascript:navmenu("discovery_person?tmdbid=${this.tmdbid}&type=${this.media_type}&title=演员&subtitle=${this.media_info.title}")'
            lazy="person-card"
            .slide_card=${this.media_info.actors.map((item) => ( html`
              <person-card
                lazy=1
                person-id=${item.id}
                person-image=${item.image}
                person-name=${item.name}
                person-role=${item.role}
                @click=${() => {
                  navmenu("recommend?type="+this.media_type+"&subtype=person&personid="+item.id+"&title=参演作品&subtitle="+item.name)
                }}
              ></person-card>`))
            }
          ></custom-slide>`
        : nothing }

        <!-- 渲染类似影片 -->
        ${this.similar_media.length
        ? html`
          <custom-slide
            slide-title="类似"
            slide-click='javascript:navmenu("recommend?type=${this.media_type}&subtype=sim&tmdbid=${this.tmdbid}&title=类似&subtitle=${this.media_info.title}")'
            lazy="normal-card"
            .slide_card=${this.similar_media.map((item, index) => ( html`
              <normal-card
                @fav_change=${(e) => {
                  Golbal.update_fav_data("get_recommend", "sim", (extra) => (
                    extra.Items[index].fav = e.detail.fav, extra
                  ));
                }}
                lazy=1
                card-tmdbid=${item.id}
                card-pagetype=${item.type}
                card-showsub=1
                card-image=${item.image}
                card-fav=${item.fav}
                card-vote=${item.vote}
                card-year=${item.year}
                card-title=${item.title}
                card-overview=${item.overview}
              ></normal-card>`))
            }
          ></custom-slide>`
        : nothing }

        <!-- 渲染推荐影片 -->
        ${this.recommend_media.length
        ? html`
          <custom-slide
            slide-title="推荐"
            slide-click='javascript:navmenu("recommend?type=${this.media_type}&subtype=more&tmdbid=${this.tmdbid}&title=推荐&subtitle=${this.media_info.title}")'
            lazy="normal-card"
            .slide_card=${this.recommend_media.map((item, index) => ( html`
              <normal-card
                @fav_change=${(e) => {
                  Golbal.update_fav_data("get_recommend", "more", (extra) => (
                    extra.Items[index].fav = e.detail.fav, extra
                  ));
                }}
                lazy=1
                card-tmdbid=${item.id}
                card-pagetype=${item.type}
                card-showsub=1
                card-image=${item.image}
                card-fav=${item.fav}
                card-vote=${item.vote}
                card-year=${item.year}
                card-title=${item.title}
                card-overview=${item.overview}
              ></normal-card>`))
            }
          ></custom-slide>`
        : nothing }

      </div>
    `;
  }

  _update_fav_data() {
    Golbal.update_fav_data("media_detail", "info", (extra) => (
      extra.data.fav = this.fav, extra
    ));
  }

  _loveClick(e) {
    e.stopPropagation();
    Golbal.lit_love_click(this.media_info.title, this.media_info.year, this.media_type, this.tmdbid, this.fav,
      () => {
        this.fav = "0";
        this._update_fav_data();
      },
      () => {
        this.fav = "1";
        this._update_fav_data();
      });
  }


}


window.customElements.define("page-mediainfo", PageMediainfo);