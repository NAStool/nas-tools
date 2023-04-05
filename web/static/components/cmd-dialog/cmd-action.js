import {classMap, html, LitElement, nothing, repeat, unsafeCSS, unsafeHTML} from "../utility/lit-core.min.js";
import style from './style.js';

export class CmdAction extends LitElement {

    static styles = unsafeCSS(style);

    static properties = {
        theme: {attribute: "theme"},
        action: {attribute: "action"},
        selected: {attribute: "selected "},
    };

    constructor() {
        super();
        this.selected = false
        this.theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        this.addEventListener('click', this.click);
    }

    /**
     * Scroll to show element
     */
    ensureInView() {
        requestAnimationFrame(() => {
            this.scrollIntoView({block: 'nearest'});
        });
    }

    /**
     * Click event
     */
    click() {
        this.dispatchEvent(
            new CustomEvent('actionSelected', {
                detail: this.action,
                bubbles: true,
                composed: true,
            }),
        );
    }

    /**
     * Updated
     * @param changedProperties
     */
    updated(changedProperties) {
        if (changedProperties.has('selected') && this.selected) {
            this.ensureInView();
        }
    }

    render() {
        const classes = {
            selected: this.selected,
            dark: this.theme === 'dark',
        };

        return html`
            <li class=${classMap(classes)} part="action ${this.selected ? 'selected' : ''}">
                ${this.img}
                <strong part="title">
                    ${this.action.title}
                    ${this.description}
                </strong>
                ${this.hotkeys}
            </li>
        `;
    }

    /**
     * Get hotkeys
     * @private
     */
    get hotkeys() {
        if (this.action?.hotkey) {
            const hotkeys = this.action.hotkey
                .replace('cmd', '⌘')
                .replace('shift', '⇧')
                .replace('alt', '⌥')
                .replace('ctrl', '⌃')
                .toUpperCase()
                .split('+');
            return hotkeys.length > 0 ? html`<span>${repeat(hotkeys, hotkey => html`<kbd
                    part="kbd">${hotkey}</kbd>`)}</span>` : '';
        }

        return nothing;
    }

    /**
     * Get description
     * @private
     */
    get description() {
        return this.action.description ? html`<small part="description">${this.action.description}</small>` : nothing;
    }

    /**
     * Get icon
     * @private
     */
    get img() {
        return this.action.img ? html`<span>${unsafeHTML(this.action.img)}</span>` : nothing;
    }
}

window.customElements.define("cmd-action", CmdAction);