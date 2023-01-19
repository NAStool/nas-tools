import { html } from "../utility/lit-core.min.js";
import { CustomElement } from "../utility/utility.js";

export class NormalCardPlaceholder extends CustomElement {
  constructor() {
    super();
  }

  static render_placeholder() {
    return html`
      <div class="placeholder-glow">
        <div class="ratio placeholder cursor-pointer" style="--tblr-aspect-ratio:150%"></div>
      </div>
    `;
  }

  render() {
    return html`
      <div class="card card-sm rounded-4 overflow-hidden">
        ${NormalCardPlaceholder.render_placeholder()}
      </div>
    `;
  }
}

window.customElements.define("normal-card-placeholder", NormalCardPlaceholder);