// --- Global state for the custom tag input ---
let allCatalogueTags = []; 
let selectedCatalogueTagNames = new Set(); 

function initCatalogue() {
    document.getElementById('listAllProductsForm')?.addEventListener('submit', handleListAllProducts);
    document.getElementById('searchProductsForm')?.addEventListener('submit', handleSearchProducts);
    document.getElementById('getProductsByTagsForm')?.addEventListener('submit', handleGetProductsByTags);
    document.getElementById('getProductByIdForm')?.addEventListener('submit', handleGetProductById);
    document.getElementById('getAllTagsBtn')?.addEventListener('click', getAllTags);

    setupCustomTagInput();
}

async function setupCustomTagInput() {
    const inputTrigger = document.getElementById('catalogueTagsInputTrigger');
    const dropdown = document.getElementById('availableCatalogueTagsDropdown');

    try {
        const response = await makeRequest('/catalogue/tags', 'GET', null, true); 
        if (response.ok && Array.isArray(response.data)) {
            allCatalogueTags = response.data.map(tag => ({ name: tag.name, id: tag.tagID }));
            renderAvailableTagsDropdown();
        } else {
            console.error("Failed to fetch tags for catalogue input:", response.data?.detail || "Unknown error");
            dropdown.innerHTML = '<div class="tag-item">Error loading tags.</div>';
        }
    } catch (error) {
        console.error("Error fetching tags:", error);
        dropdown.innerHTML = '<div class="tag-item">Error loading tags.</div>';
    }

    inputTrigger.addEventListener('focus', () => {
        dropdown.style.display = 'block';
        renderAvailableTagsDropdown(); 
    });

    inputTrigger.addEventListener('blur', () => {
        setTimeout(() => {
            if (!dropdown.matches(':hover')) { 
                 dropdown.style.display = 'none';
            }
        }, 200);
    });
    
    inputTrigger.addEventListener('input', () => {
        renderAvailableTagsDropdown(inputTrigger.value.toLowerCase());
    });

    inputTrigger.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
        }
    });
}

async function getAllTags() {
    const response = await makeRequest('/catalogue/tags', 'GET', null, true);
    if (response.ok) {
        showNotification('Tags retrieved successfully!', 'success');
        if (response.data && Array.isArray(response.data)) {
            createTable('getAllTagsResponse', response.data.length > 0 ? response.data : []);
        } else {
            const container = document.getElementById('getAllTagsResponse').querySelector('.table-container');
            if(container) container.innerHTML = "<p>Tags data not in expected format.</p>";
        }
    } else {
        showNotification(response.data?.detail || 'Failed to retrieve tags!', 'error');
    }
    displayResponse('getAllTagsResponse', response);
}

function renderAvailableTagsDropdown(filterText = '') {
    const dropdown = document.getElementById('availableCatalogueTagsDropdown');
    dropdown.innerHTML = '';

    const filteredTags = allCatalogueTags.filter(tag => 
        tag.name.toLowerCase().includes(filterText)
    );

    if (filteredTags.length === 0 && filterText) {
        dropdown.innerHTML = '<div class="tag-item">No tags match your filter.</div>';
        return;
    }
    if (filteredTags.length === 0 && !filterText && allCatalogueTags.length > 0) {
         dropdown.innerHTML = '<div class="tag-item">All tags selected or no tags available.</div>';
        return;
    }
     if (allCatalogueTags.length === 0 && !filterText) {
        dropdown.innerHTML = '<div class="tag-item">No tags available to select.</div>';
        return;
    }


    filteredTags.forEach(tag => {
        const item = document.createElement('div');
        item.classList.add('tag-item');
        item.textContent = tag.name;
        item.dataset.tagName = tag.name;

        if (selectedCatalogueTagNames.has(tag.name)) {
            item.classList.add('selected');
            item.style.display = 'none';
        }

        item.addEventListener('mousedown', (e) => { 
            e.preventDefault();
            toggleCatalogueTagSelection(tag.name);
            document.getElementById('catalogueTagsInputTrigger').value = '';
            renderAvailableTagsDropdown()
            document.getElementById('catalogueTagsInputTrigger').focus();
        });
        dropdown.appendChild(item);
    });
}

function toggleCatalogueTagSelection(tagName) {
    if (selectedCatalogueTagNames.has(tagName)) {
        selectedCatalogueTagNames.delete(tagName);
    } else {
        selectedCatalogueTagNames.add(tagName);
    }
    renderSelectedCatalogueTagPills();
}

function renderSelectedCatalogueTagPills() {
    const container = document.getElementById('selectedCatalogueTagsContainer');
    container.innerHTML = '';

    selectedCatalogueTagNames.forEach(tagName => {
        const pill = document.createElement('div');
        pill.classList.add('tag-pill');
        pill.textContent = tagName;

        const removeBtn = document.createElement('span');
        removeBtn.classList.add('remove-tag');
        removeBtn.innerHTML = '×';
        removeBtn.title = `Remove ${tagName}`;
        removeBtn.addEventListener('click', () => {
            selectedCatalogueTagNames.delete(tagName);
            renderSelectedCatalogueTagPills();
            renderAvailableTagsDropdown();
        });

        pill.appendChild(removeBtn);
        container.appendChild(pill);
    });
}


async function handleGetProductsByTags(e) {
    e.preventDefault();
    setFormLoading('getProductsByTagsForm', true);

    const selectedTagNamesArray = Array.from(selectedCatalogueTagNames);

    const availableOnly = document.getElementById('taggedAvailableOnly').value === 'true';
    const sortBy = document.getElementById('taggedSortBy').value;

    if (selectedTagNamesArray.length === 0) {
        showNotification('Please select at least one tag.', 'error');
        setFormLoading('getProductsByTagsForm', false);
        return;
    }

    let tagsQueryParam = selectedTagNamesArray.map(tagName => `t=${encodeURIComponent(tagName)}`).join('&');
    let queryString = `?${tagsQueryParam}&available_only=${availableOnly}`;
    if (sortBy) {
        queryString += `&sort_by=${sortBy}`;
    }

    const response = await makeRequest(`/catalogue/tagged${queryString}`, 'GET', null, false);

    if (response.ok && response.data) {
        showNotification('Products by tags retrieved!', 'success');
        createTable('getProductsByTagsResponse', Array.isArray(response.data) ? response.data : []);
    } else {
        showNotification(response.data?.detail || 'Failed to get products by tags!', 'error');
        createTable('getProductsByTagsResponse', []);
    }
    displayResponse('getProductsByTagsResponse', response);
    setFormLoading('getProductsByTagsForm', false);
}

async function handleListAllProducts(e) {
    e.preventDefault();
    setFormLoading('listAllProductsForm', true);

    const response = await makeRequest(`/catalogue/all`, 'GET', null, false); 
    if (response.ok && response.data) {
        showNotification('Products retrieved successfully!', 'success');
        createTable('listAllProductsResponse', Array.isArray(response.data) ? response.data : []);
    } else {
        showNotification(response.data?.detail || 'Failed to retrieve products!', 'error');
        createTable('listAllProductsResponse', []); 
    }
    displayResponse('listAllProductsResponse', response);
    setFormLoading('listAllProductsForm', false);
}

async function handleSearchProducts(e) {
    e.preventDefault();
    setFormLoading('searchProductsForm', true);
    const query = document.getElementById('searchQuery').value;
    const availableOnly = document.getElementById('searchAvailableOnly').value === 'true';
    const sortBy = document.getElementById('searchSortBy').value;
    let queryString = `?query=${encodeURIComponent(query)}&available_only=${availableOnly}`;
    if (sortBy) {
        queryString += `&sort_by=${sortBy}`;
    }
    const response = await makeRequest(`/catalogue/search${queryString}`, 'GET', null, false); 
    if (response.ok && response.data) {
        showNotification('Search results retrieved!', 'success');
        createTable('searchProductsResponse', Array.isArray(response.data) ? response.data : []);
    } else {
        showNotification(response.data?.detail || 'Failed to search products!', 'error');
        createTable('searchProductsResponse', []);
    }
    displayResponse('searchProductsResponse', response);
    setFormLoading('searchProductsForm', false);
}

async function handleGetProductById(e) {
    e.preventDefault();
    setFormLoading('getProductByIdForm', true);
    const productId = document.getElementById('getProductId').value;
    if (!productId) {
        showNotification('Please enter a Product ID.', 'error');
        setFormLoading('getProductByIdForm', false);
        return;
    }
    const response = await makeRequest(`/catalogue/${productId}`, 'GET', null, false); 
    if (response.ok && response.data) {
        showNotification('Product retrieved successfully!', 'success');
        createTable('getProductByIdResponse', response.data ? [response.data] : []);
    } else {
        showNotification(response.data?.detail || `Failed to retrieve product ${productId}!`, 'error');
        createTable('getProductByIdResponse', []);
    }
    displayResponse('getProductByIdResponse', response);
    setFormLoading('getProductByIdForm', false);
}