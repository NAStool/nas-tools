import { html, nothing } from "../../utility/lit-core.min.js";
import { CustomElement } from "../../utility/utility.js";

export class LayoutSearchbar extends CustomElement {
  static properties = {
    
  };

  constructor() {
    super();
  }

  firstUpdated() {
    
  }

  render() {
    return html`
      <div></div>
    `;
  }

}


window.customElements.define("layout-searchbar", LayoutSearchbar);