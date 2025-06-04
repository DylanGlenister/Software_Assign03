function initInfo() {
    console.log("Initializing Info Page...");
    document.getElementById('refreshHealthBtn')?.addEventListener('click', fetchAllHealthStatuses);
    
    document.querySelectorAll('#info .nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetSection = this.getAttribute('data-section');
            if (targetSection) {
                const sidebarNavItem = document.querySelector(`.sidebar .nav-item[data-section="${targetSection}"]`);
                sidebarNavItem?.click();
            }
        });
    });

    fetchAllHealthStatuses();
}

async function fetchHealth(endpoint, elementId, serviceName) {
    const statusEl = document.getElementById(elementId);
    if (!statusEl) {
        console.error(`Element ${elementId} not found for ${serviceName} health.`);
        return;
    }
    statusEl.innerHTML = `<span class="text-warning">Checking ${serviceName}...</span>`;
    statusEl.className = 'health-status-box status-checking';

    try {
        const responce = await makeRequest(endpoint, 'GET');
        if (responce.status === 0) {
            throw {"message": "Status 0. Is the backend running?"}
        }

        if (responce.ok) {
            statusEl.innerHTML = `
                <strong class="text-success">${responce.data.status.toUpperCase()}</strong>: ${responce.data.message}<br>
                <small>Time: ${new Date(responce.data.timestamp).toLocaleString()}</small>`;
            statusEl.className = 'health-status-box status-ok';
        } else {
            let httpStatus = responce.status || 'Unknown';
            let mainMessage = `Error fetching ${serviceName} health.`;
            let details = '';

            if (responce.data) {
                let detail = responce.data.detail || responce.data.Detail
                let error =  responce.data.error || responce.data.Error
                if (detail) {
                    mainMessage = detail;
                }
                else if (error){
                    mainMessage = error;
                }
                else{
                    mainMessage = JSON.stringify(responce.data)
                }
            }

            statusEl.innerHTML = `
                <strong class="text-danger">ERROR (HTTP: ${httpStatus})</strong><br>
                <span>${mainMessage}</span>
                ${details ? `<br><small>${details}</small>` : ''}`;
            statusEl.className = 'health-status-box status-error';
            console.error(`Full error responce for ${serviceName}:`, responce);
        }
    } catch (error) {
        statusEl.innerHTML = `
            <strong class="text-danger">NETWORK FAILURE</strong><br>
            <span>Could not connect or fetch ${serviceName} health.</span><br>
            <small>${error.message}</small>`;
        statusEl.className = 'health-status-box status-error';
        console.error(`Network error fetching ${serviceName} health:`, error);
    }
}


function fetchSiteHealthApi() {
    fetchHealth(`/utility/health/backend`, 'backendHealthStatus', 'Backend (API)');
}

function fetchDatabaseHealthApi() {
    fetchHealth(`/utility/health/database`, 'databaseHealthStatus', 'Database');
}

function fetchAllHealthStatuses() {
    fetchSiteHealthApi();
    fetchDatabaseHealthApi();
}