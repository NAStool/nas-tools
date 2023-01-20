import { html } from "../utility/lit-core.min.js";
import { CustomElement } from "../utility/utility.js";

class PagePerson extends CustomElement {
  static properties = {
    page_title: { attribute: "page-title" },
    person_list: { type: Array },
  };

  constructor() {
    super();
    this.page_title = "加载中.."
    this.person_list = [];
  }

  // 仅执行一次  界面首次刷新后
  firstUpdated() {
    // 要从这里获取演员信息吗 ?
    // demo
    // const new_list = [];
    // for (let i = 0; i < 20; i++) {
    //     new_list.push({
    //       id: "3131-antonio-banderas",
    //       image: "https://www.themoviedb.org/t/p/w138_and_h175_face/iWIUEwgn2KW50MssR7tdPeFoRGW.jpg",
    //       name: "Antonio Banderas", 
    //       role: "Puss in Boots (voice)",
    //     });
    // }
    // this.person_list = new_list;
  }

  render() {
    return html`
      <div class="container-xl">
        <div class="page-header d-print-none">
          <div class="row align-items-center">
            <div class="col">
              <h2 class="page-title">${this.page_title}</h2>
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
                    // 点击演员卡片后是否需要做点什么 ?
                    console.log(item, index);
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