import { html } from "../../utility/lit-core.min.js";
import { CustomElement, Golbal } from "../../utility/utility.js";

export class PagePerson extends CustomElement {
  static properties = {
    page_title: { attribute: "page-title" },
    page_subtitle: { attribute: "page-subtitle"},
    media_type: { attribute: "media-type" },
    tmdbid: { attribute: "media-tmdbid" },
    keyword: { attribute: "keyword" },
    person_list: { type: Array },
  };

  constructor() {
    super();
    this.person_list = [];
    this.result = false;
  }

  // 仅执行一次  界面首次刷新后
  firstUpdated() {
    Golbal.get_cache_or_ajax("media_person", this.media_type, { tmdbid: this.tmdbid, type: this.media_type, keyword: this.keyword },
      (ret) => {
        if (ret.code === 0) {
          this.person_list = ret.data;
          this.result = true;
        }
      }
    );
  }

  render() {
    return html`
      <div class="container-xl">
        <div class="page-header d-print-none">
          <div class="row align-items-center">
            <div class="col">
              <h2 class="page-title">${this.page_title}</h2>
              <div class="text-muted mt-1">${this.page_subtitle}</div>
            </div>
          </div>
        </div>
      </div>
      <div class="page-body">
        <div class="container-xl">
          ${this.person_list.length !== 0
          ? html`<div class="d-grid gap-3 grid-media-card">
            ${this.person_list.map((item, index) => ( html`
              <person-card
                person-id=${item.id}
                person-image=${item.image}
                person-name=${item.name}
                person-role=${item.role}
                @click=${() => {
                  navmenu("recommend?type="+this.media_type+"&subtype=person&personid="+item.id+"&title=参演作品&subtitle="+item.name)
                }}
              ></person-card>`))
            }</div>`
          : this.result ? html`
            <div class="container-xl d-flex flex-column justify-content-center">
              <div class="empty">
                <div class="empty-img"><img src="./static/img/posting_photo.svg" height="128" alt="">
                </div>
                <p class="empty-title">没有数据。</p>
              </div>
            </div>` 
          : html`<div class="d-grid gap-3 grid-media-card">${Array(20).fill(html`<person-card lazy="1"></person-card>`)}</div>`
          }
          </div>            
        </div>
      </div>
    `;
  }

}


window.customElements.define("page-person", PagePerson);