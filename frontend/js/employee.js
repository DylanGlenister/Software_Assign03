function initEmployee() {
    document.getElementById('createProductForm')?.addEventListener('submit', handleCreateProduct);
    document.getElementById('updateProductForm')?.addEventListener('submit', handleUpdateProduct);

    document.getElementById('getAllOrdersBtn')?.addEventListener('click', getAllOrders);

    document.getElementById('createTagForm')?.addEventListener('submit', handleCreateTag);
    document.getElementById('deleteTagForm')?.addEventListener('submit', handleDeleteTag);

    document.getElementById('addProductTagForm')?.addEventListener('submit', handleAddTagToProduct);
    document.getElementById('removeProductTagForm')?.addEventListener('submit', handleRemoveTagFromProduct);

    document.getElementById('addProductImageForm')?.addEventListener('submit', handleAddImageToProduct);
    document.getElementById('deleteImageForm')?.addEventListener('submit', handleDeleteImage);

    populateProductDropdowns();
    populateTagDropdowns();
}

function populateProductDropdowns() {
    setSelectOptions({
        endpoint: '/catalogue/all',
        elements: [
            'updateProductId_ProductSelect',
            'addProductTag_ProductId_ProductSelect',
            'removeProductTag_ProductId_ProductSelect',
            'addProductImage_ProductId_ProductSelect'
        ],
        label: 'Select product',
        key: '',
        errorMessage: 'Could not get products list.',
        requireAuth: true,
        nameKey: "name",
        idKey: "productID"
    });
}

function populateTagDropdowns() {
    setSelectOptions({
        endpoint: '/employee/tags',
        elements: [
            'deleteTagId_TagSelect',
            'addProductTag_TagId_TagSelect',
            'removeProductTag_TagId_TagSelect'
        ],
        label: 'Select tag',
        key: '',
        errorMessage: 'Could not get tags list. Ensure you are logged in.',
        requireAuth: true,
        nameKey: "name",
        idKey: "tagID"
    });
}


// --- Product Handlers ---
async function handleCreateProduct(e) {
    e.preventDefault();
    setFormLoading('createProductForm', true);
    const name = document.getElementById('createProductName').value;
    const description = document.getElementById('createProductDescription').value;
    const price = parseFloat(document.getElementById('createProductPrice').value);
    const stock = parseInt(document.getElementById('createProductStock').value);
    const available = parseInt(document.getElementById('createProductAvailable').value);
    const payload = { name, description, price, stock, available };

    const response = await makeRequest('/employee/products/create', 'POST', payload, true);
    if (response.ok) {
        showNotification('Product created successfully!', 'success');
        document.getElementById('createProductForm').reset();
        populateProductDropdowns();
    } else {
        showNotification(response.data?.detail || 'Failed to create product!', 'error');
    }
    displayResponse('createProductResponse', response);
    setFormLoading('createProductForm', false);
}

async function handleUpdateProduct(e) {
    e.preventDefault();
    setFormLoading('updateProductForm', true);
    const productId = document.getElementById('updateProductId_ProductSelect').value;
    if (!productId) {
        showNotification('Please select a product to update.', 'error');
        setFormLoading('updateProductForm', false); return;
    }
    const payload = {};
    const name = document.getElementById('updateProductName').value;
    const description = document.getElementById('updateProductDescription').value;
    const priceString = document.getElementById('updateProductPrice').value;
    const stockString = document.getElementById('updateProductStock').value;
    const availableString = document.getElementById('updateProductAvailable').value;
    const discontinuedString = document.getElementById('updateProductDiscontinued').value;

    if (name) payload.name = name;
    if (description) payload.description = description;
    if (priceString) payload.price = parseFloat(priceString);
    if (stockString) payload.stock = parseInt(stockString);
    if (availableString) payload.available = parseInt(availableString);
    if (discontinuedString !== "") payload.discontinued = (discontinuedString === "true");

    if (Object.keys(payload).length === 0) {
        showNotification('Please provide at least one field to update.', 'info');
        setFormLoading('updateProductForm', false); return;
    }

    console.log(productId)

    const response = await makeRequest(`/employee/products/update/${productId}`, 'PATCH', payload, true);
    if (response.ok) {
        showNotification('Product updated successfully!', 'success');
        document.getElementById('updateProductForm').reset();
        document.getElementById('updateProductId_ProductSelect').value = "";
        populateProductDropdowns();
    } else {
        showNotification(response.data?.detail || 'Failed to update product!', 'error');
    }
    displayResponse('updateProductResponse', response);
    setFormLoading('updateProductForm', false);
}

// --- Order Handler ---
async function getAllOrders() {
    setFormLoading('getAllOrdersBtn', true);
    const response = await makeRequest('/employee/orders', 'GET', null, true);
    if (response.ok) {
        showNotification('Orders retrieved successfully!', 'success');
        if (response.data && Array.isArray(response.data)) {
            createTable('getAllOrdersResponse', response.data.length > 0 ? response.data : []);
        } else {
             const container = document.getElementById('getAllOrdersResponse').querySelector('.table-container');
             if(container) container.innerHTML = "<p>Orders data not in expected format.</p>";
        }
    } else {
        showNotification(response.data?.detail || 'Failed to retrieve orders!', 'error');
    }
    displayResponse('getAllOrdersResponse', response);
    setFormLoading('getAllOrdersBtn', false);
}

// --- Tag Handlers ---
async function handleCreateTag(e) {
    e.preventDefault();
    setFormLoading('createTagForm', true);
    const name = document.getElementById('createTagName').value;
    const response = await makeRequest('/employee/tags/create', 'POST', { name }, true);
    if (response.ok) {
        showNotification('Tag created successfully!', 'success');
        document.getElementById('createTagForm').reset();
        populateTagDropdowns();
    } else {
        showNotification(response.data?.detail || 'Failed to create tag!', 'error');
    }
    displayResponse('createTagResponse', response);
    setFormLoading('createTagForm', false);
}

async function handleDeleteTag(e) {
    e.preventDefault();
    setFormLoading('deleteTagForm', true);
    const tagId = document.getElementById('deleteTagId_TagSelect').value;
    if (!tagId) {
        showNotification('Please select a tag to delete.', 'error');
        setFormLoading('deleteTagForm', false); return;
    }
    const response = await makeRequest(`/employee/tags/delete/${tagId}`, 'DELETE', null, true);
    if (response.ok) {
        showNotification('Tag deleted successfully!', 'success');
        document.getElementById('deleteTagForm').reset();
        populateTagDropdowns();
    } else {
        showNotification(response.data?.detail || 'Failed to delete tag!', 'error');
    }
    displayResponse('deleteTagResponse', response);
    setFormLoading('deleteTagForm', false);
}

// --- ProductTag Handlers ---
async function handleAddTagToProduct(e) {
    e.preventDefault();
    setFormLoading('addProductTagForm', true);
    const productId = document.getElementById('addProductTag_ProductId_ProductSelect').value;
    const tagId = document.getElementById('addProductTag_TagId_TagSelect').value;
    if (!productId || !tagId) {
        showNotification('Please select both a product and a tag.', 'error');
        setFormLoading('addProductTagForm', false); return;
    }
    const response = await makeRequest(`/employee/products/${productId}/tags/add/${tagId}`, 'POST', null, true);
    if (response.ok) {
        showNotification('Tag added to product successfully!', 'success');
        document.getElementById('addProductTagForm').reset();
    } else {
        showNotification(response.data?.detail || 'Failed to add tag to product!', 'error');
    }
    displayResponse('addProductTagResponse', response);
    setFormLoading('addProductTagForm', false);
}

async function handleRemoveTagFromProduct(e) {
    e.preventDefault();
    setFormLoading('removeProductTagForm', true);
    const productId = document.getElementById('removeProductTag_ProductId_ProductSelect').value;
    const tagId = document.getElementById('removeProductTag_TagId_TagSelect').value;
     if (!productId || !tagId) {
        showNotification('Please select both a product and a tag to remove.', 'error');
        setFormLoading('removeProductTagForm', false); return;
    }
    const response = await makeRequest(`/employee/products/${productId}/tags/remove/${tagId}`, 'DELETE', null, true);
    if (response.ok) {
        showNotification('Tag removed from product successfully!', 'success');
        document.getElementById('removeProductTagForm').reset();
    } else {
        showNotification(response.data?.detail || 'Failed to remove tag from product!', 'error');
    }
    displayResponse('removeProductTagResponse', response);
    setFormLoading('removeProductTagForm', false);
}

// --- Image Handlers ---
async function handleAddImageToProduct(e) {
    e.preventDefault();
    setFormLoading('addProductImageForm', true);
    const productId = document.getElementById('addProductImage_ProductId_ProductSelect').value;
    const url = document.getElementById('addProductImage_Url').value;
    if (!productId || !url) {
        showNotification('Please select a product and enter an image URL.', 'error');
        setFormLoading('addProductImageForm', false); return;
    }
    const response = await makeRequest(`/employee/products/${productId}/images/add`, 'POST', { url }, true);
    if (response.ok) {
        showNotification('Image added to product successfully!', 'success');
        document.getElementById('addProductImageForm').reset();
    } else {
        showNotification(response.data?.detail || 'Failed to add image!', 'error');
    }
    displayResponse('addProductImageResponse', response);
    setFormLoading('addProductImageForm', false);
}

async function handleDeleteImage(e) {
    e.preventDefault();
    setFormLoading('deleteImageForm', true);
    const imageId = document.getElementById('deleteImageId').value;
    if (!imageId) {
        showNotification('Please enter an Image ID to delete.', 'error');
        setFormLoading('deleteImageForm', false); return;
    }
    const response = await makeRequest(`/employee/images/${imageId}`, 'DELETE', null, true);
    if (response.ok) {
        showNotification('Image deleted successfully!', 'success');
        document.getElementById('deleteImageForm').reset();
    } else {
        showNotification(response.data?.detail || 'Failed to delete image!', 'error');
    }
    displayResponse('deleteImageResponse', response);
    setFormLoading('deleteImageForm', false);
}
