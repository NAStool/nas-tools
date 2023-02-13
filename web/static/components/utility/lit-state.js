export const observeState = superclass => class extends superclass {

    constructor() {
        super();
        this._observers = [];
    }

    update(changedProperties) {
        stateRecorder.start();
        super.update(changedProperties);
        this._initStateObservers();
    }

    connectedCallback() {
        super.connectedCallback();
        if (this._wasConnected) {
            this.requestUpdate();
            delete this._wasConnected;
        }
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        this._wasConnected = true;
        this._clearStateObservers();
    }

    _initStateObservers() {
        this._clearStateObservers();
        if (!this.isConnected) return;
        this._addStateObservers(stateRecorder.finish());
    }

    _addStateObservers(stateVars) {
        for (let [state, keys] of stateVars) {
            const observer = () => this.requestUpdate();
            this._observers.push([state, observer]);
            state.addObserver(observer, keys);
        }
    }

    _clearStateObservers() {
        for (let [state, observer] of this._observers) {
            state.removeObserver(observer);
        }
        this._observers = [];
    }

}


export class LitState {

    constructor() {
        this._observers = [];
        this._initStateVars();
    }

    addObserver(observer, keys) {
        this._observers.push({observer, keys});
    }

    removeObserver(observer) {
        this._observers = this._observers.filter(observerObj => observerObj.observer !== observer);
    }

    _initStateVars() {

        if (this.constructor.stateVarOptions) {
            for (let [key, options] of Object.entries(this.constructor.stateVarOptions)) {
                this._initStateVar(key, options);
            }
        }

        if (this.constructor.stateVars) {
            for (let [key, value] of Object.entries(this.constructor.stateVars)) {
                this._initStateVar(key, {});
                this[key] = value;
            }
        }

    }

    _initStateVar(key, options) {

        if (this.hasOwnProperty(key)) {
            // Property already defined, so don't re-define.
            return;
        }

        options = this._parseOptions(options);

        const stateVar = new options.handler({
            options: options,
            recordRead: () => this._recordRead(key),
            notifyChange: () => this._notifyChange(key)
        });

        Object.defineProperty(
            this,
            key,
            {
                get() {
                    return stateVar.get();
                },
                set(value) {
                    if (stateVar.shouldSetValue(value)) {
                        stateVar.set(value);
                    }
                },
                configurable: true,
                enumerable: true
            }
        );

    }

    _parseOptions(options) {

        if (!options.handler) {
            options.handler = StateVar;
        } else {

            // In case of a custom `StateVar` handler is provided, we offer a
            // second way of providing options to your custom handler class.
            //
            // You can decorate a *method* with `@stateVar()` instead of a
            // variable. The method must return an object, and that object will
            // be assigned to the `options` object.
            //
            // Within the method you have access to the `this` context. So you
            // can access other properties and methods from your state class.
            // And you can add arrow function callbacks where you can access
            // `this`. This provides a lot of possibilities for a custom
            // handler class.
            if (options.propertyMethod && options.propertyMethod.kind === 'method') {
                Object.assign(options, options.propertyMethod.descriptor.value.call(this));
            }

        }

        return options;

    }

    _recordRead(key) {
        stateRecorder.recordRead(this, key);
    }

    _notifyChange(key) {
        for (const observerObj of this._observers) {
            if (!observerObj.keys || observerObj.keys.includes(key)) {
                observerObj.observer(key);
            }
        };
    }

}


export class StateVar {

    constructor(args) {
        this.options = args.options; // The options given in the `stateVar` declaration
        this.recordRead = args.recordRead; // Callback to indicate the `stateVar` is read
        this.notifyChange = args.notifyChange; // Callback to indicate the `stateVar` value has changed
        this.value = undefined; // The initial value
    }

    // Called when the `stateVar` on the `LitState` class is read (for example:
    // `myState.myStateVar`). Should return the value of the `stateVar`.
    get() {
        this.recordRead();
        return this.value;
    }

    // Called before the `set()` method is called. If this method returns
    // `false`, the `set()` method won't be called. This can be used for
    // validation and/or optimization.
    shouldSetValue(value) {
        return this.value !== value;
    }

    // Called when the `stateVar` on the `LitState` class is set (for example:
    // `myState.myStateVar = 'value'`.
    set(value) {
        this.value = value;
        this.notifyChange();
    }

}


export function stateVar(options = {}) {

    return element => {

        return {
            kind: 'field',
            key: Symbol(),
            placement: 'own',
            descriptor: {},
            initializer() {
                if (typeof element.initializer === 'function') {
                    this[element.key] = element.initializer.call(this);
                }
            },
            finisher(litStateClass) {

                if (element.kind === 'method') {
                    // You can decorate a *method* with `@stateVar()` instead
                    // of a variable. When the state class is constructed, this
                    // method will be called, and it's return value must be an
                    // object that will be added to the options the stateVar
                    // handler will receive.
                    options.propertyMethod = element;
                }

                if (litStateClass.stateVarOptions === undefined) {
                    litStateClass.stateVarOptions = {};
                }

                litStateClass.stateVarOptions[element.key] = options;

            }
        };

    };

}


class StateRecorder {

    constructor() {
        this._log = null;
    }

    start() {
        this._log = new Map();
    }

    recordRead(stateObj, key) {
        if (this._log === null) return;
        const keys = this._log.get(stateObj) || [];
        if (!keys.includes(key)) keys.push(key);
        this._log.set(stateObj, keys);
    }

    finish() {
        const stateVars = this._log;
        this._log = null;
        return stateVars;
    }

}

export const stateRecorder = new StateRecorder();