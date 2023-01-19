import { html } from "../utility/lit-core.min.js";
import { CustomElement } from "../utility/utility.js";

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
      "tv": [
        {
          title:"TMDB最新电视剧",
          type :"nt",
        },
        {
          title:"TMDB热门电视剧",
          type :"ht",
        },
        {
          title:"豆瓣热门电视剧",
          type :"dbht",
        },
        {
          title:"豆瓣热门动漫",
          type :"dbdh",
        },
        {
          title:"豆瓣热门综艺",
          type :"dbzy",
        },
      ],
      "movie":[
        {
          title:"正在热映",
          type :"dbom",
        },
        {
          title:"即将上映",
          type :"dbnm",
        },
        {
          title:"TMDB最新电影",
          type :"nm",
        },
        {
          title:"TMDB热门电影",
          type :"hm",
        },
        {
          title:"豆瓣热门电影",
          type :"dbhm",
        },
        {
          title:"豆瓣电影TOP250",
          type :"dbtop",
        },
      ],
      "bangumi": [
        {
          title:"星期一",
          type :"bangumi",
          week :"1",
        },{
          title:"星期二",
          type :"bangumi",
          week :"2",
        },{
          title:"星期三",
          type :"bangumi",
          week :"3",
        },{
          title:"星期四",
          type :"bangumi",
          week :"4",
        },{
          title:"星期五",
          type :"bangumi",
          week :"5",
        },{
          title:"星期六",
          type :"bangumi",
          week :"6",
        },{
          title:"星期日",
          type :"bangumi",
          week :"7",
        },
      ]
    }
  }

  firstUpdated() {
    for (const item of this._media_type_list[this.discovery_type]) {
      ajax_post("get_recommend", { "type": item.type, "page": 1, "week": item.week},
        (ret) => {
          this._slide_card_list = {...this._slide_card_list, [item.type + (item.week ?? "")]: ret.Items};
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
            slide-click="javascript:navmenu('recommend?t=${item.type}&week=${item.week ?? ""}')"
            lazy="normal-card"
            .slide_card=${this._slide_card_list[item.type + (item.week ?? "")]
              ? this._slide_card_list[item.type + (item.week ?? "")].map((card) => ( html`
                <normal-card
                  lazy=1
                  card-tmdbid=${card.id}
                  card-pagetype=${item.type}
                  card-showsub=1
                  card-image=${card.image}
                  card-fav=${card.fav}
                  card-vote=${card.vote}
                  card-year=${card.year}
                  card-title=${card.title}
                  card-overview=${card.overview}
                ></normal-card>`))
              : Array(7).fill(html`<normal-card-placeholder></normal-card-placeholder>`)
            }
          ></custom-slide>`
        ))}
      </div>
    `;
  }
}


window.customElements.define("page-discovery", PageDiscovery);