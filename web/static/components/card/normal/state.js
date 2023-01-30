import { LitState } from "../../utility/lit-state.js"

class CardState extends LitState {
    static get stateVars() {
        return {
            more_id: undefined
        };
    }
}

export const cardState = new CardState();