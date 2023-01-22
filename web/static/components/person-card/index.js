import { html } from "../utility/lit-core.min.js";
import { CustomElement } from "../utility/utility.js";

export class PersonCard extends CustomElement {

  static properties = {
    person_id: { attribute: "person-id" },
    person_image: { attribute: "person-image" },
    person_name: { attribute: "person-name" },
    person_role: { attribute: "person-role" },
    lazy: {},
  };

  constructor() {
    super();
    this.lazy = "0";
  }

  render() {
    return html`
      <style>
        .lit-person-card {
          position:relative;
          z-index:1;
          --tblr-aspect-ratio:150%;
          border:none;
          box-shadow:0 0 0 1px #888888,0 .125rem .25rem rgba(0,0,0,0.2);
          background-image:linear-gradient(45deg,#99999b,#637599 60%);
        }
        .lit-person-card:hover {
          transform:scale(1.05, 1.05);
          opacity:1;
          box-shadow:0 0 0 1px #bbbbbb;
          background-image:linear-gradient(45deg,#bbbbbd,#8597aa 60%);
        }
      </style>
      <div class="card card-sm lit-person-card rounded-4 overflow-hidden cursor-pointer ratio">
        <div class="text-center p-4 pt-3 placeholder-glow">
          <div class="avatar-rounded overflow-hidden" style="position:relative;z-index:1;">
            <custom-img
              lazy=${this.lazy}
              img-src=${this.person_image}
              img-ratio="100%"
              img-style="object-fit:cover;"
            ></custom-img>
          </div>
          <h3 class="lh-sm text-white mt-3 ${this.lazy == "1" ? "placeholder" : ""}"
              style="margin-bottom: 5px; -webkit-line-clamp:2; display: -webkit-box; -webkit-box-orient:vertical; overflow:hidden; text-overflow: ellipsis;">
            <strong>${this.person_name}</strong>
          </h3>
          <div class="lh-sm text-white mt-2 ${this.lazy == "1" ? "placeholder" : ""}"
              style="margin-bottom: 5px; -webkit-line-clamp:3; display: -webkit-box; -webkit-box-orient:vertical; overflow:hidden; text-overflow: ellipsis;">
            ${this.person_role}
          </div>
        </div>
      </div>
    `;
  }

}

window.customElements.define("person-card", PersonCard);