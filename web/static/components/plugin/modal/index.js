import { html, nothing } from "../../utility/lit-core.min.js";
import { CustomElement } from "../../utility/utility.js";

export class PluginModal extends CustomElement {
  static properties = {
    id: {attribute: "plugin-id"},
    name: {attribute: "plugin-name"},
    config: {attribute: "plugin-config", type: Object},
    fields: {attribute: "plugin-fields", type: Array},
    prefix: {attribute: "plugin-prefix"},
    page: {attribute: "plugin-page"},
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
          case "password":
            row_content = html`${row_content}${this.__render_text(col)}`;
            break;
          case "switch":
            row_content = html`${row_content}${this.__render_switch(col)}`;
            break;
          case "select":
            row_content = html`${row_content}${this.__render_select(col)}`;
            break;
          case "textarea":
            row_content = html`${row_content}${this.__render_textarea(col)}`;
            break;
          case "form-selectgroup":
            row_content = html`${row_content}${this.__render_form_selectgroup(col)}`;
            break;
          default:
            break;
        }
      }
      div_content =  html`${div_content}<div class="row mb-2">${row_content}</div>`;
    }
    return div_content
  }

  __render_details(field) {
    let title = field["summary"];
    let tooltip = field["tooltip"];
    let id = field["id"];
    let hidden = field["hidden"];
    let open = field["open"];
    return html`<details class="mb-2" id="${this.prefix}${id}" style="display:${hidden ? 'none':'block'}" ?open="${open}">
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
    let hidden = field_content["hidden"];
    let type = field_content["type"];
    let content = field_content["content"];
    let text = html``;
    for (let index in content) {
      let id = content[index]["id"];
      let placeholder = content[index]["placeholder"];
      let default_value = content[index]["default"];
      if (index === "0") {
        text = html`<input type="${type}" value="${this.config[id] || default_value || ''}" class="form-control" id="${this.prefix}${id}" placeholder="${placeholder}" autocomplete="off" ?hidden=${hidden}>`
        text_content = html`<div class="mb-1">
                      <label class="form-label ${required}">${title} ${this.__render_note(tooltip)}</label>
                      ${text}
                    </div>`
      } else {
        text = html`<input type="text" value="${this.config[id] || default_value || ""}" class="form-control" id="${this.prefix}${id}" placeholder="${placeholder}" autoComplete="off" ?hidden=${hidden}>`
        text_content = html`${text_content}<div class="mb-3">
                      ${text}
                    </div>`
      }
    }
    return html`<div class="col-12 col-lg">${text_content}</div>`
  }


  __render_switch(field_content) {
    let title = field_content["title"];
    let required = field_content["required"];
    let tooltip = field_content["tooltip"];
    let id = field_content["id"];
    let onclick = field_content["onclick"];
    let default_value = field_content["default"];
    let checkbox;
    if (this.config[id] || (this.config[id] === undefined && default_value)) {
      checkbox = html`<input class="form-check-input" type="checkbox" id="${this.prefix}${id}" onclick="${onclick}" checked>`
    } else {
      checkbox = html`<input class="form-check-input" type="checkbox" id="${this.prefix}${id}" onclick="${onclick}">`
    }
    return html`<div class="col-12 col-lg">
                  <div class="mb-1">
                    <label class="form-check form-switch ${required}">
                    ${checkbox}
                    <span class="form-check-label">${title} ${this.__render_note(tooltip)}</span>
                  </label>
                  </div>
                </div>`
  }

  __render_select(field_content) {
    let text_content = html``;
    let title = field_content["title"];
    let required = field_content["required"];
    let tooltip = field_content["tooltip"];
    let content = field_content["content"];
    for (let index in content) {
      let id = content[index]["id"];
      let options = content[index]["options"];
      let default_value = content[index]["default"];
      let onchange = content[index]["onchange"];
      let text_options = html``;
      for (let option in options) {
        if (this.config[id]) {
          if (this.config[id] === option) {
            text_options = html`${text_options}<option value="${option}" selected>${options[option]}</option>`
          } else {
            text_options = html`${text_options}<option value="${option}">${options[option]}</option>`
          }
        } else if (default_value && default_value === option) {
          text_options = html`${text_options}<option value="${option}" selected>${options[option]}</option>`
        } else {
          text_options = html`${text_options}<option value="${option}">${options[option]}</option>`
        }
      }
      text_content = html`
        <div class="mb-1">
          <label class="form-label ${required}">${title} ${this.__render_note(tooltip)}</label>
          <select class="form-control" id="${this.prefix}${id}" onchange="${onchange}">
            ${text_options}
          </select>
        </div>`
    }
    return html`<div class="col-12 col-lg">${text_content}</div>`
  }

  __render_textarea(field_content) {
    let title = field_content["title"];
    let required = field_content["required"];
    let tooltip = field_content["tooltip"];
    let content = field_content["content"];
    let readonly = field_content["readonly"];
    let id = content["id"];
    let placeholder = content["placeholder"];
    let rows = content["rows"] || 5;
    let label = html``;
    let textarea = html``;
    if (title) {
      label = html`<label class="form-label ${required}">${title} ${this.__render_note(tooltip)}</label>`
    }
    if (readonly) {
      textarea = html`<textarea class="form-control" id="${this.prefix}${id}" rows="${rows}" placeholder="${placeholder}" readonly>${this.config[id] || ""}</textarea>`
    } else {
      textarea = html`<textarea class="form-control" id="${this.prefix}${id}" rows="${rows}" placeholder="${placeholder}">${this.config[id] || ""}</textarea>`
    }
    return html`<div class="col-12 col-lg">
                  <div class="mb-1">
                    ${label}
                    ${textarea}
                  </div>
                </div>`
  }

  __render_form_selectgroup(field_content) {
    let content = field_content["content"];
    let id = field_content["id"];
    let onclick = field_content["onclick"] || "";
    let text_options = html``;
    // 单选
    if (field_content["radio"]) {
      onclick += `check_selectgroup_raido(this);`
    }
    for (let option in content) {
      let checkbox;
      if (this.config[id] && this.config[id].includes(option)) {
        checkbox = html`<input type="checkbox" name="${this.prefix}${id}" value="${option}" onclick="${onclick}" class="form-selectgroup-input" checked>`
      } else {
        checkbox = html`<input type="checkbox" name="${this.prefix}${id}" value="${option}" onclick="${onclick}" class="form-selectgroup-input">`
      }
      text_options = html`${text_options}
                          <label class="form-selectgroup-item">
                            ${checkbox}
                            <span class="form-selectgroup-label">${content[option].name}</span>
                          </label>`
    }
    return html`<div class="col-12 col-lg">
                  <div class="mb-1">
                    <div class="form-selectgroup" id="${this.prefix}${id}">
                      ${text_options}
                    </div>
                  </div>
                </div>`
  }

  __render_note(tooltip) {
    if (tooltip) {
      return html`<span class="form-help" data-bs-toggle="tooltip" title="${tooltip}">?</span>`;
    }
  }

  render() {
    return html`
      <div class="modal modal-blur fade" id="modal-plugin-${this.id}" tabindex="-1" role="dialog" aria-hidden="true"
           data-bs-backdrop="static" data-bs-keyboard="false">
        <div class="modal-dialog modal-lg modal-dialog-centered" role="document">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">${this.name}</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body" style="overflow-y: auto">
            ${this.__render_fields()}
            </div>
            <div class="modal-footer">
              <a href="javascript:show_plugin_extra_page('${this.id}')" class="btn me-auto" ?hidden="${!this.page}">
                ${this.page}
              </a>
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