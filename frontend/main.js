let API_BASE_URL = 'http://localhost:8000/api/v1/endpoints';
let AUTH_TOKEN = null; 

// --- UTILITY FUNCTIONS (accessible globally) ---
async function makeRequest(endpoint, method = 'GET', body = null, requireAuth = false) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = { 'Content-Type': 'application/json' };
    if (requireAuth && AUTH_TOKEN) {
        headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
    }
    const config = { method, headers };
    if (body && (method === 'POST' || method === 'PUT' || method === 'DELETE')) {
        config.body = JSON.stringify(body);
    }

    let responseData = { ok: false, status: 0, data: { error: "Request failed to execute." } };
    try {
        const response = await fetch(url, config);
        const dataText = await response.text();
        let jsonData;
        try { 
            jsonData = JSON.parse(dataText); 
        } catch (e) { 
            jsonData = { raw_response: dataText, parse_error: e.message, endpoint_called: endpoint };
            if (typeof logAppMessage === 'function') {
                logAppMessage(`JSON Parse Error for ${method} ${endpoint}: ${e.message}. Raw: ${dataText.substring(0,150)}...`, 'error');
            }
        }
        responseData = { ok: response.ok, status: response.status, data: jsonData };

        if (!response.ok) {
            let errorMsg = `API Error: ${method} ${endpoint} (Status: ${response.status}). `;
            if(jsonData?.detail) errorMsg += `Detail: ${jsonData.detail}`;
            else if(jsonData?.error) errorMsg += `Error: ${jsonData.error}`;
            else if(jsonData?.raw_response) errorMsg += `Response: ${jsonData.raw_response.substring(0,100)}...`;
            else errorMsg += `Response: ${JSON.stringify(jsonData).substring(0,100)}...`;
            
            if (typeof logAppMessage === 'function') {
                logAppMessage(errorMsg, 'error');
            }
        }
        return responseData;

    } catch (error) {
        const errorMsg = `Network/Fetch Error for ${method} ${endpoint}: ${error.message}`;
        if (typeof logAppMessage === 'function') {
            logAppMessage(errorMsg, 'error');
        }
        responseData.data.error = error.message;
        return responseData;
    }
}

function displayResponse(elementId, response) {
    const container = document.getElementById(elementId);
    if (!container) {
        console.warn(`Response container with ID '${elementId}' not found.`);
        return;
    }

    const content = container.querySelector('.response-content');
    if (!content) {
        console.warn(`Response content area not found in container '${elementId}'.`);
        return;
    }

    container.style.display = 'block';

    content.innerHTML = JSON.stringify(response, null, 2);
    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function createTable(elementId, items) {
    const container = document.getElementById(elementId);
    if (!container) {
        console.warn(`Response container with ID '${elementId}' not found.`);
        return;
    }

    const tableContainer = container.querySelector('.table-container');
    if (!tableContainer) {
        console.warn(`Table content area not found in container '${elementId}'.`);
        return;
    }
    if (!items.length) {
        tableContainer.innerHTML = '<p>No data available.</p>';
        return;
    }

    const headers = Object.keys(items[0]);

    let table = `<table class="table table-striped">
        <thead>
            <tr>${headers.map(key => `<th>${formatHeader(key)}</th>`).join('')}</tr>
        </thead>
        <tbody>`;

    for (const item of items) {
        table += `<tr>${headers.map(key => `<td>${formatValue(item[key])}</td>`).join('')}</tr>`;
    }

    table += '</tbody></table>';

    tableContainer.innerHTML = table
}


function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.style.cssText = `
        position: fixed; top: 20px; right: 20px; padding: 15px 20px;
        background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1'};
        color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460'};
        border: 1px solid ${type === 'success' ? '#c3e6cb' : type === 'error' ? '#f5c6cb' : '#bee5eb'};
        border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000;
        max-width: 300px; font-weight: 500;`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

function setFormLoading(formId, loading) {
    const form = document.getElementById(formId);
    if (form) {
        form.classList.toggle('loading', loading);
    }
}

function updateTokenDisplay() {
    const tokenDisplay = document.getElementById('currentToken');
    const tokenValueEl = document.getElementById('tokenValue');
    
    if (tokenDisplay && tokenValueEl) {
        if (AUTH_TOKEN) {
            tokenDisplay.style.display = 'block';
            tokenValueEl.textContent = AUTH_TOKEN;
        } else {
            tokenDisplay.style.display = 'none';
        }
    }
}

function setOptions(data, element, idKey, nameKey) {
    data.forEach(entry => {
        const option = document.createElement('option');
        option.value = entry[idKey];
        option.textContent = `${entry[idKey]} (${entry[nameKey]})`;
        element.appendChild(option);
    });
}

function capitalize(text) {
    return text
        .split(' ')
        .map(word =>
            word.length > 1 ? word[0].toUpperCase() + word.slice(1) : word.toUpperCase()
        )
        .join(' ');
}

function formatHeader(header) {
    header = header.replace(/([a-z0-9])([A-Z])/g, '$1 $2');
    return capitalize(header);
}

function formatValue(value) {
    if (value === null || value === undefined || value === '') return '-';
    if ((typeof value === 'number' && Number.isInteger(value)) || (!isNaN(parseFloat(value)))) return value

    const date = new Date(value);
    if (!isNaN(date)) {
        return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
        });
    }

    return capitalize(String(value))
}

async function setSelectOptions({ endpoint, elements, label = 'Select an option', key, errorMessage, requireAuth = false, idKey = "id", nameKey = "name"}) {
    const response = await makeRequest(endpoint, 'GET', {}, requireAuth);

    if (!response.ok || !response.data || !response.data[key]) {
        showNotification(errorMessage, 'error');
        console.log(response)
        return;
    }
    
    elements.forEach(elementId => {
        const selectElement = document.getElementById(elementId);
        selectElement.innerHTML = `<option value="">${label}</option>`;
        
        setOptions(response.data[key], selectElement, idKey, nameKey);
    })
}

// --- NAVIGATION AND PARTIAL LOADING ---
const mainContentArea = document.getElementById('main-content-area');

async function loadSection(sectionName) {
    if (!mainContentArea) {
        console.error("#main-content-area not found!");
        return;
    }
    try {
        mainContentArea.innerHTML = '<p class="loading-placeholder" style="padding: 20px; text-align: center;">Loading...</p>'; 
        const response = await fetch(`html/${sectionName}.html`);
        if (!response.ok) throw new Error(`Failed to load ${sectionName}.html: ${response.status} ${response.statusText}`);
        mainContentArea.innerHTML = await response.text();
        const loadedSectionElement = mainContentArea.querySelector(`#${sectionName}.content-section`);
        if (loadedSectionElement) {
            loadedSectionElement.classList.add('active'); 
        } else {
            console.warn(`Could not find the root element for section "${sectionName}"`);
            const genericSectionElement = mainContentArea.querySelector('.content-section');
            if (genericSectionElement) genericSectionElement.classList.add('active');
        }

        switch (sectionName) {
            case 'info':
                if (typeof initInfo === 'function') initInfo();
                else console.warn('initInfo function not found.');
                break;
            case 'config':
                if (typeof initConfig === 'function') initConfig();
                else console.warn('initConfig function not found.');
                break;
            case 'accounts':
                if (typeof initAccounts === 'function') initAccounts();
                else console.warn('initAccounts function not found.');
                break;
            case 'admin':
                if (typeof initAdmin === 'function') initAdmin();
                else console.warn('initAdmin function not found.');
                break;
            case 'customer':
                if (typeof initCustomer === 'function') initCustomer();
                else console.warn('initCustomer function not found.');
                break;
            case 'employee':
                if (typeof initEmployee === 'function') initEmployee();
                else console.warn('initEmployee function not found.');
                break;

            default:
                console.warn(`No specific init function for section: ${sectionName}`);
        }
    } catch (error) {
        console.error('Error loading section:', sectionName, error);
        mainContentArea.innerHTML = `<div class="error" style="display:block; padding:20px;">Error loading content for ${sectionName}.<br>Details: ${error.message}.</div>`;
        if (typeof logAppMessage === 'function') {
            logAppMessage(`Failed to load section '${sectionName}': ${error.message}`, 'error');
        }
    }
}


function setupNavigation() {
    const navItems = document.querySelectorAll('.sidebar .nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            const targetSection = this.getAttribute('data-section');
            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');
            loadSection(targetSection);
        });
    });

}

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', function() {
    const savedUrl = localStorage.getItem('apiBaseUrl');
    const savedToken = localStorage.getItem('authToken');
    if (savedUrl) API_BASE_URL = savedUrl;
    if (savedToken) AUTH_TOKEN = savedToken;
    
    setupNavigation();
    
    const defaultSectionItem = document.querySelector('.sidebar .nav-item.active');
    let defaultSectionName = 'info';
    if (defaultSectionItem) {
        defaultSectionName = defaultSectionItem.getAttribute('data-section');
    } else {
        const infoNavItem = document.querySelector('.sidebar .nav-item[data-section="info"]');
        infoNavItem?.classList.add('active');
    }
    loadSection(defaultSectionName);
});