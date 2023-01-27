import { html } from "../utility/lit-core.min.js";
import { CustomElement, Golbal } from "../utility/utility.js";

class PagePerson extends CustomElement {
  static properties = {
    page_title: { attribute: "page-title" },
    page_subtitle: { attribute: "page-subtitle"},
    media_type: { attribute: "media-type" },
    tmdbid: { attribute: "media-tmdbid" },
    person_list: { type: Array },
  };

  constructor() {
    super();
    this.person_list = [];
  }

  // 仅执行一次  界面首次刷新后
  firstUpdated() {
    Golbal.get_cache_or_ajax("media_person", this.media_type, { "tmdbid": this.tmdbid, "type": this.media_type},
      (ret) => {
        if (ret.code === 0) {
          this.person_list = ret.data;
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
          <div class="row">
            ${this.person_list.length != 0
            ? this.person_list.map((item, index) => ( html`
              <div class="mb-3 col-6 col-md-3 col-xl-2">
                <person-card
                  person-id=${item.id}
                  person-image=${item.image}
                  person-name=${item.name}
                  person-role=${item.role}
                  @click=${() => {
                    navmenu("recommend?type="+this.media_type+"&subtype=person&personid="+item.id+"&title=参演作品&subtitle="+item.name)
                  }}
                ></person-card>
              </div>` ) )
            : Array(20).fill(html`
              <div class="mb-3 col-6 col-md-3 col-xl-2">
                <person-card lazy="1"></person-card>
              </div>`)
            }
          </div>            
        </div>
      </div>
    `;
  }

}


window.customElements.define("page-person", PagePerson);