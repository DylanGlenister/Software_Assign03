function initAdmin() {
    document.getElementById('createAccountForm')?.addEventListener('submit', handleCreateAccount);
    document.getElementById('changeOthersPasswordForm')?.addEventListener('submit', handleChangeOthersPassword);
    document.getElementById('deactivateAccountForm')?.addEventListener('submit', handleDeactivateAccount);
    document.getElementById('deleteAccountForm')?.addEventListener('submit', handleDeleteAccount);
    document.getElementById('getAllAccountsBtn')?.addEventListener('click', getAllAccounts);
    document.getElementById('deleteFilteredAccountsForm').addEventListener('submit', handleDeleteAccounts);

    document.getElementById('fillCreateCustomerBtn')?.addEventListener('click', () => fillCreateData('customer'));
    document.getElementById('fillCreateAdminBtn')?.addEventListener('click', () => fillCreateData('admin'));
    document.getElementById('fillCreateEmployeeBtn')?.addEventListener('click', () => fillCreateData('employee'));

    setSelectOptions({
        endpoint: '/utility/getRoles',
        elements: ['createAccountRole', 'deleteFilteredAccountsRole'],
        label: 'Select role',
        key: 'roles',
        errorMessage: 'Could not get roles'
    })

    setSelectOptions({
        endpoint: '/utility/getStatuses',
        elements: ['deleteFilteredAccountsStatus'],
        label: 'Select status',
        key: 'statuses',
        errorMessage: 'Could not get status'
    })

    updateAccountsList()
}

function updateAccountsList() {
    setSelectOptions({
        endpoint: '/admin/accounts',
        elements: ['changePasswordAccountId', 'deactivateAccountId', 'deleteAccountId'],
        label: 'Select account',
        key: 'accounts',
        errorMessage: 'Could not get accounts (Please login as an admin first)',
        requireAuth: true,
        nameKey: "email",
        idKey: "accountID"
    })
}

async function handleCreateAccount(e) {
    e.preventDefault();
    setFormLoading('createAccountForm', true);
    const email = document.getElementById('createAccountEmail').value;
    const password = document.getElementById('createAccountPassword').value;
    const role = document.getElementById('createAccountRole').value;
    const response = await makeRequest('/admin/createAccount', 'POST', { email, password, role: role }, true);
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
    const accountId = parseInt(document.getElementById('changePasswordAccountId').value);
    const response = await makeRequest('/admin/changeOthersPassword', 'PUT', { newPassword: newPassword, accountID: accountId }, true);
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
    const response = await makeRequest('/admin/deactivateAccount', 'PUT', { accountID: accountId }, true);
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
    const response = await makeRequest('/admin/deleteAccount', 'DELETE', { accountID: accountId }, true);
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

async function handleDeleteAccounts(e) {
    e.preventDefault();
    setFormLoading('deleteAccountForm', true);
    
    try {
        const role = document.getElementById('deleteFilteredAccountsRole').value;
        const status = document.getElementById('deleteFilteredAccountsStatus').value;
        const daysOld = document.getElementById('deleteFilteredAccountsDaysOld').value;

        if (!role && !daysOld && !status) {
            showNotification('At least one filter (role, status or days old) must be set!', 'error');
            return;
        }
        
        const payload = {};
        if (role) payload.role = role;
        if (status) payload.status = status;
        if (daysOld) payload.daysOld = parseInt(daysOld);
        
        const response = await makeRequest('/admin/deleteAccounts', 'DELETE', payload, true);
        
        if (response.ok) {
            showNotification('Accounts deleted successfully!', 'success');
            document.getElementById('deleteAccountForm').reset();
        } else {
            showNotification('Failed to delete account!', 'error');
        }
        
        displayResponse('deleteFilteredAccountsResponse', response);
        updateAccountsList();
        
    } catch (error) {
        console.error('Error deleting accounts:', error);
        showNotification('An unexpected error occurred', 'error');
    } finally {
        setFormLoading('deleteAccountForm', false);
    }
}

async function getAllAccounts() {
    const response = await makeRequest('/admin/accounts', 'GET', null, true);
    if (response.ok) showNotification('Accounts retrieved successfully!', 'success');
    else showNotification('Failed to retrieve accounts!', 'error');
    displayResponse('getAllAccountsResponse', response)
    createTable('getAllAccountsResponse', response.data.accounts);
}

function fillCreateData(role) {
    const timestamp = Date.now();
    document.getElementById('createAccountEmail').value = `${role}${timestamp}@example.com`;
    document.getElementById('createAccountPassword').value = SAMPLE_CREDENTIALS[role]["password"];
    document.getElementById('createAccountRole').value = role;
}