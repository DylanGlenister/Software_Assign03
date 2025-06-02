function initAdmin() {
    document.getElementById('createAccountForm')?.addEventListener('submit', handleCreateAccount);
    document.getElementById('changeOthersPasswordForm')?.addEventListener('submit', handleChangeOthersPassword);
    document.getElementById('deactivateAccountForm')?.addEventListener('submit', handleDeactivateAccount);
    document.getElementById('deleteAccountForm')?.addEventListener('submit', handleDeleteAccount);
    document.getElementById('getAllAccountsBtn')?.addEventListener('click', getAllAccounts);
    document.getElementById('fillCreateAccountDataBtn')?.addEventListener('click', fillCreateAccountData);

    setSelectOptions({
        endpoint: '/utility/getRoles',
        elements: ['createAccountRole'],
        label: 'Select role',
        key: 'roles',
        errorMessage: 'Could not get roles'
    })

    updateAccountsList()
}

function updateAccountsList() {
    setSelectOptions({
        endpoint: '/admin/accounts',
        elements: ['targetAccountId', 'deactivateAccountId', 'deleteAccountId'],
        label: 'Select account',
        key: 'accounts',
        errorMessage: 'Could not get accounts (Please login as an admin first)',
        requireAuth: true
    })
}

async function handleCreateAccount(e) {
    e.preventDefault();
    setFormLoading('createAccountForm', true);
    const email = document.getElementById('createAccountEmail').value;
    const password = document.getElementById('createAccountPassword').value;
    const roleId = parseInt(document.getElementById('createAccountRole').value);
    const response = await makeRequest('/admin/createAccount', 'POST', { email, password, role_ID: roleId }, true);
    if (response.ok) {
        showNotification('Account created successfully!', 'success');
        document.getElementById('createAccountForm').reset();
    } else {
        showNotification('Failed to create account!', 'error');
    }
    displayResponse('createAccountResponse', response);
    updateAccountsList()

    setFormLoading('createAccountForm', false);
}

async function handleChangeOthersPassword(e) {
    e.preventDefault();
    setFormLoading('changeOthersPasswordForm', true);
    const newPassword = document.getElementById('othersNewPassword').value;
    const accountId = parseInt(document.getElementById('targetAccountId').value);
    const response = await makeRequest('/admin/changeOthersPassword', 'PUT', { new_password: newPassword, account_ID: accountId }, true);
    if (response.ok) {
        showNotification('Password changed successfully!', 'success');
        document.getElementById('changeOthersPasswordForm').reset();
    } else {
        showNotification('Failed to change password!', 'error');
    }
    displayResponse('changeOthersPasswordResponse', response);
    setFormLoading('changeOthersPasswordForm', false);
}

async function handleDeactivateAccount(e) {
    e.preventDefault();
    setFormLoading('deactivateAccountForm', true);
    const accountId = parseInt(document.getElementById('deactivateAccountId').value);
    const response = await makeRequest('/admin/deactivateAccount', 'PUT', { account_ID: accountId }, true);
    if (response.ok) {
        showNotification('Account deactivated successfully!', 'success');
        document.getElementById('deactivateAccountForm').reset();
    } else {
        showNotification('Failed to deactivate account!', 'error');
    }
    displayResponse('deactivateAccountResponse', response);
    setFormLoading('deactivateAccountForm', false);
}

async function handleDeleteAccount(e) {
    e.preventDefault();
    setFormLoading('deleteAccountForm', true);
    const accountId = parseInt(document.getElementById('deleteAccountId').value);
    const response = await makeRequest('/admin/deleteAccount', 'DELETE', { account_ID: accountId }, true);
    if (response.ok) {
        showNotification('Account deleted successfully!', 'success');
        document.getElementById('deleteAccountForm').reset();
    } else {
        showNotification('Failed to delete account!', 'error');
    }
    displayResponse('deleteAccountResponse', response);
    updateAccountsList()

    setFormLoading('deleteAccountForm', false);
}

async function getAllAccounts() {
    const response = await makeRequest('/admin/accounts', 'GET', null, true);
    if (response.ok) showNotification('Accounts retrieved successfully!', 'success');
    else showNotification('Failed to retrieve accounts!', 'error');
    displayResponse('getAllAccountsResponse', response);
}

function fillCreateAccountData() {
    const timestamp = Date.now();
    document.getElementById('createAccountEmail').value = `user${timestamp}@example.com`;
    document.getElementById('createAccountPassword').value = 'password123';
    document.getElementById('createAccountRole').value = '2';
}