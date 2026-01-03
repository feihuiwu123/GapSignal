/* GapSignal Trading System - Main JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTables if present
    initDataTables();

    // Initialize tooltips
    initTooltips();

    // Setup auto-refresh if enabled
    setupAutoRefresh();

    // Setup signal filtering
    setupSignalFiltering();

    // Update timestamps
    updateRelativeTimestamps();

    // Setup chart interactions
    setupChartInteractions();
});

function initDataTables() {
    const tables = document.querySelectorAll('.data-table');
    tables.forEach(table => {
        if (typeof $.fn.DataTable !== 'undefined') {
            // Check if DataTable is already initialized on this table
            if ($.fn.DataTable.isDataTable(table)) {
                console.log('DataTable already initialized on', table.id || table.className);
                return; // Skip initialization
            }
            $(table).DataTable({
                pageLength: 25,
                lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, 'All']],
                order: [[0, 'asc']],
                responsive: true,
                autoWidth: false,
                language: {
                    search: 'Search:',
                    lengthMenu: 'Show _MENU_ entries',
                    info: 'Showing _START_ to _END_ of _TOTAL_ entries',
                    paginate: {
                        first: 'First',
                        last: 'Last',
                        next: 'Next',
                        previous: 'Previous'
                    }
                }
            });
        }
    });
}

function initTooltips() {
    if (typeof $.fn.tooltip !== 'undefined') {
        $('[data-toggle="tooltip"]').tooltip();
    }
}

function setupAutoRefresh() {
    const refreshBtn = document.getElementById('refresh-data');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function(e) {
            e.preventDefault();
            refreshData();
        });
    }

    // Auto-refresh every 5 minutes if enabled
    const autoRefreshCheckbox = document.getElementById('auto-refresh');
    if (autoRefreshCheckbox) {
        autoRefreshCheckbox.addEventListener('change', function() {
            if (this.checked) {
                startAutoRefresh();
            } else {
                stopAutoRefresh();
            }
        });
    }
}

let autoRefreshInterval = null;

function startAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    autoRefreshInterval = setInterval(refreshData, 5 * 60 * 1000); // 5 minutes
    showToast('Auto-refresh enabled (every 5 minutes)', 'info');
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
    showToast('Auto-refresh disabled', 'info');
}

function refreshData() {
    const refreshBtn = document.getElementById('refresh-data');
    const originalText = refreshBtn ? refreshBtn.innerHTML : 'Refresh';

    if (refreshBtn) {
        refreshBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Refreshing...';
        refreshBtn.disabled = true;
    }

    // Show loading overlay
    showLoading();

    fetch('/api/refresh')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Data refreshed successfully', 'success');
                // Reload page after short delay to show updated data
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showToast('Error refreshing data: ' + (data.error || 'Unknown error'), 'danger');
            }
        })
        .catch(error => {
            console.error('Error refreshing data:', error);
            showToast('Network error refreshing data', 'danger');
        })
        .finally(() => {
            if (refreshBtn) {
                refreshBtn.innerHTML = originalText;
                refreshBtn.disabled = false;
            }
            hideLoading();
        });
}

function setupSignalFiltering() {
    const filterBtns = document.querySelectorAll('.signal-filter');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const signalType = this.getAttribute('data-signal');
            filterSignals(signalType);
        });
    });
}

function filterSignals(signalType) {
    const rows = document.querySelectorAll('.signal-row');
    const activeFilterBtn = document.querySelector('.signal-filter.active');

    if (activeFilterBtn) {
        activeFilterBtn.classList.remove('active');
    }

    const newActiveBtn = document.querySelector(`.signal-filter[data-signal="${signalType}"]`);
    if (newActiveBtn) {
        newActiveBtn.classList.add('active');
    }

    rows.forEach(row => {
        const rowSignal = row.getAttribute('data-signal') || 'none';
        if (signalType === 'all' || rowSignal === signalType) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function updateRelativeTimestamps() {
    const timeElements = document.querySelectorAll('.time-ago');
    timeElements.forEach(el => {
        const timestamp = parseInt(el.getAttribute('data-timestamp')) * 1000;
        if (timestamp) {
            el.textContent = formatTimeAgo(timestamp);
        }
    });

    // Update every minute
    setInterval(() => {
        timeElements.forEach(el => {
            const timestamp = parseInt(el.getAttribute('data-timestamp')) * 1000;
            if (timestamp) {
                el.textContent = formatTimeAgo(timestamp);
            }
        });
    }, 60000);
}

function formatTimeAgo(timestamp) {
    const now = new Date().getTime();
    const diff = now - timestamp;

    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days > 0) {
        return `${days} day${days > 1 ? 's' : ''} ago`;
    } else if (hours > 0) {
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else if (minutes > 0) {
        return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else {
        return 'just now';
    }
}

function setupChartInteractions() {
    // Chart download buttons
    const downloadBtns = document.querySelectorAll('.chart-download');
    downloadBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const chartId = this.getAttribute('data-chart-id');
            downloadChart(chartId);
        });
    });

    // Chart timeframe selector
    const timeframeSelect = document.getElementById('chart-timeframe');
    if (timeframeSelect) {
        timeframeSelect.addEventListener('change', function() {
            const symbol = this.getAttribute('data-symbol');
            const interval = this.value;
            updateChartTimeframe(symbol, interval);
        });
    }
}

function downloadChart(chartId) {
    const chartElement = document.getElementById(chartId);
    if (chartElement && typeof html2canvas !== 'undefined') {
        html2canvas(chartElement).then(canvas => {
            const link = document.createElement('a');
            link.download = `chart-${chartId}-${new Date().toISOString().slice(0,10)}.png`;
            link.href = canvas.toDataURL('image/png');
            link.click();
        });
    } else {
        showToast('Chart download requires html2canvas library', 'warning');
    }
}

function updateChartTimeframe(symbol, interval) {
    showLoading();

    fetch(`/api/chart/${symbol}?interval=${interval}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update chart with new data
                if (typeof Plotly !== 'undefined' && data.chart) {
                    const chartData = JSON.parse(data.chart);
                    Plotly.react('chart-container', chartData.data, chartData.layout);
                }
                showToast(`Chart updated to ${interval} timeframe`, 'success');
            } else {
                showToast('Error updating chart: ' + (data.error || 'Unknown error'), 'danger');
            }
        })
        .catch(error => {
            console.error('Error updating chart:', error);
            showToast('Network error updating chart', 'danger');
        })
        .finally(() => {
            hideLoading();
        });
}

function showLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    } else {
        // Create loading overlay if it doesn't exist
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        `;
        overlay.innerHTML = `
            <div class="spinner-border text-primary" style="width: 3rem; height: 3rem;" role="status">
                <span class="sr-only">Loading...</span>
            </div>
        `;
        document.body.appendChild(overlay);
    }
}

function hideLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}

function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9998;
        `;
        document.body.appendChild(toastContainer);
    }

    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-delay="5000">
            <div class="toast-header bg-${type} text-white">
                <strong class="mr-auto">GapSignal</strong>
                <small>just now</small>
                <button type="button" class="ml-2 mb-1 close text-white" data-dismiss="toast" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
            <div class="toast-body bg-dark text-white">
                ${message}
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(toastId);

    // Initialize Bootstrap toast if available
    if (typeof $.fn.toast !== 'undefined') {
        $(toastElement).toast('show');

        $(toastElement).on('hidden.bs.toast', function() {
            this.remove();
        });
    } else {
        // Fallback: auto-remove after 5 seconds
        setTimeout(() => {
            toastElement.remove();
        }, 5000);
    }
}

// Utility function to format numbers
function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined) return 'N/A';

    if (num >= 1e9) {
        return (num / 1e9).toFixed(decimals) + 'B';
    } else if (num >= 1e6) {
        return (num / 1e6).toFixed(decimals) + 'M';
    } else if (num >= 1e3) {
        return (num / 1e3).toFixed(decimals) + 'K';
    } else {
        return num.toFixed(decimals);
    }
}

// Utility function to format percentages
function formatPercent(num, decimals = 2) {
    if (num === null || num === undefined) return 'N/A';

    const sign = num > 0 ? '+' : '';
    return sign + num.toFixed(decimals) + '%';
}

// Export functions for use in browser console
window.GapSignal = {
    refreshData,
    showToast,
    formatNumber,
    formatPercent
};