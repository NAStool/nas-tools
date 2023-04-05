import {html, LitElement, unsafeCSS, live, repeat, unsafeHTML} from "../utility/lit-core.min.js";
import Fuse from '../../js/modules/fuse.esm.min.js';
import hotkeys from '../../js/modules/hotkeys.esm.js';

import './cmd-action.js'; // eslint-disable-line import/no-unassigned-import
import style from './style.js';


export class CmdDialog extends LitElement {
    static styles = unsafeCSS(style);

    static properties = {
        theme: {attribute: "theme"},
        placeholder: {attribute: "placeholder"},
        note: {attribute: "note"},
        hotkey: {attribute: "hotkey"},
        actions: {attribute: "actions"},
        _search: {state: true},
        _selected: {state: true},
        _results: {state: true},
    };

    constructor() {
        super();
        this.theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        this.placeholder = '搜索...';
        this.note = '';
        this.hotkey = 'cmd+k,ctrl+k';
        this.actions = [];
        this._search = '';
        this._selected = null;
        this._results = [];
        this.fuse = null;
    }

    /**
     * Open the dialog.
     */
    open() {
        if (!this.dialog.open) {
            this.dialog.showModal();
        }
    }

    /**
     * Close the dialog.
     */
    close() {
        this.input.value = '';
        this.dialog.close();
    }

    connectedCallback() {
        super.connectedCallback();

        // Open dialog
        hotkeys(this.hotkey, event => {
            this.open();
            event.preventDefault();
        });

        // Select next
        hotkeys('down,tab', event => {
            if (this.dialog.open) {
                event.preventDefault();
                this._selected = this._selectedIndex >= this._results.length - 1 ? this._results[0] : this._results[this._selectedIndex + 1];
            }
        });

        // Select previous
        hotkeys('up,shift+tab', event => {
            if (this.dialog.open) {
                event.preventDefault();
                this._selected = this._selectedIndex === 0 ? this._results[this._results.length - 1] : this._results[this._selectedIndex - 1];
            }
        });

        // Trigger action
        hotkeys('enter', event => {
            if (this.dialog.open) {
                event.preventDefault();
                this._triggerAction(this._results[this._selectedIndex]);
            }
        });
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        // Unregister hotkeys
        hotkeys.unbind(this.hotkey);
        hotkeys.unbind('down,tab');
        hotkeys.unbind('up,shift+tab');
        hotkeys.unbind('enter');
    }

    update(changedProperties) {
        if (changedProperties.has('actions')) {
            // Register action hotkeys
            for (const action of this.actions.filter(item => Boolean(item.hotkey))) {
                hotkeys(action.hotkey ?? '', event => {
                    event.preventDefault();
                    this._triggerAction(action);
                });
            }

            // Setup fuse search
            this.fuse = new Fuse(this.actions,
                {
                    keys: [
                        {name: 'title', weight: 2},
                        {name: 'tags', weight: 1},
                        {name: 'url', weight: 1},
                    ],
                });
        }

        super.update(changedProperties);
    }

    render() {
        // Search for matches
        const results = this.fuse?.search(this._search);
        if (results) {
            this._results = results.map(item => item.item);
        }

        if (this._search.length > 0) {
            const results = this.fuse?.search(this._search);
            if (results) {
                this._results = results.map(item => item.item);
            }
        } else {
            this._results = this.actions;
        }

        // Select first result
        if (this._results.length > 0 && this._selectedIndex === -1) {
            this._selected = this._results[0];
        }

        // Nothing was found
        if (this._results.length === 0) {
            this._selected = undefined;
        }

        const actionList = html`
            <ul part="action-list">${repeat(
                    this._results,
                    action =>
                            html`
                                <cmd-action
                                        .action=${action}
                                        .selected=${live(action === this._selected)}
                                        .theme=${this.theme}
                                        @mouseover=${(event) => {
                                            this._actionFocused(action, event);
                                        }}
                                        @actionSelected=${(event) => {
                                            this._triggerAction(event.detail);
                                        }}
                                ></cmd-action>
                            `)}
            </ul>
        `;

        return html`
            <dialog
                    part="dialog"
                    class="${this.theme}"
                    @close="${this.close}"
                    @click="${(event) => {
                        if (event.target === this.dialog) {
                            this.close();
                        } // Close on backdrop click
                    }}">
                <!-- Header -->
                <form part="dialog-form">
                    <input
                            part="input"
                            type="text"
                            spellcheck="false"
                            autocomplete="off"
                            @input="${this._onInput}"
                            placeholder="${this.placeholder}"
                            autofocus
                    >
                </form>
                <!-- Action list -->
                <main part="dialog-body">${actionList}</main>
                <!-- Footer -->
                <slot name="footer">
                    <p><kbd part="kbd">⏎</kbd> 确定 <kbd part="kbd">↑</kbd> <kbd part="kbd">↓</kbd> 选择 <kbd part="kbd">esc</kbd> 关闭</p>
                    ${unsafeHTML(this.note ?? `<span>${this._results.length} options</span>`)}
                </slot>
            </dialog>
        `;
    }

    /**
     * Render the results on input.
     * @param event
     * @private
     */
    async _onInput(event) {
        const input = event.target;
        this._search = input.value;
        await this.updateComplete;

        this.dispatchEvent(
            new CustomEvent(
                'change', {
                    detail: {
                        search: input.value,
                        actions: this._results,
                    },
                    bubbles: true,
                    composed: true,
                }),
        );
    }

    /**
     * Handle focus on action.
     * @param action
     * @param $event
     * @private
     */
    _actionFocused(action, $event) {
        this._selected = action;
        ($event.target).ensureInView();
    }

    /**
     * Trigger the action.
     * @param action
     * @private
     */
    _triggerAction(action) {
        this._selected = action;

        // Fire selected event even when action is empty/not selected,
        // so possible handle api search for example
        this.dispatchEvent(
            new CustomEvent('selected', {
                detail: {search: this._search, action},
                bubbles: true,
                composed: true,
            }),
        );

        // Trigger action
        if (action) {
            if (action.onAction) {
                const result = action.onAction(action);
                if (!result?.keepOpen) {
                    this.close();
                }
            } else if (action.url) {
                window.open(action.url, action.target ?? '_self');
                this.close();
            }
        }
    }

    /**
     * Return the index of the selected action.
     * @private
     */
    get _selectedIndex() {
        return this._selected ? this._results.indexOf(this._selected) : -1;
    }

    /**
     * Return the dialog element.
     */
    get dialog() {
        return this.shadowRoot?.querySelector('dialog');
    }

    /**
     * Return the input element.
     */
    get input() {
        return this.shadowRoot?.querySelector('input');
    }
}


window.customElements.define("cmd-dialog", CmdDialog);