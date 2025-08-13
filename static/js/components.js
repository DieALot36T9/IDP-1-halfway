/* static/js/components.js */

import { state } from './state.js';

export function renderNavbar() {
    let links = '';
    if (state.isLoggedIn) {
        if (state.user.type === 'user') {
            links = `<a href="#/books">Browse Books</a><a href="#/subscribe">Subscribe</a><a href="#/bookmarks">My Bookmarks</a><a href="#/history">Reading History</a><a href="#/profile">Profile</a>`;
        } else if (state.user.type === 'publisher') {
            links = `<a href="#/publisher/dashboard">My Books</a><a href="#/publisher/add-book">Add Book</a><a href="#/books">Browse All Books</a>`;
        }
        links += `<a href="#" id="logout-btn">Logout (${state.user.name})</a>`;
    } else {
        links = `<a href="#/books">Browse Books</a><a href="#/login">Login</a><a href="#/register">Register</a>`;
    }
    return `<nav class="navbar"><a href="#/" class="logo">eBookReader</a><div class="navbar-links">${links}</div></nav>`;
}

export function renderBookCard(book, context = 'browse') {
    const coverPath = book.cover_path ? `/static/uploads/${book.cover_path}` : 'https://placehold.co/400x600/eee/ccc?text=No+Cover';

    let actions = '';
    if (state.isLoggedIn) {
        if (state.user.type === 'user') {
            const isSubscribed = state.user.subscriptions && state.user.subscriptions[book.category_id];

            if (isSubscribed) {
                actions = `<button class="btn btn-primary" data-action="read-book" data-book-id="${book.book_id}">Read</button>`;
            } else {
                actions = `<button class="btn btn-warning" data-action="subscribe">Subscribe</button>`;
            }

            if (context === 'bookmarks') {
                actions += ` <button class="btn btn-danger" data-action="remove-bookmark" data-book-id="${book.book_id}">Remove</button>`;
            } else {
                actions += ` <button class="btn btn-secondary" data-action="add-bookmark" data-book-id="${book.book_id}">Bookmark</button>`;
            }
        } else if (state.user.type === 'publisher' && state.user.publisher_id === book.publisher_id) {
            actions = `<button class="btn btn-secondary" data-action="edit-book" data-book-id="${book.book_id}">Edit</button> <button class="btn btn-danger" data-action="delete-book" data-book-id="${book.book_id}">Delete</button>`;
        }
    } else {
        actions = `<button class="btn btn-primary" data-action="login">Login to Read</button>`;
    }

    return `
        <div class="book-card" data-book-id="${book.book_id}">
            <img src="${coverPath}" alt="${book.name}" class="book-card-cover">
            <div class="book-card-content">
                <h3>${book.name}</h3>
                <p class="author">by ${book.author_name}</p>
                <p class="category">Category: ${book.category_name || 'Uncategorized'}</p>
                <p class="publisher">Publisher: ${book.publisher_name || 'N/A'}</p>
                ${book.last_read_timestamp ? `<p><em>Last read: ${new Date(book.last_read_timestamp).toLocaleString()}</em></p>` : ''}
                <div class="book-card-actions">${actions}</div>
            </div>
        </div>
    `;
}

export function renderBookGrid(books, context = 'browse') {
    if (!books || books.length === 0) {
        return '<p class="text-center">No books found for this selection.</p>';
    }
    return `<div class="book-grid">${books.map(book => renderBookCard(book, context)).join('')}</div>`;
}
