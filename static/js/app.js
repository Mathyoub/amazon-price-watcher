// Amazon Price Watcher Web Interface JavaScript

// Utility functions
function showLoading(element) {
    element.classList.add('loading');
}

function hideLoading(element) {
    element.classList.remove('loading');
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleString();
}

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Form validation for add product
document.addEventListener('DOMContentLoaded', function() {
    const addForm = document.querySelector('form[action*="add"]');
    if (addForm) {
        addForm.addEventListener('submit', function(e) {
            const urlInput = document.getElementById('url');
            const url = urlInput.value.trim();

            if (!url.includes('amazon.com')) {
                e.preventDefault();
                alert('Please enter a valid Amazon URL');
                urlInput.focus();
                return false;
            }
        });
    }
});

// Refresh data functionality
function refreshData() {
    location.reload();
}

// Copy URL functionality
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // Show toast or notification
        console.log('URL copied to clipboard');
    });
}

// Format product titles for display
function truncateTitle(title, maxLength = 60) {
    if (title.length <= maxLength) return title;
    return title.substring(0, maxLength) + '...';
}

// Price change indicator
function getPriceChangeClass(change) {
    if (change > 0) return 'price-up';
    if (change < 0) return 'price-down';
    return '';
}

// Real-time updates (if needed)
function startRealTimeUpdates() {
    // Could implement WebSocket or polling here
    console.log('Real-time updates not implemented yet');
}