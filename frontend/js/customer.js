function initCustomer() {
    document.getElementById('registerForm')?.addEventListener('submit', handleRegister);
    document.getElementById('getTrolleyBtn')?.addEventListener('click', getTrolley);
    document.getElementById('addToTrolleyForm')?.addEventListener('submit', handleAddToTrolley);
    document.getElementById('removeFromTrolleyForm')?.addEventListener('submit', handleRemoveFromTrolley);
    document.getElementById('clearTrolleyBtn')?.addEventListener('click', clearTrolley);
    document.getElementById('fillRegisterDataBtn')?.addEventListener('click', fillRegisterData);

    setSelectOptions({
        endpoint: '/utility/getProducts',
        elements: ['addProductId'],
        label: 'Select product',
        key: 'products',
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
        showNotification('Shopping cart retrieved successfully!', 'success');
    } else {
        showNotification('Failed to retrieve shopping cart!', 'error');
    }

    if (response.data && response.data.token != null) {
        console.log("Setting token")
        AUTH_TOKEN = response.data.token
        localStorage.setItem('authToken', AUTH_TOKEN);
    }

    
    displayResponse('getTrolleyResponse', response);
}

async function handleAddToTrolley(e) {
    e.preventDefault();
    setFormLoading('addToTrolleyForm', true);
    const productId = parseInt(document.getElementById('addProductId').value);
    const amount = parseInt(document.getElementById('addAmount').value);
    const response = await makeRequest('/customer/trolley/add', 'POST', { product_id: productId, amount: amount }, true);
    if (response.ok) showNotification('Item added to cart successfully!', 'success');
    else showNotification('Failed to add item to cart!', 'error');
    displayResponse('addToTrolleyResponse', response);
    setFormLoading('addToTrolleyForm', false);
}

async function handleRemoveFromTrolley(e) {
    e.preventDefault();
    setFormLoading('removeFromTrolleyForm', true);
    const productId = parseInt(document.getElementById('removeProductId').value);
    const amount = parseInt(document.getElementById('removeAmount').value);
    const response = await makeRequest('/customer/trolley/remove', 'POST', { product_id: productId, amount: amount }, true);
    if (response.ok) showNotification('Item removed from cart successfully!', 'success');
    else showNotification('Failed to remove item from cart!', 'error');
    displayResponse('removeFromTrolleyResponse', response);
    setFormLoading('removeFromTrolleyForm', false);
}

async function clearTrolley() {
    if (!AUTH_TOKEN) {
        showNotification('Please login as a customer first!', 'error');
        return;
    }
    const response = await makeRequest('/customer/trolley/clear', 'POST', null, true);
    if (response.ok) showNotification('Shopping cart cleared successfully!', 'success');
    else showNotification('Failed to clear shopping cart!', 'error');
    displayResponse('clearTrolleyResponse', response);
}

function fillRegisterData() {
    const timestamp = Date.now();
    document.getElementById('registerEmail').value = `customer${timestamp}@example.com`;
    document.getElementById('registerPassword').value = 'password123';
}