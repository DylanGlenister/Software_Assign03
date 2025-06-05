function initCustomer() {
    document.getElementById('registerForm')?.addEventListener('submit', handleRegister);
    document.getElementById('getTrolleyBtn')?.addEventListener('click', getTrolley);
    document.getElementById('addToTrolleyForm')?.addEventListener('submit', handleAddToTrolley);
    document.getElementById('modifyItemInTrolleyForm')?.addEventListener('submit', handleModifyItemInTrolley);
    document.getElementById('removeFromTrolleyForm')?.addEventListener('submit', handleRemoveFromTrolley);
    document.getElementById('clearTrolleyBtn')?.addEventListener('click', clearTrolley);
    document.getElementById('fillRegisterDataBtn')?.addEventListener('click', fillRegisterData);

    setSelectOptions({
        endpoint: '/utility/getProducts',
        elements: ['addProductId'],
        label: 'Select product',
        key: 'products',
        idKey: 'productID',
        errorMessage: 'Could not get products'
    })
}

async function handleRegister(e) {
    e.preventDefault();
    setFormLoading('registerForm', true);
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const response = await makeRequest('/customer/register', 'POST', { email, password });
    if (response.ok) {
        showNotification('Registration successful!', 'success');
        document.getElementById('registerForm').reset();
    } else {
        showNotification('Registration failed!', 'error');
    }
    displayResponse('registerResponse', response);
    setFormLoading('registerForm', false);
}

async function getTrolley() {
    const response = await makeRequest('/customer/trolley', 'GET', null, true);
    if (response.ok) {
        showNotification('Shopping trolley retrieved successfully!', 'success');
    } else {
        showNotification('Failed to retrieve shopping trolley!', 'error');
    }

    if (response.data && response.data.token != null) {
        console.log("Setting token")
        AUTH_TOKEN = response.data.token
        localStorage.setItem('authToken', AUTH_TOKEN);
    }


    displayResponse('getTrolleyResponse', response);
    createTable('getTrolleyResponse', response.data.trolley);
}

async function handleAddToTrolley(e) {
    e.preventDefault();
    setFormLoading('addToTrolleyForm', true);
    const productId = parseInt(document.getElementById('addProductId').value);
    const amount = parseInt(document.getElementById('addAmount').value);
    const response = await makeRequest('/customer/trolley/add', 'POST', { product_id: productId, amount: amount }, true);
    if (response.ok) showNotification('Item added to trolley successfully!', 'success');
    else showNotification('Failed to add item to trolley!', 'error');
    displayResponse('addToTrolleyResponse', response);
    setFormLoading('addToTrolleyForm', false);
}

async function handleModifyItemInTrolley(e) {
    e.preventDefault();
    setFormLoading('modifyItemInTrolleyForm', true);
    const productId = parseInt(document.getElementById('modifyProductId').value);
    const amount = parseInt(document.getElementById('modifyAmount').value);
    const response = await makeRequest('/customer/trolley/modify', 'POST', { product_id: productId, amount: amount }, true);
    if (response.ok) showNotification('Item modified in trolley successfully!', 'success');
    else showNotification('Failed to modify item in trolley!', 'error');
    displayResponse('modifyItemInTrolleyResponse', response);
    setFormLoading('modifyItemInTrolleyForm', false);
}

async function handleRemoveFromTrolley(e) {
    e.preventDefault();
    setFormLoading('removeFromTrolleyForm', true);
    const productId = parseInt(document.getElementById('removeProductId').value);
    const response = await makeRequest('/customer/trolley/remove', 'POST', { product_id: productId }, true);
    if (response.ok) showNotification('Item removed from trolley successfully!', 'success');
    else showNotification('Failed to remove item from trolley!', 'error');
    displayResponse('removeFromTrolleyResponse', response);
    setFormLoading('removeFromTrolleyForm', false);
}

async function clearTrolley() {
    if (!AUTH_TOKEN) {
        showNotification('Please login as a customer first!', 'error');
        return;
    }
    const response = await makeRequest('/customer/trolley/clear', 'POST', null, true);
    if (response.ok) showNotification('Shopping trolley cleared successfully!', 'success');
    else showNotification('Failed to clear shopping trolley!', 'error');
    displayResponse('clearTrolleyResponse', response);
}

function fillRegisterData() {
    const timestamp = Date.now();
    document.getElementById('registerEmail').value = `customer${timestamp}@example.com`;
    document.getElementById('registerPassword').value = SAMPLE_CREDENTIALS['customer']['password'];
}
