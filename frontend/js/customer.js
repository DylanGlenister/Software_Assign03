function initCustomer() {
    document.getElementById('registerForm')?.addEventListener('submit', handleRegister);
    document.getElementById('getTrolleyBtn')?.addEventListener('click', getTrolley);
    document.getElementById('addToTrolleyForm')?.addEventListener('submit', handleAddToTrolley);
    document.getElementById('modifyItemInTrolleyForm')?.addEventListener('submit', handleModifyItemInTrolley);
    document.getElementById('removeFromTrolleyForm')?.addEventListener('submit', handleRemoveFromTrolley);
    document.getElementById('clearTrolleyBtn')?.addEventListener('click', clearTrolley);
    document.getElementById('fillRegisterDataBtn')?.addEventListener('click', fillRegisterData);

    document.getElementById('getOrdersBtn')?.addEventListener('click', handleGetOrders);
    document.getElementById('createOrderForm')?.addEventListener('submit', handleCreateOrder);
    document.getElementById('getAddressesBtn')?.addEventListener('click', handleGetAddresses);
    document.getElementById('addAddressForm')?.addEventListener('submit', handleAddAddress);
    document.getElementById('removeAddressForm')?.addEventListener('submit', handleRemoveAddress);

    updateProductOptions()
}

function updateProductOptions(){
    setSelectOptions({
        endpoint: '/utility/getProducts',
        elements: ['addProductId', 'updateProductId', 'removeProductId'],
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
    updateProductOptions()
    setFormLoading('addToTrolleyForm', false);
}

async function handleModifyItemInTrolley(e) {
    e.preventDefault();
    setFormLoading('modifyItemInTrolleyForm', true);
    const productId = parseInt(document.getElementById('updateProductId').value);
    const amount = parseInt(document.getElementById('modifyAmount').value);
    const response = await makeRequest('/customer/trolley/modify', 'POST', { product_id: productId, amount: amount }, true);
    if (response.ok) showNotification('Item modified in trolley successfully!', 'success');
    else showNotification('Failed to modify item in trolley!', 'error');
    displayResponse('modifyItemInTrolleyResponse', response);
    updateProductOptions()
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
    updateProductOptions()
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

function groupOrders(orderItems) {
    if (!orderItems || orderItems.length === 0) return {};
    const orders = {};
    orderItems.forEach(item => {
        const { orderID, accountID, addressID, date, lineItemID, productID, quantity, priceAtSale, name, location } = item;
        if (!orders[orderID]) {
            orders[orderID] = {
                orderID,
                accountID,
                addressID,
                location,
                date,
                items: []
            };
        }
        orders[orderID].items.push({ lineItemID, productID, quantity, priceAtSale, name });
    });
    return orders;
}

async function handleGetOrders() {
    if (!AUTH_TOKEN) {
        showNotification('Please login as a customer first!', 'error');
        return;
    }
    const response = await makeRequest('/customer/orders', 'GET', null, true);
    
    displayResponse('getOrdersResponse', response);

    const ordersOuterContainer = document.getElementById('getOrdersResponse');
    const allOrdersDisplayContainer = ordersOuterContainer?.querySelector('.table-container'); 

    if (!allOrdersDisplayContainer) {
        console.error('.table-container not found in #getOrdersResponse for all orders');
        if (response.ok) showNotification('Orders retrieved, but main display area is missing.', 'warning');
        else showNotification('Failed to retrieve orders and main display area is missing.', 'error');
        return;
    }
    allOrdersDisplayContainer.innerHTML = ''; 

    if (response.ok) {
        showNotification('Orders retrieved successfully!', 'success');
        if (response.data && response.data.token != null) {
            AUTH_TOKEN = response.data.token;
            localStorage.setItem('authToken', AUTH_TOKEN);
        }

        if (response.data && response.data.orders && response.data.orders.length > 0) {
            const groupedOrders = groupOrders(response.data.orders);

            for (const orderId in groupedOrders) {
                const orderData = groupedOrders[orderId];

                const orderWrapperDiv = document.createElement('div');
                orderWrapperDiv.className = 'order-block';
                orderWrapperDiv.style.cssText = "border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; background-color: #f9f9f9;";

                const orderTitleH4 = document.createElement('h4');
                orderTitleH4.textContent = `Order ID: ${orderData.orderID}`;
                orderTitleH4.style.marginTop = '0px';
                orderWrapperDiv.appendChild(orderTitleH4);

                const orderInfoDiv = document.createElement('div');
                orderInfoDiv.style.marginBottom = '10px';
                orderInfoDiv.innerHTML = `
                    <p style="margin: 3px 0; font-size: 0.9em;"><strong>Date:</strong> ${new Date(orderData.date).toLocaleString()}</p>
                    <p style="margin: 3px 0; font-size: 0.9em;"><strong>Address ID:</strong> ${orderData.addressID} (${orderData.location})</p>
                `;
                orderWrapperDiv.appendChild(orderInfoDiv);

                const itemsTitleH5 = document.createElement('h5');
                itemsTitleH5.textContent = 'Items:';
                itemsTitleH5.style.marginTop = '15px';
                itemsTitleH5.style.marginBottom = '5px';
                orderWrapperDiv.appendChild(itemsTitleH5);

                allOrdersDisplayContainer.appendChild(orderWrapperDiv);


                if (orderData.items.length > 0) {
                    const itemsForTable = orderData.items.map(item => ({
                        lineItemID: item.lineItemID,
                        name: item.name,
                        productID: item.productID,
                        quantity: item.quantity,
                        priceAtSale: item.priceAtSale
                    }));

                    const itemsTableHostDiv = document.createElement('div');
                    const uniqueItemsContainerId = `order-items-table-${orderData.orderID}`;
                    itemsTableHostDiv.id = uniqueItemsContainerId;

                    const actualTableContainerForItems = document.createElement('div');
                    actualTableContainerForItems.className = 'table-container';
                    itemsTableHostDiv.appendChild(actualTableContainerForItems);
                    orderWrapperDiv.appendChild(itemsTableHostDiv);

                    createTable(uniqueItemsContainerId, itemsForTable);

                } else {
                    const noItemsP = document.createElement('p');
                    noItemsP.textContent = 'No items in this order.';
                    noItemsP.style.fontStyle = 'italic';
                    orderWrapperDiv.appendChild(noItemsP);
                }
                // The orderWrapperDiv is already appended above.
            }
        } else if (response.data && response.data.orders) {
            allOrdersDisplayContainer.textContent = 'No orders found.';
        }
    } else {
        showNotification(response.data?.detail || 'Failed to retrieve orders!', 'error');
        allOrdersDisplayContainer.textContent = 'Failed to load orders.';
    }
}

async function handleCreateOrder(e) {
    e.preventDefault();
    if (!AUTH_TOKEN) {
        showNotification('Please login as a customer first!', 'error');
        return;
    }
    setFormLoading('createOrderForm', true);
    const addressId = parseInt(document.getElementById('createOrderAddressId').value);
    const response = await makeRequest('/customer/order/create', 'POST', { address_id: addressId }, true);
    if (response.ok) {
        showNotification('Order created successfully!', 'success');
        document.getElementById('createOrderForm').reset();
    } else {
        showNotification('Failed to create order!', 'error');
    }

    if (response.data && response.data.token != null) {
        AUTH_TOKEN = response.data.token;
        localStorage.setItem('authToken', AUTH_TOKEN);
    }
    displayResponse('createOrderResponse', response);
    setFormLoading('createOrderForm', false);
}

async function handleGetAddresses(e) {
    e.preventDefault();
    if (!AUTH_TOKEN) {
        showNotification('Please login as a customer first!', 'error');
        return;
    }
    const response = await makeRequest('/customer/address', 'GET', null, true);
    if (response.ok) {
        showNotification('Addresses retrieved successfully!', 'success');
    } else {
        showNotification('Failed to retrieve addresses!', 'error');
    }

    if (response.data && response.data.token != null) {
        AUTH_TOKEN = response.data.token;
        localStorage.setItem('authToken', AUTH_TOKEN);
    }
    displayResponse('getAddressesResponse', response);
     if (response.data && response.data.addresses) {
        createTable('getAddressesResponse', response.data.addresses);
    }
}

async function handleAddAddress(e) {
    e.preventDefault();
    if (!AUTH_TOKEN) {
        showNotification('Please login as a customer first!', 'error');
        return;
    }
    setFormLoading('addAddressForm', true);
    const address = document.getElementById('addAddressValue').value;
    const endpoint = `/customer/address/add`;
    const response = await makeRequest(endpoint, 'POST', {"address": address}, true);

    if (response.ok) {
        showNotification('Address added successfully!', 'success');
        document.getElementById('addAddressForm').reset();
    } else {
        showNotification(response.data?.detail || 'Failed to add address!', 'error');
    }

    if (response.data && response.data.token != null) {
        AUTH_TOKEN = response.data.token;
        localStorage.setItem('authToken', AUTH_TOKEN);
    }
    displayResponse('addAddressResponse', response);
    setFormLoading('addAddressForm', false);
}

async function handleRemoveAddress(e) {
    e.preventDefault();
    if (!AUTH_TOKEN) {
        showNotification('Please login as a customer first!', 'error');
        return;
    }
    setFormLoading('removeAddressForm', true);
    const addressId = parseInt(document.getElementById('removeAddressIdValue').value);
    const endpoint = `/customer/address/remove`;
    const response = await makeRequest(endpoint, 'DELETE', {"address_id": addressId}, true);

    if (response.ok) {
        showNotification('Address removed successfully!', 'success');
        document.getElementById('removeAddressForm').reset();
    } else {
        showNotification(response.data?.detail || 'Failed to remove address!', 'error');
    }

    if (response.data && response.data.token != null) {
        AUTH_TOKEN = response.data.token;
        localStorage.setItem('authToken', AUTH_TOKEN);
    }
    displayResponse('removeAddressResponse', response);
    setFormLoading('removeAddressForm', false);
}

function fillRegisterData() {
    const timestamp = Date.now();
    document.getElementById('registerEmail').value = `customer${timestamp}@example.com`;
    document.getElementById('registerPassword').value = SAMPLE_CREDENTIALS['customer']['password'];
}
