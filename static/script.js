// Main JavaScript for Court Data Fetcher

document.addEventListener('DOMContentLoaded', function() {
    // Handle form submission and show loading spinner
    const searchForm = document.getElementById('searchForm');
    const loadingContainer = document.getElementById('loadingContainer');
    
    if (searchForm) {
        searchForm.addEventListener('submit', function() {
            // Validate form
            const caseType = document.getElementById('caseType').value;
            const caseNumber = document.getElementById('caseNumber').value;
            const year = document.getElementById('year').value;
            const captchaCode = document.getElementById('captchaCode');
            
            if (!caseType || !caseNumber || !year) {
                alert('Please fill in all required fields');
                return false;
            }
            
            if (captchaCode && captchaCode.required && !captchaCode.value) {
                alert('Please enter the CAPTCHA code');
                return false;
            }
            
            // Show loading spinner
            if (loadingContainer) {
                loadingContainer.style.display = 'flex';
            }
            
            return true;
        });
    }
    
    // CAPTCHA refresh functionality
    const refreshCaptchaBtn = document.getElementById('refreshCaptcha');
    const captchaImage = document.getElementById('captchaImage');
    
    if (refreshCaptchaBtn && captchaImage) {
        refreshCaptchaBtn.addEventListener('click', function() {
            // Add timestamp to prevent caching
            const timestamp = new Date().getTime();
            captchaImage.src = '/captcha?' + timestamp;
        });
    }
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Handle case history filtering
    const historySearchInput = document.getElementById('historySearch');
    const historyItems = document.querySelectorAll('.history-item');
    
    if (historySearchInput && historyItems.length > 0) {
        historySearchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            
            historyItems.forEach(function(item) {
                const caseText = item.querySelector('.history-case').textContent.toLowerCase();
                const shouldShow = caseText.includes(searchTerm);
                
                item.style.display = shouldShow ? 'block' : 'none';
            });
        });
    }
});