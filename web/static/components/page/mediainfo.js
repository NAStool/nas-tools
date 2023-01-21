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
      background: "https://www.themoviedb.org/t/p/w1920_and_h800_multi_faces/r9PkFnRUIthgBp2JZZzD380MWZy.jpg",
      image: "https://www.themoviedb.org/t/p/w300_and_h450_bestv2/rnn30OlNPiC3IOoWHKoKARGsBRK.jpg",
      vote: "8.6",
      year: "2022",
      title: "穿靴子的猫2",
      overview: "时隔11年，臭屁自大又爱卖萌的猫大侠回来了！如今的猫大侠（安东尼奥·班德拉斯 配音），依旧幽默潇洒又不拘小节、数次“花式送命”后，九条命如今只剩一条，于是不得不请求自己的老搭档兼“宿敌”——迷人的软爪妞（萨尔玛·海耶克 配音）来施以援手来恢复自己的九条生命。",
      certification: "PG",
      genres: "动画, 动作, 冒险, 喜剧, 家庭, 奇幻",
      runtime: "1h 42m",
      fact: [
        {"评分": "8.6"},
        {"原始标题": "Puss in Boots: The Last Wish"},
        {"状态": "已发布"},
        {"上映日期": "2022-12-23 (CN)"},
        {"收入": "US$254,905,780.00"},
        {"成本": "US$90,000,000.00"},
        {"原始语言": "英语"},
        {"出品国家": "美国"},
        {"制作公司": "Universal Pictures, DreamWorks Animation"},
      ],
      crew: [
        {"Tommy Swerdlow": "Screenplay, Story"},
        {"Joel Crawford": "Director"},
        {"Paul Fisher": "Screenplay"},
        {"Tom Wheeler": "Story"},
      ],
    // ......... 参数
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
        overview: "时隔11年，臭屁自大又爱卖萌的猫大侠回来了！如今的猫大侠（安东尼奥·班德拉斯 配音），依旧幽默潇洒又不拘小节、数次“花式送命”后，九条命如今只剩一条，于是不得不请求自己的老搭档兼“宿敌”——迷人的软爪妞（萨尔玛·海耶克 配音）来施以援手来恢复自己的九条生命。",
      });
    }
    this.similar_media = new_list;
    this.recommend_media = new_list;
  }

  render() {
    return html`
      <style>
        .lit-media-info-background {
          background-image:
            linear-gradient(180deg, rgba(var(--tblr-body-bg-rgb),0.5) 50%, rgba(var(--tblr-body-bg-rgb),1) 100%),
            linear-gradient(0, rgba(var(--tblr-body-bg-rgb),0) 90%, rgba(var(--tblr-body-bg-rgb),1) 100%),
            linear-gradient(90deg, rgba(var(--tblr-body-bg-rgb),0) 90%, rgba(var(--tblr-body-bg-rgb),1) 100%),
            linear-gradient(270deg, rgba(var(--tblr-body-bg-rgb),0) 90%, rgba(var(--tblr-body-bg-rgb),1) 100%)
        }
        .lit-media-info-image {
          width:233px;
          height:350px;
        }

        @media (max-width: 767.98px) {
          .lit-media-info-image {
            width:166px;
            height:250px;
          }
        }
      </style>
      <div class="container-xl">
        <!-- 渲染媒体信息 -->
        <div class="card rounded-0" style="border:none;height:490px">
          <img src=${this.media_info.background} class="card-img rounded-0" alt=""
            style="display: block; width: 0px; height: 0px; min-width: 100%; max-width: 100%; min-height: 100%; max-height: 100%; object-fit: cover;"/>
          <div class="card-img-overlay rounded-0 lit-media-info-background">
            <div class="d-md-flex flex-md-row mb-4">
              <custom-img class="d-flex justify-content-center"
                img-class="rounded-4 object-cover lit-media-info-image"
                img-src=${this.media_info.image}>
              </custom-img>
              <div class="d-flex justify-content-center">
                <div class="d-flex flex-column justify-content-end ms-2">
                  <h1 class="align-self-center align-self-md-start display-6">
                    <strong>${this.media_info.title}</strong>
                    <strong class="h1">(${this.media_info.year})</strong>
                  </h1>
                  <div class="align-self-center align-self-md-start">
                    <span class="badge badge-outline text-warning me-1">${this.media_info.certification}</span>
                    <span class="badge badge-outline text-primary me-1">${this.media_info.runtime}</span>
                    <span class="">${this.media_info.genres}</span>
                  </div>
                </div>
              </div>
            </div>
            <h1 class="d-flex">
              <strong>简介</strong>
            </h1>
          </div>
        </div>
        <div class="row">
          <div class="col-lg-8">
            <h2 class="text-muted ms-4 me-2">
              <small>${this.media_info.overview}</small>
            </h2>
            <div class="row mx-2 mt-4">
              ${this.media_info.crew
              ? this.media_info.crew.map((item, index) => ( html`
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
            <div class="ms-3 me-2 mt-1">
              <div class="card rounded-3" style="background: none">
                ${this.media_info.fact
                ? this.media_info.fact.map((item) => ( html`
                  <div class="card-body p-2">
                    <div class="d-flex justify-content-between">
                      <div style="min-width:25%;">
                        <strong>${Object.keys(item)[0]}</strong>
                      </div>
                      <div class="text-break text-muted">
                        ${Object.values(item)[0]}
                      </div>
                    </div>
                  </div>
                  `) )
                : nothing }
              </div>
            </div>
          </div>
        </div>
        

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