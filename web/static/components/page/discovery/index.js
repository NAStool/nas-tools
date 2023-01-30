import { html, nothing } from "../../utility/lit-core.min.js";
import { CustomElement, Golbal } from "../../utility/utility.js";

class PageDiscovery extends CustomElement {
  static properties = {
    discovery_type: { attribute: "discovery-type" },
    _slide_card_list: { state: true },
    _media_type_list: { state: true },
  };

  constructor() {
    super();
    this._slide_card_list = {};
    this._media_type_list = {
      "TV": [
        {
          title:"TMDB最新电视剧",
          subtype :"nt",
          mediatype: "电视剧",
        },
        {
          title:"TMDB热门电视剧",
          subtype :"ht",
          mediatype: "电视剧",
        },
        {
          title:"豆瓣热门电视剧",
          subtype :"dbht",
          mediatype: "电视剧",
        },
        {
          title:"豆瓣热门动漫",
          subtype :"dbdh",
          mediatype: "动漫",
        },
        {
          title:"豆瓣热门综艺",
          subtype :"dbzy",
          mediatype: "综艺",
        }
      ],
      "MOV":[
        {
          title:"正在热映",
          subtype :"dbom",
          mediatype: "电影",
        },
        {
          title:"即将上映",
          subtype :"dbnm",
          mediatype: "电影",
        },
        {
          title:"TMDB最新电影",
          subtype :"nm",
          mediatype: "电影",
        },
        {
          title:"TMDB热门电影",
          subtype :"hm",
          mediatype: "电影",
        },
        {
          title:"豆瓣热门电影",
          subtype :"dbhm",
          mediatype: "电影",
        },
        {
          title:"豆瓣电影TOP250",
          subtype :"dbtop",
          mediatype: "电影",
        }
      ],
      "BANGUMI": [
        {
          title:"星期一",
          subtype :"Mon",
          week :"1",
        },{
          title:"星期二",
          subtype :"Tues",
          week :"2",
        },{
          title:"星期三",
          subtype :"Wed",
          week :"3",
        },{
          title:"星期四",
          subtype :"Thur",
          week :"4",
        },{
          title:"星期五",
          subtype :"Fri",
          week :"5",
        },{
          title:"星期六",
          subtype :"Sat",
          week :"6",
        },{
          title:"星期日",
          subtype :"Sun",
          week :"7",
        },
      ]
    }
  }

  firstUpdated() {
    for (const item of this._media_type_list[this.discovery_type]) {
      Golbal.get_cache_or_ajax("get_recommend", item.subtype, { "type": this.discovery_type, "subtype": item.subtype, "page": 1, "week": item.week},
        (ret) => {
          this._slide_card_list = {...this._slide_card_list, [item.subtype]: ret.Items};
        }
      );
    }
  }

  render() {
    return html`
      <div class="container-xl">
        ${this._media_type_list[this.discovery_type]?.map((item) => ( html`
          <custom-slide
            slide-title=${item.title}
            slide-click="javascript:navmenu('recommend?type=${this.discovery_type}&subtype=${item.subtype}&week=${item.week ?? ""}&title=${item.title}')"
            lazy="normal-card"
            .slide_card=${this._slide_card_list[item.subtype]
              ? this._slide_card_list[item.subtype].map((card, index) => ( html`
                <normal-card
                  @fav_change=${(e) => {
                    Golbal.update_fav_data("get_recommend", item.subtype, (extra) => (
                      extra.Items[index].fav = e.detail.fav, extra
                    ));
                  }}
                  lazy=1
                  card-tmdbid=${card.id}
                  card-pagetype=${this.discovery_type}
                  card-showsub=1
                  card-image=${card.image}
                  card-fav=${card.fav}
                  card-vote=${card.vote}
                  card-year=${card.year}
                  card-title=${card.title}
                  card-overview=${card.overview}
                  card-restype=${item.mediatype ?? nothing}
                  card-weekday=${item.week ? item.title : nothing}
                  class="px-2"
                ></normal-card>`))
              : Array(20).fill(html`<normal-card-placeholder></normal-card-placeholder>`)
            }
          ></custom-slide>`
        ))}
      </div>
    `;
  }
}


window.customElements.define("page-discovery", PageDiscovery);