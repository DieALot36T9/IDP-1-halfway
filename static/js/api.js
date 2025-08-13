/* static/js/api.js */

import { state } from './state.js';
import { displayError } from './utils.js';

const API_BASE_URL = 'http://localhost:8000/api';

export async function apiRequest(endpoint, method = 'GET', body = null, isFormData = false, responseType = 'json') {
    const headers = {};
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    const config = { method, headers };
    if (body) {
        if (isFormData) {
            config.body = body;
        } else {
            headers['Content-Type'] = 'application/json';
            config.body = JSON.stringify(body);
        }
    }
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        if (responseType === 'blob') {
            return await response.blob();
        }
        if (response.status === 204) {
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error('API Request Error:', error);
        displayError(error.message);
        throw error;
    }
}
