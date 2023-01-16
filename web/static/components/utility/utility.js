import { LitElement } from "./lit-core.min.js";

export class CustomElement extends LitElement {

  // 兼容前进后退时重载
  connectedCallback() {
    super.connectedCallback();
    this.innerHTML = "";
  }

  // 过滤空字符
  attributeChangedCallback(name, oldValue, newValue) {
    super.attributeChangedCallback(name, oldValue, Golbal.repNull(newValue));
  }

  // 不使用影子dom
  createRenderRoot() {
    return this;
  }

}

export class Golbal {

  // 没有图片时
  static noImage = "../static/img/no-image.png";

  // 转换传值的空字符情况
  static repNull(value) {
    if (!value || value == "None" || value == "null") {
      return "";
    } else {
      return value;
    }
  }

  // 是否触摸屏设备
  static is_touch_device() {
    return 'ontouchstart' in window;
  }

}