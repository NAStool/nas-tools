import { html, nothing } from "../utility/lit-core.min.js";
import { CustomElement } from "../utility/utility.js";

class PageMediainfo extends CustomElement {
  static properties = {
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
    // 要从这里获取媒体信息吗 ?
    // demo

    // 媒体信息
    this.media_info = {
      background: ""
    };

    // 演员阵容
    let new_list = [];
    for (let i = 0; i < 20; i++) {
      new_list.push({
        id: "3131-antonio-banderas",
        image: "https://www.themoviedb.org/t/p/w138_and_h175_face/iWIUEwgn2KW50MssR7tdPeFoRGW.jpg",
        name: "Antonio Banderas", 
        role: "Puss in Boots (voice)",
      });
    }
    this.person_list = new_list;

    // 类似和推荐
    new_list = [];
    for (let i = 0; i < 20; i++) {
      new_list.push({
        id: "315162",
        type: "mov",
        image: "https://www.themoviedb.org/t/p/w300_and_h450_bestv2/rnn30OlNPiC3IOoWHKoKARGsBRK.jpg",
        fav: "0",
        vote: "8.6",
        year: "2022",
        title: "穿靴子的猫2",
        overview: "时隔11年，臭屁自大又爱卖萌的猫大侠回来了！如今的猫大侠（安东尼奥·班德拉斯 配音），依旧幽默潇洒又不拘小节、数次“花式送命”后，九条命如今只剩一条，于是不得不请求自己的老搭档兼“宿敌”——迷人的软爪妞（萨尔玛·海耶克 配音）来施以援手来恢复自己的九条生命。"
      });
    }
    this.similar_media = new_list;
    this.recommend_media = new_list;
  }

  render() {
    return html`
      <div class="container-xl">
        <!-- .....未完成部分 -->
        <!-- ?? this.media_info -->
        <!-- 上面媒体信息待编写 -->

        <!-- 渲染演员阵容 -->
        ${this.person_list.length
        ? html`
          <custom-slide
            slide-title="演员阵容"
            slide-click="javascript:navmenu('person?xxxxxx=xxxxxx')"
            lazy="person-card"
            .slide_card=${this.person_list.map((item) => ( html`
              <person-card
                lazy=1
                person-id=${item.id}
                person-image=${item.image}
                person-name=${item.name}
                person-role=${item.role}
                @click=${() => {
                  // 点击演员卡片后是否需要做点什么 ?
                  console.log(item);
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
            slide-click="javascript:navmenu('recommend?xxxxxx=xxxxxx')"
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
        ${this.similar_media.length
        ? html`
          <custom-slide
            slide-title="推荐"
            slide-click="javascript:navmenu('recommend?xxxxxx=xxxxxx')"
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

      </div>
    `;
  }

}


window.customElements.define("page-mediainfo", PageMediainfo);