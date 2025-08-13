/* static/js/main.js */

import { loadState, logout } from './state.js';
import { router } from './router.js';
import { apiRequest } from './api.js';
import { navigateTo } from './utils.js';
import { readBook } from './pages.js';

// --- EVENT HANDLERS ---
async function handleAppClick(e) {
    const target = e.target;
    const action = target.dataset.action;
    if (!action) return;

    e.preventDefault();

    const bookId = target.dataset.bookId;
    const categoryId = target.dataset.categoryId;
    const categoryName = target.dataset.categoryName;

    switch (action) {
        case 'read-book':
            readBook(bookId);
            break;
        case 'subscribe':
            navigateTo('#/subscribe');
            break;
        case 'login':
            navigateTo('#/login');
            break;
        case 'edit-book':
            navigateTo(`#/publisher/edit-book/${bookId}`);
            break;
        case 'add-bookmark':
            if (!state.isLoggedIn || state.user.type !== 'user') return;
            try {
                await apiRequest('/user/bookmarks/add', 'POST', { book_id: bookId });
                alert("Book added to bookmarks!");
            } catch(e) {/* handled */}
            break;
        case 'remove-bookmark':
            if (!state.isLoggedIn || state.user.type !== 'user') return;
            if (confirm("Are you sure you want to remove this bookmark?")) {
                try {
                    await apiRequest('/user/bookmarks/remove', 'POST', { book_id: bookId });
                    alert("Bookmark removed.");
                    router();
                } catch(e) {/* handled */}
            }
            break;
        case 'delete-book':
            if (!state.isLoggedIn || state.user.type !== 'publisher') return;
            if (confirm("Are you sure you want to delete this book? This cannot be undone.")) {
                try {
                    await apiRequest('/books/delete', 'POST', { book_id: bookId });
                    alert("Book deleted successfully.");
                    router();
                } catch(e) {/* handled */}
            }
            break;
        case 'subscribe-to-category':
            if (!state.isLoggedIn) {
                navigateTo('#/login');
                return;
            }
            if (confirm(`Subscribe to the "${categoryName}" category for 1 month?`)) {
                try {
                    await apiRequest('/user/subscribe', 'POST', { category_id: categoryId });

                    const expiryDate = new Date();
                    expiryDate.setDate(expiryDate.getDate() + 30);

                    if (!state.user.subscriptions) {
                        state.user.subscriptions = {};
                    }
                    state.user.subscriptions[categoryId] = expiryDate.toISOString().split('T')[0];
                    saveState();

                    alert('Subscription successful! Your access has been updated.');
                    router();
                } catch(e) {/* error handled in apiRequest */}
            }
            break;
    }
}

// --- INITIALIZATION ---
function init() {
    const app = document.getElementById('app');
    loadState();
    window.addEventListener('hashchange', router);
    window.addEventListener('load', router);
    app.addEventListener('click', handleAppClick);
    document.body.addEventListener('click', e => {
        if (e.target.id === 'logout-btn') {
            e.preventDefault();
            logout();
        }
    });
    router();
}

init();