/* static/js/admin.js */

const API_BASE_URL = 'http://localhost:8001/api/admin';
const app = document.getElementById('admin-app');

const state = {
    isLoggedIn: false,
    token: null,
    admin: null // { name, email }
};

// --- API HELPER (MODIFIED TO HANDLE EXPIRED SESSIONS) ---
async function apiRequest(endpoint, method = 'GET', body = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    const config = { method, headers };
    if (body) {
        config.body = JSON.stringify(body);
    }
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
        if (!response.ok) {
            if (response.status === 401) {
                logout(); 
                throw new Error('Session expired');
            }
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        return response.status === 204 ? null : await response.json();
    } catch (error) {
        if (error.message !== 'Session expired') {
            alert(`API Error: ${error.message}`);
        }
        throw error;
    }
}

// --- STATE & NAVIGATION ---
function saveState() { localStorage.setItem('adminAuthState', JSON.stringify(state)); }
function loadState() {
    const saved = localStorage.getItem('adminAuthState');
    if (saved) Object.assign(state, JSON.parse(saved));
}
function logout() {
    Object.assign(state, { isLoggedIn: false, token: null, admin: null });
    saveState();
    router();
}
function navigateTo(hash) { window.location.hash = hash; }

// --- RENDER FUNCTIONS ---
function renderLayout(content) {
    if (!state.isLoggedIn) {
        app.innerHTML = renderLoginPage();
        addLoginListener();
        return;
    }
    app.innerHTML = `
        <aside class="sidebar">
            <h2>Admin Panel</h2>
            <a href="#/dashboard">Dashboard</a>
            <a href="#/users">Manage Users</a>
            <a href="#/publishers">Manage Publishers</a>
            <a href="#/books">Manage Books</a>
            <a href="#/categories">Manage Categories</a>
            <a href="#" id="logout-btn" class="logout-btn">Logout (${state.admin.name})</a>
        </aside>
        <main class="main-content">${content}</main>
    `;
    document.getElementById('logout-btn').addEventListener('click', logout);
}

function renderLoginPage() {
    return `<div class="form-container"><h2>Admin Login</h2><form id="login-form"><div class="form-group"><label for="email">Email</label><input type="email" id="email" required></div><div class="form-group"><label for="password">Password</label><input type="password" id="password" required></div><button type="submit" class="btn btn-secondary">Login</button></form></div>`;
}

async function renderDashboard() {
    try {
        const [users, publishers, books] = await Promise.all([
            apiRequest('/users'),
            apiRequest('/publishers'),
            apiRequest('/books')
        ]);
        renderLayout(`<h1>Dashboard</h1><h3>At a Glance:</h3><ul><li>Total Users: ${users.length}</li><li>Total Publishers: ${publishers.length}</li><li>Total Books: ${books.length}</li></ul>`);
    } catch (error) {
        console.error("Failed to load dashboard data, likely due to session expiry.");
    }
}

async function renderUsersPage() {
    try {
        const users = await apiRequest('/users');
        const userRows = users.map(u => `
            <tr>
                <td>${u.user_id}</td>
                <td>${u.name}</td>
                <td>${u.email}</td>
                <td style="max-width: 300px;">${u.active_subscriptions || 'None'}</td>
                <td>
                    <button class="btn btn-secondary" data-action="edit-user" data-user-id="${u.user_id}">Edit</button>
                    <button class="btn btn-secondary" data-action="manage-subs" data-user-id="${u.user_id}">Manage Subs</button>
                    <button class="btn btn-danger" data-action="delete-user" data-user-id="${u.user_id}" data-user-name="${u.name}">Delete</button>
                </td>
            </tr>
        `).join('');
        renderLayout(`<h1>Manage Users</h1><div class="table-container"><table><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Active Subscriptions</th><th>Actions</th></tr></thead><tbody>${userRows}</tbody></table></div>`);
    } catch (error) {
        console.error("Failed to load users page.");
    }
}

async function renderPublishersPage() {
    try {
        const publishers = await apiRequest('/publishers');
        const pubRows = publishers.map(p => `
            <tr>
                <td>${p.publisher_id}</td>
                <td>${p.name}</td>
                <td>${p.email}</td>
                <td>
                    <button class="btn btn-secondary" data-action="edit-publisher" data-publisher-id="${p.publisher_id}">Edit</button>
                    <button class="btn btn-danger" data-action="delete-publisher" data-publisher-id="${p.publisher_id}" data-publisher-name="${p.name}">Delete</button>
                </td>
            </tr>
        `).join('');
        renderLayout(`<h1>Manage Publishers</h1><div class="table-container"><table><thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Actions</th></tr></thead><tbody>${pubRows}</tbody></table></div>`);
    } catch (error) {
        console.error("Failed to load publishers page.");
    }
}
async function renderBooksPage() {
    try {
        const books = await apiRequest('/books');
        const bookRows = books.map(b => `<tr><td>${b.book_id}</td><td>${b.name}</td><td>${b.author_name}</td><td>${b.publisher_name}</td><td>${b.category_name || 'N/A'}</td><td><button class="btn btn-danger" data-action="delete-book" data-book-id="${b.book_id}" data-book-name="${b.name}">Delete</button></td></tr>`).join('');
        renderLayout(`<h1>Manage Books</h1><div class="table-container"><table><thead><tr><th>ID</th><th>Title</th><th>Author</th><th>Publisher</th><th>Category</th><th>Actions</th></tr></thead><tbody>${bookRows}</tbody></table></div>`);
    } catch (error) {
        console.error("Failed to load books page.");
    }
}

async function renderCategoriesPage() {
    try {
        const categories = await apiRequest('/categories');
        const catRows = categories.map(c => `<tr><td>${c.category_id}</td><td>${c.category_name}</td><td><button class="btn btn-danger" data-action="delete-category" data-category-id="${c.category_id}" data-category-name="${c.category_name}">Delete</button></td></tr>`).join('');
        renderLayout(`<h1>Manage Categories</h1><div class="form-container" style="max-width: none; margin-bottom: 2rem;"><h3>Add New Category</h3><form id="add-category-form"><div class="form-group"><label for="category-name">Category Name</label><input type="text" id="category-name" required></div><button type="submit" class="btn btn-secondary">Add Category</button></form></div><div class="table-container"><table><thead><tr><th>ID</th><th>Name</th><th>Actions</th></tr></thead><tbody>${catRows}</tbody></table></div>`);
        document.getElementById('add-category-form').addEventListener('submit', async e => {
            e.preventDefault();
            const name = e.target.elements['category-name'].value;
            try {
                await apiRequest('/categories/add', 'POST', { name });
                router();
            } catch (error) { /* handled */ }
        });
    } catch (error) {
        console.error("Failed to load categories page.");
    }
}

async function renderEditUserPage(userId) {
    try {
        const user = await apiRequest(`/users/${userId}`);
        const content = `
            <div class="form-container">
                <h2>Edit User: ${user.name}</h2>
                <form id="edit-user-form">
                    <input type="hidden" id="user_id" value="${user.user_id}">
                    <div class="form-group">
                        <label for="email">Email (read-only)</label>
                        <input type="email" id="email" value="${user.email}" disabled>
                    </div>
                    <div class="form-group">
                        <label for="name">Name</label>
                        <input type="text" id="name" value="${user.name}" required>
                    </div>
                    <div class="form-group">
                        <label for="phone">Phone</label>
                        <input type="tel" id="phone" value="${user.phone || ''}">
                    </div>
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                    <a href="#/users" class="btn btn-secondary">Cancel</a>
                </form>
            </div>
        `;
        renderLayout(content);
        document.getElementById('edit-user-form').addEventListener('submit', async e => {
            e.preventDefault();
            const body = {
                user_id: parseInt(e.target.elements.user_id.value),
                name: e.target.elements.name.value,
                phone: e.target.elements.phone.value
            };
            await apiRequest('/users/update', 'POST', body);
            alert('User updated successfully!');
            navigateTo('#/users');
        });
    } catch(error) { console.error("Failed to load edit user page.")}
}

async function renderEditPublisherPage(pubId) {
    try {
        const pub = await apiRequest(`/publishers/${pubId}`);
        const content = `
            <div class="form-container">
                <h2>Edit Publisher: ${pub.name}</h2>
                <form id="edit-pub-form">
                    <input type="hidden" id="publisher_id" value="${pub.publisher_id}">
                    <div class="form-group"><label>Email (read-only)</label><input type="email" value="${pub.email}" disabled></div>
                    <div class="form-group"><label for="name">Name</label><input type="text" id="name" value="${pub.name}" required></div>
                    <div class="form-group"><label for="phone">Phone</label><input type="tel" id="phone" value="${pub.phone || ''}"></div>
                    <div class="form-group"><label for="address">Address</label><input type="text" id="address" value="${pub.address || ''}"></div>
                    <div class="form-group"><label for="description">Description</label><textarea id="description">${pub.description || ''}</textarea></div>
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                    <a href="#/publishers" class="btn btn-secondary">Cancel</a>
                </form>
            </div>
        `;
        renderLayout(content);
        document.getElementById('edit-pub-form').addEventListener('submit', async e => {
            e.preventDefault();
            const body = {
                publisher_id: parseInt(e.target.elements.publisher_id.value),
                name: e.target.elements.name.value,
                phone: e.target.elements.phone.value,
                address: e.target.elements.address.value,
                description: e.target.elements.description.value,
            };
            await apiRequest('/publishers/update', 'POST', body);
            alert('Publisher updated successfully!');
            navigateTo('#/publishers');
        });
    } catch(error) { console.error("Failed to load edit publisher page.")}
}

async function renderManageUserSubscriptionsPage(userId) {
    try {
        const [allCategories, allUsers] = await Promise.all([apiRequest('/categories'), apiRequest('/users')]);
        const user = allUsers.find(u => u.user_id == userId);
        const activeSubs = user.active_subscriptions ? user.active_subscriptions.split(', ') : [];

        const categoryRows = allCategories.map(cat => {
            const isSubscribed = activeSubs.includes(cat.category_name);
            const actionButton = isSubscribed
                ? `<button class="btn btn-danger" data-action="remove-subscription" data-user-id="${userId}" data-category-id="${cat.category_id}">Remove</button>`
                : `<button class="btn btn-secondary" data-action="add-subscription" data-user-id="${userId}" data-category-id="${cat.category_id}">Add (30 days)</button>`;
            return `<tr><td>${cat.category_name}</td><td>${isSubscribed ? 'Yes' : 'No'}</td><td>${actionButton}</td></tr>`;
        }).join('');

        const content = `
            <h1>Manage Subscriptions for ${user.name}</h1>
            <a href="#/users" style="margin-bottom: 1rem; display: inline-block;">&larr; Back to Users</a>
            <div class="table-container"><table><thead><tr><th>Category</th><th>Subscribed?</th><th>Action</th></tr></thead><tbody>${categoryRows}</tbody></table></div>
        `;
        renderLayout(content);
    } catch(error) { console.error("Failed to load manage subscriptions page.")}
}


// --- EVENT HANDLERS & ACTIONS ---
function addLoginListener() {
    const form = document.getElementById('login-form');
    if (!form) return;
    form.addEventListener('submit', async e => {
        e.preventDefault();
        const email = e.target.email.value;
        const password = e.target.password.value;
        try {
            const data = await apiRequest('/login', 'POST', { email, password });
            state.isLoggedIn = true;
            state.token = data.session_token;
            state.admin = { name: data.name, email: data.email };
            saveState();
            navigateTo('#/dashboard');
        } catch (error) { /* handled */ }
    });
}

async function handleAdminClick(e) {
    const target = e.target.closest('button');
    if (!target) return;

    const action = target.dataset.action;
    if (!action) return;

    const userId = target.dataset.userId;
    const userName = target.dataset.userName;
    const pubId = target.dataset.publisherId;
    const pubName = target.dataset.publisherName;
    const bookId = target.dataset.bookId;
    const bookName = target.dataset.bookName;
    const catId = target.dataset.categoryId;
    const catName = target.dataset.categoryName;

    switch (action) {
        case 'edit-user':
            navigateTo(`#/users/edit/${userId}`);
            break;
        case 'manage-subs':
            navigateTo(`#/users/subs/${userId}`);
            break;
        case 'delete-user':
            if (confirm(`Are you sure you want to delete user: ${userName}? This is irreversible.`)) {
                await apiRequest('/users/delete', 'POST', { user_id: userId });
                router();
            }
            break;
        case 'edit-publisher':
            navigateTo(`#/publishers/edit/${pubId}`);
            break;
        case 'delete-publisher':
            if (confirm(`Delete publisher ${pubName}? This will also delete ALL their books.`)) {
                await apiRequest('/publishers/delete', 'POST', { publisher_id: pubId });
                router();
            }
            break;
        case 'delete-book':
            if (confirm(`Delete book: ${bookName}?`)) {
                await apiRequest('/books/delete', 'POST', { book_id: bookId });
                router();
            }
            break;
        case 'delete-category':
            if (confirm(`Delete category "${catName}"? If any book is using this category, deletion will fail.`)) {
                try {
                    await apiRequest('/categories/delete', 'POST', { category_id: catId });
                    router();
                } catch (e) { /* handled */ }
            }
            break;
        case 'add-subscription':
            await apiRequest('/users/add_subscription', 'POST', { user_id: userId, category_id: catId });
            renderManageUserSubscriptionsPage(userId);
            break;
        case 'remove-subscription':
            await apiRequest('/users/remove_subscription', 'POST', { user_id: userId, category_id: catId });
            renderManageUserSubscriptionsPage(userId);
            break;
    }
}


// --- ROUTER ---
const routes = {
    '/': renderDashboard,
    '/dashboard': renderDashboard,
    '/users': renderUsersPage,
    '/users/edit/:id': (id) => renderEditUserPage(id),
    '/users/subs/:id': (id) => renderManageUserSubscriptionsPage(id),
    '/publishers': renderPublishersPage,
    '/publishers/edit/:id': (id) => renderEditPublisherPage(id),
    '/books': renderBooksPage,
    '/categories': renderCategoriesPage,
};
function router() {
    const path = window.location.hash.slice(1) || '/';
    if (!state.isLoggedIn) {
        renderLayout(''); 
        return;
    }
    
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
        renderDashboard();
    }
}

// --- INITIALIZATION ---
function init() {
    loadState();
    window.addEventListener('hashchange', router);
    window.addEventListener('load', router);
    app.addEventListener('click', handleAdminClick);
    router();
}
init();