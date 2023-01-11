import { html } from "lit";
import { TailwindElement } from "../TailwindElement";

export class MyElement extends TailwindElement {
  render() {
    return html`
      <label for="my-modal" class="btn m-3 text-gray-100 
      transition duration-500 ease-in-out bg-blue-600 hover:bg-red-600 transform hover:-translate-y-1 hover:scale-110">
        这是 Lit/TailwindCSS/daisyUI 的结合
      </label>
      <input type="checkbox" id="my-modal" class="modal-toggle" />
      <div class="modal">
        <div class="modal-box bg-zinc-800 text-gray-100
        rounded ">
          <h3 class="font-bold text-lg ">
            正在测试弹窗
          </h3>
          <p class="py-4">
            成功弹出了提示框!
          </p>
          <div class="modal-action">
            <label for="my-modal" class="btn bg-pink-500 text-gray-900">知道了!</label>
          </div>
        </div>
      </div>
    `;
  }
}

window.customElements.define("my-element", MyElement);
