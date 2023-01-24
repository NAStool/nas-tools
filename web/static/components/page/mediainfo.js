import { html, nothing } from "../utility/lit-core.min.js";
import { CustomElement } from "../utility/utility.js";

class PageMediainfo extends CustomElement {
  static properties = {
    // 类型
    media_type: { attribute: "media-type" },
    // TMDBID/DB:豆瓣ID
    tmdbid: { attribute: "media-tmdbid" },
    // 媒体信息
    media_info: { type: Object },
    // 演员阵容
    person_list: { type: Array },
    // 类似影片
    similar_media: { type: Array },
    // 推荐影片
    recommend_media: { type: Array },
  };

  constructor() {
    super();
    this.media_info = {};
    this.person_list = [];
    this.similar_media = [];
    this.recommend_media = [];
  }

  firstUpdated() {

    // 媒体信息、演员阵容
    ajax_post("media_detail", { "type": this.media_type, "tmdbid": this.tmdbid},
      (ret) => {
        console.log(ret);
        if (ret.code === 0) {
          this.media_info = ret.data;
          this.person_list = ret.data.actors;
          this.tmdbid = ret.data.tmdbid;
          // 类似
          ajax_post("media_similar", { "type": this.media_type, "tmdbid": ret.data.tmdbid, "page": 1},
            (ret) => {
              if (ret.code === 0) {
                this.similar_media = ret.data;
              }
            }
          );
          // 推荐
          ajax_post("media_recommendations", { "type": this.media_type, "tmdbid": ret.data.tmdbid, "page": 1},
            (ret) => {
              if (ret.code === 0) {
                this.recommend_media = ret.data;
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

  _render_placeholder(width, height, col) {
    return html`
      <div class="placeholder ${col}"
        style="min-width:${width};min-height:${height};">
      </div>
    `;
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
        <div class="card rounded-0" style="border:none;height:490px;">
          <custom-img style="border:none;height:490px;"
            div-style="display:inline;"
            img-placeholder="0"
            img-error="0"
            .img_src_list=${this.media_info.background}
            img-class="card-img rounded-0"
            img-style="display: block; width: 0px; height: 0px; min-width: 100%; max-width: 100%; min-height: 100%; max-height: 100%; object-fit: cover;">
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
                  <h1 class="align-self-center align-self-md-start display-6">
                    <strong>${this.media_info.title ?? this._render_placeholder("200px")}</strong>
                    <strong class="h1" ?hidden=${!this.media_info.year}>(${this.media_info.year})</strong>
                    ${this.media_info.year ? nothing : this._render_placeholder("100px")}
                  </h1>
                  <div class="align-self-center align-self-md-start">
                    <a href="${this.media_info.link}" target="_blank"><span class="badge badge-outline text-warning me-1" ?hidden=${!this.media_info.tmdbid}>${this.media_info.tmdbid}</span></a>
                    <span class="badge badge-outline text-primary me-1" ?hidden=${!this.media_info.runtime}>${this.media_info.runtime}</span>
                    <span class="">${this.media_info.genres ?? this._render_placeholder("250px")}</span>
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
              <small>${this.media_info.overview ?? this._render_placeholder("200px", "250px", "col-12")}</small>
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
            : this._render_placeholder("200px", "300px", "col-12") }
          </div>
        </div>

        <!-- 渲染演员阵容 -->
        ${this.person_list.length
        ? html`
          <custom-slide
            slide-title="演员阵容"
            slide-click='javascript:navmenu("discovery_person?tmdbid=${this.tmdbid}&type=${this.media_type}&title=${this.media_info.title}-演员")'
            lazy="person-card"
            .slide_card=${this.person_list.map((item) => ( html`
              <person-card
                lazy=1
                person-id=${item.id}
                person-image=${item.image}
                person-name=${item.name}
                person-role=${item.role}
                @click=${() => {
                  
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
            slide-click="javascript:navmenu('recommend?type=${this.media_type}&subtype=sim&tmdbid=${this.tmdbid}&title=${this.media_info.title}-类似')"
            lazy="normal-card"
            .slide_card=${this.similar_media.map((item) => ( html`
              <normal-card
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
            slide-click="javascript:navmenu('recommend?type=${this.media_type}&subtype=more&tmdbid=${this.tmdbid}&title=${this.media_info.title}-推荐')"
            lazy="normal-card"
            .slide_card=${this.recommend_media.map((item) => ( html`
              <normal-card
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

}


window.customElements.define("page-mediainfo", PageMediainfo);