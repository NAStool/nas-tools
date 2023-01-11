import { LitElement, html } from "../lit-all.min.js";
import { NoShadowdom } from "../no-shadowdom-mixin.js";

export class NormalCardPlaceholder extends NoShadowdom(LitElement) {
    render() {
        return html`
        <div class="card card-sm rounded-4" style="overflow: hidden;">
            <div class="placeholder-glow">
            <div class="ratio placeholder rounded-4" style="--tblr-aspect-ratio:150%;"></div>
            </div>
        </div>
        `;
    }
}

window.customElements.define("normal-card-placeholder", NormalCardPlaceholder);