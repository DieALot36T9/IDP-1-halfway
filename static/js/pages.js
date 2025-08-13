/* static/js/pages.js */

import { apiRequest } from './api.js';
import { state, saveState } from './state.js';
import { navigateTo, displayError } from './utils.js';
import { renderNavbar, renderBookGrid } from './components.js';
import * as pdfjsLib from '/static/js/pdfjs/build/pdf.mjs';

const app = document.getElementById('app');

export function renderLandingPage() {
    app.innerHTML = `
        ${renderNavbar()}
        <main class="landing-page">
            <div class="hero-section">
                <h1>Unlock Your Potential</h1>
                <p>Your ultimate resource for job preparation and competitive exams.</p>
                <a href="#/books" class="btn btn-primary btn-large">Browse All Books</a>
                <a href="#/subscribe" class="btn btn-secondary btn-large">View Subscriptions</a>
            </div>
        </main>
    `;
}

export async function renderBooksPage() {
    app.innerHTML = `
        ${renderNavbar()}
        <main>
            <h1 class="text-center">Browse Books</h1>
            <div id="search-bar" class="form-container" style="max-width: 700px;">
                <div class="form-group"><input type="search" id="search-input" placeholder="Search for books or authors..."></div>
            </div>
            <div id="category-filters" class="text-center category-filters">
                <p>Loading categories...</p>
            </div>
            <div id="book-list-container">
                <p class="text-center">Loading books...</p>
            </div>
        </main>
    `;
    
    const bookListContainer = document.getElementById('book-list-container');
    const searchInput = document.getElementById('search-input');
    const categoryFiltersContainer = document.getElementById('category-filters');

    const loadBooks = async (categoryId = null, searchTerm = '') => {
        bookListContainer.innerHTML = `<p class="text-center">Loading books...</p>`;
        let url = '/books?';
        if (categoryId) url += `category_id=${categoryId}&`;
        if (searchTerm) url += `search=${encodeURIComponent(searchTerm)}`;
        
        const books = await apiRequest(url);
        bookListContainer.innerHTML = renderBookGrid(books);
    };

    searchInput.addEventListener('input', (e) => {
        const activeCategoryBtn = document.querySelector('.btn-category.active');
        const categoryId = activeCategoryBtn ? activeCategoryBtn.dataset.categoryId : null;
        loadBooks(categoryId, e.target.value);
    });

    const categories = await apiRequest('/categories');
    let filterButtonsHTML = `<button class="btn btn-category active" data-category-id="">All</button>`;
    filterButtonsHTML += categories.map(cat => `<button class="btn btn-category" data-category-id="${cat.category_id}">${cat.category_name}</button>`).join('');
    categoryFiltersContainer.innerHTML = filterButtonsHTML;
    
    categoryFiltersContainer.addEventListener('click', e => {
        if (e.target.classList.contains('btn-category')) {
            document.querySelector('.btn-category.active').classList.remove('active');
            e.target.classList.add('active');
            const categoryId = e.target.dataset.categoryId;
            loadBooks(categoryId, searchInput.value);
        }
    });
    loadBooks();
}

export async function renderSubscribePage() {
    if (!state.isLoggedIn) { navigateTo('#/login'); return; }
    app.innerHTML = `${renderNavbar()}<main>
        <h1 class="text-center">Subscribe to Categories</h1>
        <p class="text-center">Gain access to all books in a category for one month.</p>
        <div id="subscription-list-container" class="subscription-grid">Loading...</div>
    </main>`;

    const categories = await apiRequest('/categories');
    const subListContainer = document.getElementById('subscription-list-container');

    if (!categories || categories.length === 0) {
        subListContainer.innerHTML = `<p class="text-center">No categories available to subscribe to.</p>`;
        return;
    }

    subListContainer.innerHTML = categories.map(cat => {
        const isSubscribed = state.user.subscriptions && state.user.subscriptions[cat.category_id];
        let buttonHTML = `<button class="btn btn-primary" data-action="subscribe-to-category" data-category-id="${cat.category_id}" data-category-name="${cat.category_name}">Subscribe (1 Month)</button>`;
        if (isSubscribed) {
            const expiry = new Date(state.user.subscriptions[cat.category_id]).toLocaleDateString();
            buttonHTML = `<p><strong>Subscribed!</strong></p><p>Expires on: ${expiry}</p><button class="btn btn-secondary" data-action="subscribe-to-category" data-category-id="${cat.category_id}" data-category-name="${cat.category_name}">Renew (1 Month)</button>`;
        }
        return `
            <div class="subscription-card">
                <h3>${cat.category_name}</h3>
                <div class="subscription-card-actions">${buttonHTML}</div>
            </div>
        `;
    }).join('');
}

export function renderLoginPage() {
    app.innerHTML = `${renderNavbar()}<main><div class="form-container"><h2>Login</h2><form id="login-form"><div class="form-group"><label for="email">Email</label><input type="email" id="email" required></div><div class="form-group"><label for="password">Password</label><input type="password" id="password" required></div><button type="submit" class="btn btn-primary">Login</button></form><p class="text-center" style="margin-top: 1rem;">Don't have an account? <a href="#/register">Register here</a></p></div></main>`;
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        try {
            const data = await apiRequest('/login', 'POST', { email, password });
            state.isLoggedIn = true;
            state.token = data.session_token;
            state.user = { 
                name: data.name, email: data.email, type: data.type, 
                publisher_id: data.publisher_id, user_id: data.user_id,
                subscriptions: data.subscriptions || {}
            };
            saveState();
            navigateTo(data.type === 'user' ? '#/books' : '#/publisher/dashboard');
        } catch (error) { /* Handled */ }
    });
}

export function renderRegisterPage() {
    app.innerHTML = `${renderNavbar()}<main><div class="form-container"><h2>Register</h2><div style="display: flex; justify-content: center; gap: 1rem; margin-bottom: 1rem;"><button class="btn btn-secondary" id="show-user-reg">As a User</button><button class="btn btn-secondary" id="show-pub-reg">As a Publisher</button></div><div id="registration-form-container"></div></div></main>`;
    const renderUserForm = () => {
        document.getElementById('registration-form-container').innerHTML = `<form id="user-register-form"><h3>User Registration</h3><div class="form-group"><label for="name">Name</label><input type="text" id="name" required></div><div class="form-group"><label for="email">Email</label><input type="email" id="email" required></div><div class="form-group"><label for="phone">Phone</label><input type="tel" id="phone"></div><div class="form-group"><label for="password">Password</label><input type="password" id="password" required></div><button type="submit" class="btn btn-primary">Register</button></form>`;
        document.getElementById('user-register-form').addEventListener('submit', async e => {
            e.preventDefault();
            const body = { name: e.target.elements.name.value, email: e.target.elements.email.value, phone: e.target.elements.phone.value, password: e.target.elements.password.value, };
            await apiRequest('/user/register', 'POST', body);
            alert('Registration successful! Please login.');
            navigateTo('#/login');
        });
    };
    const renderPublisherForm = () => {
        document.getElementById('registration-form-container').innerHTML = `
            <form id="pub-register-form">
                <h3>Publisher Registration</h3>
                <div class="form-group"><label for="name">Publisher Name</label><input type="text" id="name" required></div>
                <div class="form-group"><label for="email">Email</label><input type="email" id="email" required></div>
                <div class="form-group"><label for="phone">Phone</label><input type="tel" id="phone"></div>
                <div class="form-group"><label for="address">Address</label><input type="text" id="address"></div>
                <div class="form-group"><label for="description">Description</label><textarea id="description"></textarea></div>
                <div class="form-group"><label for="image">Publisher Image/Logo</label><input type="file" id="image" accept="image/*"></div>
                <div class="form-group"><label for="password">Password</label><input type="password" id="password" required></div>
                <button type="submit" class="btn btn-primary">Register</button>
            </form>
        `;
        document.getElementById('pub-register-form').addEventListener('submit', async e => {
            e.preventDefault();
            const formData = new FormData();
            formData.append('name', e.target.elements.name.value);
            formData.append('email', e.target.elements.email.value);
            formData.append('phone', e.target.elements.phone.value);
            formData.append('address', e.target.elements.address.value);
            formData.append('description', e.target.elements.description.value);
            formData.append('password', e.target.elements.password.value);
            if (e.target.elements.image.files[0]) {
                formData.append('image', e.target.elements.image.files[0]);
            }
            await apiRequest('/publisher/register', 'POST', formData, true);
            alert('Registration successful! Please login.');
            navigateTo('#/login');
        });
    };
    document.getElementById('show-user-reg').addEventListener('click', renderUserForm);
    document.getElementById('show-pub-reg').addEventListener('click', renderPublisherForm);
    renderUserForm();
}

export async function renderProfilePage() {
    if (!state.isLoggedIn || state.user.type !== 'user') { navigateTo('#/login'); return; }
    
    const allCategories = await apiRequest('/categories');
    const categoryMap = Object.fromEntries(allCategories.map(c => [c.category_id, c.category_name]));

    const user = state.user;
    const subscriptionItems = Object.entries(user.subscriptions || {}).map(([catId, expiry]) => 
        `<li><strong>${categoryMap[catId] || 'Unknown Category'}</strong>: Expires on ${new Date(expiry).toLocaleDateString()}</li>`
    ).join('');

    app.innerHTML = `
        ${renderNavbar()}
        <main>
            <div class="form-container"><h2>My Profile</h2><form id="profile-form"><div class="form-group"><label for="name">Name</label><input type="text" id="name" value="${user.name}" required></div><div class="form-group"><label for="email">Email (cannot be changed)</label><input type="email" id="email" value="${user.email}" disabled></div><div class="form-group"><label for="password">New Password (leave blank to keep current)</label><input type="password" id="password"></div><button type="submit" class="btn btn-primary">Save Changes</button></form></div>
            <div class="form-container" style="margin-top: 2rem;"><h2>My Subscriptions</h2>${subscriptionItems ? `<ul>${subscriptionItems}</ul>` : '<p>You have no active subscriptions. <a href="#/subscribe">Subscribe now!</a></p>'}</div>
        </main>
    `;

    document.getElementById('profile-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('name').value;
        const password = document.getElementById('password').value;
        const body = { name };
        if (password) { body.password = password; }
        try {
            await apiRequest('/user/profile', 'POST', body);
            alert('Profile updated successfully!');
            state.user.name = name;
            saveState();
            router();
        } catch (error) {/* Handled */}
    });
}

export async function renderBookmarksPage() {
    if (!state.isLoggedIn || state.user.type !== 'user') { navigateTo('#/login'); return; }
    app.innerHTML = `${renderNavbar()}<main><h2>My Bookmarks</h2><div id="book-list-container">Loading...</div></main>`;
    const books = await apiRequest('/user/bookmarks');
    document.getElementById('book-list-container').innerHTML = renderBookGrid(books, 'bookmarks');
}

export async function renderHistoryPage() {
    if (!state.isLoggedIn || state.user.type !== 'user') { navigateTo('#/login'); return; }
    app.innerHTML = `${renderNavbar()}<main><h2>My Reading History</h2><div id="book-list-container">Loading...</div></main>`;
    const books = await apiRequest('/user/history');
    document.getElementById('book-list-container').innerHTML = renderBookGrid(books);
}

export async function renderPublisherDashboard() {
    if (!state.isLoggedIn || state.user.type !== 'publisher') { navigateTo('#/login'); return; }
    app.innerHTML = `${renderNavbar()}<main><h2>My Published Books</h2><div id="publisher-book-list">Loading...</div></main>`;
    const books = await apiRequest('/books/publisher');
    document.getElementById('publisher-book-list').innerHTML = renderBookGrid(books);
}

export async function renderAddOrEditBookPage(bookId = null) {
     if (!state.isLoggedIn || state.user.type !== 'publisher') {
        navigateTo('#/login');
        return;
    }

    const [categories, allBooks] = await Promise.all([
        apiRequest('/categories'),
        bookId ? apiRequest('/books/publisher') : Promise.resolve([])
    ]);

    let book = {};
    const isEditing = bookId !== null;
    if (isEditing) {
        book = allBooks.find(b => b.book_id == bookId);
        if (!book) {
            displayError("Book not found or you don't have permission to edit it.");
            navigateTo('#/publisher/dashboard');
            return;
        }
    }

    const title = isEditing ? 'Edit Book' : 'Add New Book';
    const categoryOptions = categories.map(cat =>
        `<option value="${cat.category_id}" ${book.category_id === cat.category_id ? 'selected' : ''}>
            ${cat.category_name}
        </option>`
    ).join('');

    app.innerHTML = `
        ${renderNavbar()}
        <main>
            <div class="form-container">
                <h2>${title}</h2>
                <form id="book-form" enctype="multipart/form-data">
                    <input type="hidden" name="book_id" value="${book.book_id || ''}">
                    <input type="hidden" name="existing_cover_path" value="${book.cover_path || ''}">
                    <div class="form-group"><label for="name">Book Name</label><input type="text" name="name" value="${book.name || ''}" required></div>
                    <div class="form-group"><label for="author_name">Author Name</label><input type="text" name="author_name" value="${book.author_name || ''}" required></div>
                    <div class="form-group"><label for="description">Description</label><textarea name="description" required>${book.description || ''}</textarea></div>
                    <div class="form-group">
                        <label for="category_id">Category</label>
                        <select name="category_id" required>
                            <option value="">Select a Category</option>
                            ${categoryOptions}
                        </select>
                    </div>
                    <div class="form-group"><label for="cover">Cover Image</label><input type="file" name="cover" accept="image/*"></div>
                    ${!isEditing ? `
                    <div class="form-group"><label for="pdf">Book PDF</label><input type="file" name="pdf" accept=".pdf" required></div>
                    ` : ''}
                    <button type="submit" class="btn btn-primary">${isEditing ? 'Update Book' : 'Add Book'}</button>
                </form>
            </div>
        </main>
    `;

    document.getElementById('book-form').addEventListener('submit', async e => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const endpoint = isEditing ? '/books/update' : '/books/add';
        try {
            await apiRequest(endpoint, 'POST', formData, true);
            alert(`Book ${isEditing ? 'updated' : 'added'} successfully!`);
            navigateTo('#/publisher/dashboard');
        } catch(error) { /* Handled */ }
    });
}

export async function readBook(bookId) {
    if (!state.isLoggedIn || state.user.type !== 'user') {
        displayError("You must be logged in as a user to read books.");
        return;
    }

    try {
        await apiRequest('/user/history/add', 'POST', { book_id: bookId });
    } catch (error) { console.error("Could not update reading history"); }

    app.innerHTML = `${renderNavbar()}<main><div class="text-center" style="margin-bottom: 1rem;"><button id="prev-page" class="btn btn-secondary">Previous</button><span>Page: <span id="page-num"></span> / <span id="page-count"></span></span><button id="next-page" class="btn btn-secondary">Next</button></div><div id="pdf-viewer-container"><canvas id="pdf-canvas"></canvas><p id="pdf-loading-message" class="text-center">Loading secure document...</p></div></main>`;

    try {
        const pdfBlob = await apiRequest(`/books/read/${bookId}`, 'GET', null, false, 'blob');
        const pdfData = new Uint8Array(await pdfBlob.arrayBuffer());

        if (document.getElementById('pdf-loading-message')) {
            document.getElementById('pdf-loading-message').remove();
        }

        let pdfDoc = null, pageNum = 1, pageIsRendering = false, pageNumIsPending = null;
        const scale = 1.5, canvas = document.getElementById('pdf-canvas'), ctx = canvas.getContext('2d');

        const renderPage = num => {
            pageIsRendering = true;
            pdfDoc.getPage(num).then(page => {
                const viewport = page.getViewport({ scale });
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                const renderContext = { canvasContext: ctx, viewport };
                page.render(renderContext).promise.then(() => {
                    pageIsRendering = false;
                    if (pageNumIsPending !== null) {
                        renderPage(pageNumIsPending);
                        pageNumIsPending = null;
                    }
                });
                document.getElementById('page-num').textContent = num;
            });
        };

        const queueRenderPage = num => {
            if (pageIsRendering) { pageNumIsPending = num; } else { renderPage(num); }
        };

        document.getElementById('prev-page').addEventListener('click', () => { if (pageNum <= 1) return; pageNum--; queueRenderPage(pageNum); });
        document.getElementById('next-page').addEventListener('click', () => { if (pageNum >= pdfDoc.numPages) return; pageNum++; queueRenderPage(pageNum); });

        pdfjsLib.getDocument({ data: pdfData }).promise.then(doc => {
            pdfDoc = doc;
            document.getElementById('page-count').textContent = doc.numPages;
            renderPage(pageNum);
        });

    } catch (err) {
        displayError("Could not load book. Your subscription may have expired or there was a server error.");
        console.error(err);
        if(document.getElementById('pdf-loading-message')) {
            document.getElementById('pdf-loading-message').textContent = 'Failed to load document.';
        }
    }
}
