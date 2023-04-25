import { html } from "../../utility/lit-core.min.js";
import { CustomElement } from "../../utility/utility.js";

export class CustomPlexLibraryImg extends CustomElement {

  static properties = {
    img_src_list: { attribute: "img-src-list" },
  };

  constructor() {
    super();
  }

  firstUpdated() {
    this._init()
  }

  _init(){
    const canvas = this.querySelector("canvas");
    const ctx = canvas.getContext("2d");
    // 设置背景色为黑色
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const IMAGES = this.img_src_list.split(",");
    const POSTER_WIDTH = 150;
    const POSTER_HEIGHT = 252;
    const MARGIN_WIDTH = 8;
    const MARGIN_HEIGHT = 4;
    const REFLECTION_HEIGHT = POSTER_HEIGHT / 2;
    const REFLECTION_SHOW_HEIGHT = 100;

    async function loadImages() {
        // 只要4个,取最小值保证不越界
        const loopCount = Math.min(4, IMAGES.length);
        for (let i = 0; i < loopCount; i++) {
            const img = new Image();
            img.src = IMAGES[i];
            await new Promise(resolve => img.onload = resolve);
            drawImageWithReflection(img, i + 1);
        }
    }
    function drawImageWithReflection(img, index) {
        const x = MARGIN_WIDTH * index + POSTER_WIDTH * (index - 1);
        const y = MARGIN_HEIGHT;

        ctx.drawImage(img, x, y, POSTER_WIDTH, POSTER_HEIGHT);

        ctx.save();
        ctx.translate(0, canvas.height);
        ctx.scale(1, -1);
        ctx.drawImage(
            img,
            0,
            0,
            img.width,
            img.height,
            x,
            REFLECTION_SHOW_HEIGHT - REFLECTION_HEIGHT,
            POSTER_WIDTH,
            REFLECTION_HEIGHT
        );

        const gradient = ctx.createLinearGradient(
            0,
            REFLECTION_SHOW_HEIGHT - REFLECTION_HEIGHT,
            0,
            REFLECTION_HEIGHT
        );
        gradient.addColorStop(0, "rgba(0, 0, 0, 1)");
        gradient.addColorStop(1, "rgba(0, 0, 0, 0.3)");
        ctx.fillStyle = gradient;
        ctx.fillRect(x, 0, POSTER_WIDTH, REFLECTION_SHOW_HEIGHT);

        ctx.restore();
    }

    // 开始加载~
    loadImages()
  }


  render() {
    return html`
        <canvas width="640" height="360" class="w-100"></canvas>
    `;
  }

}

window.customElements.define("custom-plex-library-img", CustomPlexLibraryImg);