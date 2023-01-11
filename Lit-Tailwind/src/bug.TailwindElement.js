import { LitElement, adoptStyles, unsafeCSS } from 'lit';
import style from './tailwind.css' 

const stylesheet = unsafeCSS(style)
export class TailwindElement extends LitElement {
  connectedCallback() {
    super.connectedCallback();
    adoptStyles(this.shadowRoot, [stylesheet])
  }
};
