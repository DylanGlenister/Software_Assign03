let tokenCountdownInterval = null;

function initConfig() {
    const apiUrlInput = document.getElementById('apiBaseUrl');
    if (apiUrlInput) {
        apiUrlInput.value = API_BASE_URL;
    }

    document.getElementById('saveConfigBtn')?.addEventListener('click', saveCurrentConfig);
    document.getElementById('clearTokenBtn')?.addEventListener('click', handleClearToken);
    document.getElementById('fetchTokenDetailsBtn')?.addEventListener('click', fetchAndDisplayTokenDetails);

    manageTokenSectionDisplay();
}

function manageTokenSectionDisplay() {
    const tokenInfoMessageEl = document.getElementById('tokenInfoMessage');
    const actualTokenDataEl = document.getElementById('actualTokenData');
    const tokenDetailsErrorEl = document.getElementById('tokenDetailsError');
    const rawTokenDisplayEl = document.getElementById('currentToken');

    if (AUTH_TOKEN) {
        if (tokenInfoMessageEl) tokenInfoMessageEl.style.display = 'none';
        if (actualTokenDataEl) actualTokenDataEl.style.display = 'block';
        if (rawTokenDisplayEl) rawTokenDisplayEl.style.display = 'block';
        updateRawTokenValue();
        fetchAndDisplayTokenDetails();
    } else {
        if (tokenInfoMessageEl) tokenInfoMessageEl.style.display = 'block';
        if (actualTokenDataEl) actualTokenDataEl.style.display = 'none';
        if (rawTokenDisplayEl) rawTokenDisplayEl.style.display = 'none';
        if (tokenDetailsErrorEl) tokenDetailsErrorEl.style.display = 'none';
        if (typeof updateSidebarAccessIndicators === 'function') {
            CURRENT_USER_ROLE = null;
            updateSidebarAccessIndicators();
        }
        clearTokenDetailsUIData();
        clearTokenCountdown();
    }
}

function saveCurrentConfig() {
    const url = document.getElementById('apiBaseUrl')?.value.trim();
    if (url) {
        API_BASE_URL = url;
        localStorage.setItem('apiBaseUrl', url);
        showNotification('Configuration saved successfully!', 'success');
    } else {
        showNotification('API Base URL cannot be empty.', 'error');
    }
}

function handleClearToken() {
    AUTH_TOKEN = null;
    localStorage.removeItem('authToken');
    showNotification('Token cleared successfully!', 'success');

    if (typeof updateSidebarAccessIndicators === 'function') {
        CURRENT_USER_ROLE = null;
        updateSidebarAccessIndicators();
    }

    manageTokenSectionDisplay();
}

function updateRawTokenValue() {
    const tokenValueEl = document.getElementById('tokenValue');
    if (tokenValueEl) {
        tokenValueEl.textContent = AUTH_TOKEN || '';
    }
}

async function fetchAndDisplayTokenDetails() {
    const actualTokenDataEl = document.getElementById('actualTokenData');
    const errorDisplay = document.getElementById('tokenDetailsError');
    const fetchBtn = document.getElementById('fetchTokenDetailsBtn');

    if (!AUTH_TOKEN) {
        manageTokenSectionDisplay();
        return;
    }

    if(fetchBtn) fetchBtn.disabled = true;
    if(errorDisplay) errorDisplay.style.display = 'none';

    const response = await makeRequest('/utility/tokenInfo', 'POST', null, true);
    
    if(fetchBtn) fetchBtn.disabled = false;

    if (response.ok && response.data && response.data.data) {
        if(actualTokenDataEl) actualTokenDataEl.style.display = 'block';
        document.getElementById('tokenInfoMessage').style.display = 'none';

        const tokenInfo = response.data;
        const userSpecificData = tokenInfo.data;

        const date = new Date(tokenInfo.expires_at);

        const options = {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true
        };

        const formattedExpiresAt = date.toLocaleString(undefined, options) || null;

        document.getElementById('tokenExpiresAt').textContent = formattedExpiresAt || '-';
        document.getElementById('tokenAccountId').textContent = userSpecificData.accountID || '-';
        document.getElementById('tokenEmail').textContent = userSpecificData.email || '-';
        document.getElementById('tokenRoleId').textContent = capitalize(userSpecificData.role) || '-';
        document.getElementById('tokenStatusId').textContent = capitalize(userSpecificData.status) || '-';
        
        updateRawTokenValue();
        document.getElementById('currentToken').style.display = 'block';

        if (typeof updateSidebarAccessIndicators === 'function') {
            CURRENT_USER_ROLE = userSpecificData.role ? userSpecificData.role.toLowerCase() : null;
            updateSidebarAccessIndicators();
        }

        startTokenCountdown(tokenInfo.time_remaining_seconds);
    } else {
        let errorMessage = 'Failed to fetch token details.';
        if (response.data && response.data.Detail) errorMessage = response.data.Detail;
        else if (response.data && response.data.Error) errorMessage = response.data.Error;
        else if (response.status) errorMessage += ` (Status: ${response.status})`;
        
        console.error("Error fetching token details:", response);
        if(errorDisplay) {
            errorDisplay.textContent = errorMessage;
            errorDisplay.style.display = 'block';
        }
        showNotification(errorMessage, 'error');
        clearTokenDetailsUIData(false);

        if (typeof updateSidebarAccessIndicators === 'function') {
            CURRENT_USER_ROLE = null;
            updateSidebarAccessIndicators();
        }
        clearTokenCountdown();
    }
}

function startTokenCountdown(totalSeconds) {
    clearInterval(tokenCountdownInterval); 
    const timeRemainingEl = document.getElementById('tokenTimeRemaining');
    if (!timeRemainingEl) return;

    if (typeof totalSeconds !== 'number' || totalSeconds <= 0) {
        timeRemainingEl.textContent = 'Expired or N/A';
        return;
    }
    let remainingSeconds = Math.floor(totalSeconds);
    function updateCountdown() {
        if (remainingSeconds <= 0) {
            clearInterval(tokenCountdownInterval);
            timeRemainingEl.textContent = 'Expired';
            return;
        }
        const hours = Math.floor(remainingSeconds / 3600);
        const minutes = Math.floor((remainingSeconds % 3600) / 60);
        const seconds = remainingSeconds % 60;
        timeRemainingEl.textContent = 
            `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        remainingSeconds--;
    }
    updateCountdown();
    tokenCountdownInterval = setInterval(updateCountdown, 1000);
}

function clearTokenCountdown() {
    clearInterval(tokenCountdownInterval);
    const timeRemainingEl = document.getElementById('tokenTimeRemaining');
    if (timeRemainingEl) timeRemainingEl.textContent = '-';
}


function clearTokenDetailsUIData(clearRawTokenValue = true) {
    document.getElementById('tokenExpiresAt').textContent = '-';
    document.getElementById('tokenAccountId').textContent = '-';
    document.getElementById('tokenEmail').textContent = '-';
    document.getElementById('tokenRoleId').textContent = '-';
    document.getElementById('tokenStatusId').textContent = '-';
    document.getElementById('tokenTimeRemaining').textContent = '-';
    if (clearRawTokenValue) {
        const tokenValueEl = document.getElementById('tokenValue');
        if (tokenValueEl) tokenValueEl.textContent = '';
    }
}