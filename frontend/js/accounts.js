const SAMPLE_CREDENTIALS = {
    customer: { email: 'customer@example.com', password: 'CustomerPassword101112%' },
    admin: { email: 'admin@example.com', password: 'AdminPassword789%' },
    employee: { email: 'employee@example.com', password: 'EmployeePassword456%' },
    owner: {email: 'owner@example.com', password: 'OwnerPassword123%'}
};

async function initAccounts() {
    document.getElementById('loginForm')?.addEventListener('submit', handleLogin);
    document.getElementById('updateAccountForm')?.addEventListener('submit', handleUpdateAccount);
    document.getElementById('changePasswordForm')?.addEventListener('submit', handleChangePassword);

    document.getElementById('fillLoginCustomerBtn')?.addEventListener('click', () => fillLoginData('customer'));
    document.getElementById('fillLoginAdminBtn')?.addEventListener('click', () => fillLoginData('admin'));
    document.getElementById('fillLoginEmployeeBtn')?.addEventListener('click', () => fillLoginData('employee'));
    document.getElementById('fillLoginOwnerBtn')?.addEventListener('click', () => fillLoginData('owner'));

    setSelectOptions({
        endpoint: '/utility/getStatuses',
        elements: ['updateStatus'],
        label: 'Select status',
        key: 'statuses',
        errorMessage: 'Could not get statuses'
    })
}

async function handleLogin(e) {
    e.preventDefault();
    setFormLoading('loginForm', true);
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const response = await makeRequest('/accounts/login', 'POST', { email, password });
    
    if (response.ok && response.data.token) {
        AUTH_TOKEN = response.data.token.access_token;
        localStorage.setItem('authToken', AUTH_TOKEN);
        showNotification('Login successful!', 'success');
    } else {
        showNotification('Login failed! Check response for details.', 'error');
        console.error("Login failed response:", response);
    }
    displayResponse('loginResponse', response);
    setFormLoading('loginForm', false);
}


async function handleUpdateAccount(e) {
    e.preventDefault();
    setFormLoading('updateAccountForm', true);
    const email = document.getElementById('updateEmail').value;
    const status = document.getElementById('updateStatus').value;
    const firstName = document.getElementById('updateFirstName').value;
    const lastName = document.getElementById('updateLastName').value;
    const payload = {};
    if (email) payload.email = email;
    if (status !== "") payload.status = status;
    if (firstName !== "") payload.firstname = firstName
    if (lastName !== "") payload.lastname = lastName
    
    if (Object.keys(payload).length === 0) {
        showNotification('No data provided for update.', 'info');
        displayResponse('updateAccountResponse', { info: "No changes to update." });
        setFormLoading('updateAccountForm', false);
        return;
    }

    const response = await makeRequest('/accounts/update', 'PUT', payload, true);
    if (response.ok) showNotification('Account updated successfully!', 'success');
    else showNotification('Failed to update account!', 'error');

    displayResponse('updateAccountResponse', response);
    setFormLoading('updateAccountForm', false);
}

async function handleChangePassword(e) {
    e.preventDefault();
    setFormLoading('changePasswordForm', true);
    const newPassword = document.getElementById('newPassword').value;
    const response = await makeRequest('/accounts/changePassword', 'PUT', { new_password: newPassword }, true);
    if (response.ok) {
        showNotification('Password changed successfully!', 'success');
        document.getElementById('newPassword').value = '';
    } else {
        showNotification('Failed to change password!', 'error');
    }
    displayResponse('changePasswordResponse', response);
    setFormLoading('changePasswordForm', false);
}

function fillLoginData(role) {
    const emailField = document.getElementById('loginEmail');
    const passwordField = document.getElementById('loginPassword');
    
    const creds = SAMPLE_CREDENTIALS[role];
    
    if (creds && emailField && passwordField) {
        emailField.value = creds.email;
        passwordField.value = creds.password;
    } else {
        console.warn(`No sample credentials found for role: ${role} or form fields missing.`);
        showNotification(`Sample data for '${role}' not configured.`, 'error');
    }
}