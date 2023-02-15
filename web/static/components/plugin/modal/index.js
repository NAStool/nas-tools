import { html, nothing } from "../../utility/lit-core.min.js";
import { CustomElement } from "../../utility/utility.js";

export class PluginModal extends CustomElement {
  static properties = {
    id: {attribute: "plugin-id"},
    name: {attribute: "plugin-name"},
    config: {attribute: "plugin-config", type: Object},
    fields: {attribute: "plugin-fields", type: Array},
    prefix: {attribute: "plugin-prefix"},
  };

  constructor() {
    super();
    this.id = "";
    this.name = "";
    this.config = {};
    this.fields = [];
    this.prefix = "";
  }

  __render_fields() {
    let content = html``;
    for (let field of this.fields) {
      switch(field["type"]) {
        case "div":
          content = html`${content}${this.__render_div(field)}`;
          break;
        case "details":
          content = html`${content}${this.__render_details(field)}`;
          break;
      }
    }
    return content;
  }

  __render_div(field) {
    let field_content = field["content"];
    let div_content = html``;
    for (let row of field_content) {
      let row_content = html``;
      for (let col of row) {
        let col_type = col["type"];
        switch(col_type) {
          case "text":
            row_content = html`${row_content}${this.__render_text(col)}`;
            break;
          case "select":
            row_content = html`${row_content}${this.__render_select(col)}`;
            break;
          case "switch":
            row_content = html`${row_content}${this.__render_switch(col)}`;
            break;
        }
      }
      div_content =  html`${div_content}<div class="row">${row_content}</div>`;
    }
    return div_content
  }

  __render_details(field) {
    let title = field["summary"];
    let tooltip = field["tooltip"];
    return html`<details class="mb-2">
                  <summary class="summary mb-2">
                    ${title} ${this.__render_note(tooltip)}
                  </summary>
                  ${this.__render_div(field)}
                </details>`
  }

  __render_text(field_content) {
    let text_content = html``;
    let title = field_content["title"];
    let required = field_content["required"];
    let tooltip = field_content["tooltip"];
    let content = field_content["content"];
    for (let index in content) {
      let id = content[index]["id"];
      let placeholder = content[index]["placeholder"];
      if (index === "0") {
        text_content = html`<div class="mb-1">
                      <label class="form-label ${required}">${title} ${this.__render_note(tooltip)}</label>
                      <input type="text" value="${this.__render_value(id)}" class="form-control" id="${this.prefix}${id}" placeholder="${placeholder}" autocomplete="off">
                    </div>`
      } else {
        text_content = html`${text_content}<div class="mb-3">
                      <input type="text" value="${this.__render_value(id)}" class="form-control" id="${this.prefix}${id}" placeholder="${placeholder}" autoComplete="off">
                    </div>`
      }
    }
    return html`<div class="col-12 col-lg">${text_content}</div>`
  }

  __render_select(field_content) {
    let content = ``;
    return `<div class="col-12 col-lg"></div>`
  }

  __render_switch(field_content) {
    let content = ``;
    return `<div class="col-12 col-lg"></div>`
  }

  __render_value(id) {
    return `${this.config[id] || ""}`;
  }

  __render_note(tooltip) {
    if (tooltip) {
      return html`<span class="form-help" data-bs-toggle="tooltip" data-bs-original-title="${tooltip}">?</span>`;
    }
  }

  render() {
    return html`<div class="modal modal-blur fade" id="modal-plugin-${this.id}" tabindex="-1" role="dialog" aria-hidden="true"
                     data-bs-backdrop="static" data-bs-keyboard="false">
                  <div class="modal-dialog modal-lg modal-dialog-centered" role="document">
                    <div class="modal-content">
                      <div class="modal-header">
                        <h5 class="modal-title">${this.name}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                      </div>
                      <div class="modal-body">
                      ${this.__render_fields()}
                      </div>
                      <div class="modal-footer">
                        <a href="javascript:save_plugin_config('${this.id}', '${this.prefix}')" class="btn btn-primary">
                          确定
                        </a>
                      </div>
                    </div>
                  </div>
                </div>`
  }

}

window.customElements.define("plugin-modal", PluginModal);