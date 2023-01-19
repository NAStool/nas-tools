import { html } from "../utility/lit-core.min.js";
import { CustomElement, Golbal } from "../utility/utility.js";

export class CustomImg extends CustomElement {

  static properties = {
    img_src: { attribute: "img-src" },
    img_class: { attribute: "img-class" },
    img_style: { attribute: "img-style" },
    img_ratio: { attribute: "img-ratio" },
    lazy: {},
    _placeholder: { state: true },
  };

  constructor() {
    super();
    this.lazy = "0";
    this._placeholder = true;
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name == "img-src" && oldValue != newValue) {
      this._placeholder = true;
    }
    super.attributeChangedCallback(name, oldValue, newValue);
  }

  render() {
    const styles = `--tblr-aspect-ratio:${this.img_ratio}; ${this.img_style}`;
    return html`
      <div ?hidden=${!this._placeholder} class="placeholder-glow">
        <div class="ratio placeholder cursor-pointer" style=${styles}></div>
      </div>
      <div ?hidden=${this._placeholder} class="ratio" style="--tblr-aspect-ratio:${this.img_ratio};">
        <img class=${this.img_class} style=${this.img_style} alt=""
          src=${this.lazy == "1" ? "" : this.img_src ?? Golbal.noImage}
          @error=${() => { if (this.lazy != "1") { this.img_src = Golbal.noImage } }}
          @load=${() => { this._placeholder = false }}/>
      </div>
    `;
  }

}

window.customElements.define("custom-img", CustomImg);