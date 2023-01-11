// import { LitElement } from "./lit-all.min.js";

export const noShadowdom = (superClass) => class extends superClass{
    createRenderRoot() {
        return this;
    }
}

