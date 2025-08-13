/* static/js/router.js */

import * as pages from './pages.js';

const routes = {
    '/': pages.renderLandingPage,
    '/books': pages.renderBooksPage,
    '/subscribe': pages.renderSubscribePage,
    '/login': pages.renderLoginPage,
    '/register': pages.renderRegisterPage,
    '/dashboard': pages.renderBooksPage,
    '/profile': pages.renderProfilePage,
    '/bookmarks': pages.renderBookmarksPage,
    '/history': pages.renderHistoryPage,
    '/publisher/dashboard': pages.renderPublisherDashboard,
    '/publisher/add-book': () => pages.renderAddOrEditBookPage(),
    '/publisher/edit-book/:id': (id) => pages.renderAddOrEditBookPage(id),
};

export function router() {
    const app = document.getElementById('app');
    app.innerHTML = '';
    const path = window.location.hash.slice(1) || '/';

    const paramRoute = Object.keys(routes).find(r => {
        const routeRegex = new RegExp(`^${r.replace(':id', '(\\d+)')}$`);
        return routeRegex.test(path);
    });

    if (paramRoute) {
        const routeRegex = new RegExp(`^${paramRoute.replace(':id', '(\\d+)')}$`);
        const match = path.match(routeRegex);
        const param = match[1];
        routes[paramRoute](param);
    } else if (routes[path]) {
        routes[path]();
    } else {
        pages.renderLandingPage();
    }
}
