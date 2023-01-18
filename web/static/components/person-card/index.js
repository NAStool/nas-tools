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
        .lit-person-card-scale:hover {
          transform:scale(1.05, 1.05);
          opacity:1
        }
      </style>
      <div class="card card-sm lit-person-card-scale rounded-4 border-1 shadow-sm ratio cursor-pointer overflow-hidden"
           style="--tblr-border-opacity: 1;border-color: rgb(128, 128, 128); --tblr-aspect-ratio: 150%; background-image:linear-gradient(45deg,#99999b,#3f4b63 60%)">
        <div class="text-center p-4 pt-3 placeholder-glow">
          <div class="avatar-rounded overflow-hidden">
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