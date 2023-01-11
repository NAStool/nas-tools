// import { LitElement } from "./lit-all.min.js";

export const NoShadowdom = (superClass) => class extends superClass{
    createRenderRoot() {
        return this;
    }
}

