import { html } from "../../utility/lit-core.min.js";
import { CustomElement } from "../../utility/utility.js";


export class LayoutNavbarButton extends CustomElement {
  render() {
    return html`
      <button class="navbar-toggler d-lg-none" type="button" data-bs-toggle="offcanvas" data-bs-target="#litLayoutNavbar">
        <span class="navbar-toggler-icon"></span>
      </button>
    `;
  }
}


window.customElements.define("layout-navbar-button", LayoutNavbarButton);