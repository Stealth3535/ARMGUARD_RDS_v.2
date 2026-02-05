// Global JavaScript for ArmGuard

document.addEventListener('DOMContentLoaded', function() {
    console.log('ArmGuard application loaded');
    
    // Enhanced login form handling
    const loginForm = document.querySelector('form[action*="login"]');
    if (loginForm) {
        const submitBtn = document.getElementById('login-btn');
        const btnText = document.querySelector('.btn-text');
        const btnSpinner = document.querySelector('.btn-spinner');
        
        loginForm.addEventListener('submit', function(e) {
            if (submitBtn && btnText && btnSpinner) {
                submitBtn.disabled = true;
                btnText.style.display = 'none';
                btnSpinner.style.display = 'inline';
                
                // Reset after 10 seconds in case of network issues
                setTimeout(() => {
                    submitBtn.disabled = false;
                    btnText.style.display = 'inline';
                    btnSpinner.style.display = 'none';
                }, 10000);
            }
        });
        
        // Add real-time validation feedback
        const inputs = loginForm.querySelectorAll('input[required]');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (this.value.trim() === '') {
                    this.style.borderColor = '#dc3545';
                    this.setAttribute('aria-invalid', 'true');
                } else {
                    this.style.borderColor = '#28a745';
                    this.setAttribute('aria-invalid', 'false');
                }
            });
            
            input.addEventListener('input', function() {
                if (this.value.trim() !== '') {
                    this.style.borderColor = '#e1e5e9';
                    this.removeAttribute('aria-invalid');
                }
            });
        });
    }
    
    // Auto-focus management
    const autofocusElement = document.querySelector('[autofocus]');
    if (autofocusElement) {
        setTimeout(() => autofocusElement.focus(), 100);
    }
    
    // Accessibility improvements
    document.addEventListener('keydown', function(e) {
        // ESC key to clear form errors
        if (e.key === 'Escape') {
            const alerts = document.querySelectorAll('.alert-error');
            alerts.forEach(alert => alert.style.display = 'none');
        }
    });
    
    // Performance monitoring
    if ('performance' in window) {
        window.addEventListener('load', function() {
            const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
            console.log(`ArmGuard loaded in ${loadTime}ms`);
        });
    }
});
