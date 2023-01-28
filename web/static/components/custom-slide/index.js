import { html } from "../utility/lit-core.min.js";
import { CustomElement } from "../utility/utility.js";

export class CustomSlide extends CustomElement {

  static properties = {
    slide_title: { attribute: "slide-title" },
    slide_click: { attribute: "slide-click" },
    lazy: { attribute: "lazy" },
    //slide_scroll: { attribute: "slide-scroll" , reflect: true, type: Number },
    slide_card: { type: Array },
    _disabled: { state: true },
  };

  constructor() {
    super();
    this._disabled = 0;
    this.slide_title = "加载中..";
    this.slide_click = "javascript:void(0)";
    this.slide_card = Array(7).fill(html`<normal-card-placeholder></normal-card-placeholder>`);
  }

  render() {
    return html`
      <style>
        .media-slide-hide-scrollbar{
          overflow-x: scroll!important;
          overscroll-behavior-x: contain!important;
          scrollbar-width: none!important;
          -ms-overflow-style: none!important;
        }
        .media-slide-hide-scrollbar::-webkit-scrollbar{
          display: none;
        }
        .media-slide-card-number{
          position: relative;
          flex:0 0 auto;
          width:48%;
        }
        @media (min-width: 768px) {
          .media-slide-card-number{
            width:30.3030303030303%;
          }
        }
        @media (min-width: 900px) {
          .media-slide-card-number{
            width:23.25581395348837%;
          }
        }
        @media (min-width: 1150px) {
          .media-slide-card-number{
            width:18.86792452830189%;
          }
        }
        @media (min-width: 1400px) {
          .media-slide-card-number{
            width:15.87301587301587%;
          }
        }
      </style>
      <div class="container-fluid overflow-hidden px-0">
        <div class="page-header d-print-none">
          <div class="d-flex justify-content-between">
            <div class="d-inline-flex">
              <a class="nav-link ms-2" href=${this.slide_card.length == 0 ? "javascript:void(0)" : this.slide_click}>
                <h2 class="my-1">
                  <strong>${this.slide_card.length == 0 ? "加载中.." : this.slide_title}</strong>
                </h2>
                <div class="ms-2">
                  <svg xmlns="http://www.w3.org/2000/svg" class="icon-tabler icon-tabler-arrow-up-right-circle" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                    <circle cx="12" cy="12" r="9"></circle>
                    <line x1="15" y1="9" x2="9" y2="15"></line>
                    <polyline points="15 15 15 9 9 9"></polyline>
                  </svg>
                </div>
              </a>
            </div>
            <div ?hidden=${this._disabled ==3 } class="col-auto ms-auto d-print-none">
              <div class="d-inline-flex">
                <a class="btn btn-sm btn-icon btn-link text-muted border-0 ${this._disabled == 0 ? "disabled" : ""}"
                   @click=${ () => this._slideNext(false) }>
                  <svg xmlns="http://www.w3.org/2000/svg" class="btn-icon icon-tabler icon-tabler-chevron-left" width="24" height="24"
                      viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
                      stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                    <polyline points="15 6 9 12 15 18"></polyline>
                  </svg>
                </a>
                <a class="media-slide-right btn btn-sm btn-icon btn-link border-0 text-muted ${this._disabled == 2 ? "disabled" : ""}"
                   @click=${ () => this._slideNext(true) }>
                  <svg xmlns="http://www.w3.org/2000/svg" class="btn-icon icon-tabler icon-tabler-chevron-right" width="24" height="24"
                      viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round"
                      stroke-linejoin="round">
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                    <polyline points="9 6 15 12 9 18"></polyline>
                  </svg>
                </a>
              </div>
            </div>
          </div>
        </div>
        <div class="media-slide-hide-scrollbar px-2 py-3"
            @scroll=${ this._countDisabled }>
          <div class="row d-flex flex-row flex-nowrap media-slide-card-number">
            ${this.slide_card}
          </div>
        </div>
      </div>
    `;
  }

  updated(changedProperties) {
    // slide数据刷新时触发界面状态改变
    if (changedProperties.has("slide_card")) {
      this._countDisabled();
    }
  }

  // 绑定事件
  firstUpdated() {
    this._scrollbar = this.querySelector("div.media-slide-hide-scrollbar");
    this._card_number = this.querySelector("div.media-slide-card-number");
    // 初次获取元素参数
    this._countMaxNumber();
    // 窗口大小发生改变时
    this._countMaxNumber_resize = () => { this._countMaxNumber() }; // 防止无法卸载事件
    window.addEventListener("resize", this._countMaxNumber_resize);
  }

  // 卸载事件
  disconnectedCallback() {
    window.removeEventListener("resize", this._countMaxNumber_resize);
    super.disconnectedCallback();
  }
  
  _countMaxNumber() {
    this._card_width = this._card_number.getBoundingClientRect().width;
    this._card_max = Math.trunc(this._scrollbar.clientWidth / this._card_width);
    this._card_current_load_index = 0;
    this._countDisabled();
  }

  _countDisabled() {
    this._card_current = this._scrollbar.scrollLeft == 0 ? 0 : Math.trunc((this._scrollbar.scrollLeft +  this._card_width / 2) /  this._card_width)
    if (this.slide_card.length * this._card_width <= this._scrollbar.clientWidth){
      this._disabled = 3;
    } else if (this._scrollbar.scrollLeft == 0) {
      this._disabled = 0;
    } else if (this._scrollbar.scrollLeft >= this._scrollbar.scrollWidth - this._scrollbar.clientWidth - 2){
      this._disabled = 2;
    } else {
      this._disabled = 1;
    }
    // 懒加载
    if (this.lazy) {
      if (this._card_current > this._card_current_load_index - this._card_max) {
        const card_list = this._card_number.querySelectorAll(this.lazy);
        if (card_list.length > 0) {
          const show_max = this._card_current + this._card_max + 1;
          for (let i = this._card_current; i < show_max; i++) {
            if (i >= card_list.length) {
              break;
            }
            card_list[i].removeAttribute("lazy");
          }
          this._card_current_load_index = show_max;
        }
      }
    }
  }

  _slideNext(next) {
    let run_to_left_px;
    if (next) {
      const card_index = this._card_current + this._card_max;
      run_to_left_px = card_index *  this._card_width;
      if (run_to_left_px >= this._scrollbar.scrollWidth - this._scrollbar.clientWidth) {
        run_to_left_px = this._scrollbar.scrollWidth - this._scrollbar.clientWidth;
      }
    } else {
      const card_index = this._card_current - this._card_max;
      run_to_left_px = card_index *  this._card_width;
      if (run_to_left_px <= 0) {
        run_to_left_px = 0;
      }
    }
    $(this._scrollbar).animate({
      scrollLeft: run_to_left_px
    }, 350, () => {
      this._scrollbar.scrollLeft = run_to_left_px;
    });
  }


}

window.customElements.define("custom-slide", CustomSlide);