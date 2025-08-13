/* static/js/state.js */

import { navigateTo } from './utils.js';

export const state = {
    isLoggedIn: false,
    token: null,
    user: null,
};

export function saveState() {
    localStorage.setItem('authState', JSON.stringify(state));
}

export function loadState() {
    const savedState = localStorage.getItem('authState');
    if (savedState) {
        Object.assign(state, JSON.parse(savedState));
    }
}

export function logout() {
    state.isLoggedIn = false;
    state.token = null;
    state.user = null;
    saveState();
    navigateTo('#/login');
}
