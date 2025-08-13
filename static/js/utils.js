/* static/js/utils.js */

export function displayError(message) {
    const app = document.getElementById('app');
    if (!app) return;

    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;

    if (app.firstChild) {
        app.insertBefore(errorDiv, app.firstChild);
    } else {
        app.appendChild(errorDiv);
    }

    setTimeout(() => errorDiv.remove(), 5000);
}

export function navigateTo(hash) {
    window.location.hash = hash;
}
