document.addEventListener('DOMContentLoaded', function() {
    const roleSelect = document.getElementById('id_role');
    const operationTypeInput = document.getElementById('operationType');
    const operationNotification = document.getElementById('operationNotification');
    const operationText = document.getElementById('operationText');
    const userSection = document.getElementById('userAccountSection');
    const personnelSection = document.getElementById('personnelInfoSection');
    const adminRestrictionGroup = document.getElementById('adminRestrictionGroup');
    const hiddenRoleValue = document.getElementById('hidden_role_value');
    
    // Check if we're in edit mode with linked personnel
    const isEditMode = operationTypeInput && (operationTypeInput.value === 'edit_both' || operationTypeInput.value === 'edit_user' || operationTypeInput.value === 'edit_personnel');
    const hasLinkedPersonnel = operationTypeInput && operationTypeInput.value === 'edit_both';
    
    function updateOperationBasedOnRole() {
        // Get role from select (create mode) or hidden input (edit mode)
        let role = '';
        if (roleSelect && roleSelect.value) {
            role = roleSelect.value;
        } else if (hiddenRoleValue && hiddenRoleValue.value) {
            role = hiddenRoleValue.value;
        }
        
        if (!role || !operationTypeInput) return;
        
        // In edit mode, preserve the original operation type
        if (isEditMode) {
            // Don't change operation_type in edit mode
            // Just update visibility based on current operation_type
            if (hasLinkedPersonnel) {
                // edit_both: Show both sections
                if (userSection) userSection.style.display = 'block';
                if (personnelSection) personnelSection.style.display = 'block';
            } else if (operationTypeInput.value === 'edit_user') {
                // edit_user: Show only user section
                if (userSection) userSection.style.display = 'block';
                if (personnelSection) personnelSection.style.display = 'none';
            } else if (operationTypeInput.value === 'edit_personnel') {
                // edit_personnel: Show only personnel section
                if (userSection) userSection.style.display = 'none';
                if (personnelSection) personnelSection.style.display = 'block';
            }
        } else {
            // Create mode: Set operation type and visibility based on role
            let operationType = '';
            let notificationClass = '';
            let notificationMessage = '';
            
            // Set operation type and notification based on role
            if (role === 'personnel') {
                operationType = 'create_personnel_only';
                notificationClass = 'alert-info';
                notificationMessage = '<i class="fas fa-user"></i> <strong>Personnel Registration:</strong> Creating personnel record only (no user login account)';
                // Hide user section, show personnel section
                if (userSection) userSection.style.display = 'none';
                if (personnelSection) personnelSection.style.display = 'block';
            } else if (role === 'armorer' || role === 'admin') {
                operationType = 'create_user_with_personnel';
                notificationClass = 'alert-info';
                const roleLabel = role === 'armorer' ? 'Armorer' : 'Administrator';
                notificationMessage = '<i class="fas fa-user-shield"></i> <strong>' + roleLabel + ' Registration:</strong> Creating user login + personnel record';
                // Show both sections
                if (userSection) userSection.style.display = 'block';
                if (personnelSection) personnelSection.style.display = 'block';
            }
            
            // Update operation type hidden input
            operationTypeInput.value = operationType;
            
            // Update notification
            if (operationNotification && notificationMessage) {
                operationNotification.className = 'alert ' + notificationClass;
                operationText.innerHTML = notificationMessage;
                operationNotification.style.display = 'block';
            } else if (operationNotification) {
                operationNotification.style.display = 'none';
            }
        }
        
        // Show/hide admin restriction field
        if (adminRestrictionGroup) {
            if (role === 'admin') {
                adminRestrictionGroup.style.display = 'block';
            } else {
                adminRestrictionGroup.style.display = 'none';
            }
        }
    }
    
    // Listen to role changes (works in both create and edit modes when roleSelect exists)
    if (roleSelect) {
        roleSelect.addEventListener('change', updateOperationBasedOnRole);
    }
    
    // Set initial state (works in both create and edit modes)
    updateOperationBasedOnRole();
    
    // Enhanced Form Validation with Visual Feedback
    const form = document.getElementById('universalForm');
    const formControls = document.querySelectorAll('.form-control');
    
    // Real-time validation for form controls
    formControls.forEach(control => {
        // Add focus effect
        control.addEventListener('focus', function() {
            this.classList.add('field-focused');
        });
        
        control.addEventListener('blur', function() {
            this.classList.remove('field-focused');
            validateField(this);
        });
        
        // Debounced input handler to prevent performance issues
        let inputTimeout;
        control.addEventListener('input', function() {
            // Clear error state while typing (immediate)
            if (this.classList.contains('is-invalid')) {
                this.classList.remove('is-invalid');
            }
            
            // Debounce validation to avoid excessive processing
            clearTimeout(inputTimeout);
            inputTimeout = setTimeout(() => {
                // Optional: You can add validation here if needed
                // For now, we just clear the error state
            }, 300);
        });
    });
    
    function validateField(field) {
        const value = field.value.trim();
        const required = field.hasAttribute('required');
        const type = field.type;
        
        // Check if field is required and empty
        if (required && !value) {
            field.classList.add('is-invalid');
            field.classList.remove('is-valid');
            return false;
        }
        
        // Email validation
        if (type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                field.classList.add('is-invalid');
                field.classList.remove('is-valid');
                return false;
            }
        }
        
        // Mark valid if passes all checks
        if (value) {
            field.classList.add('is-valid');
            field.classList.remove('is-invalid');
        }
        
        return true;
    }
    
    // Progress indicator updates (for registration forms)
    const progressSteps = document.querySelectorAll('.progress-step');
    
    function updateProgress(currentStep) {
        progressSteps.forEach((step, index) => {
            if (index < currentStep) {
                step.classList.add('completed');
                step.classList.remove('active');
            } else if (index === currentStep) {
                step.classList.add('active');
                step.classList.remove('completed');
            } else {
                step.classList.remove('active', 'completed');
            }
        });
    }
    
    // Update progress based on form interaction
    if (roleSelect) {
        roleSelect.addEventListener('change', function() {
            updateProgress(1); // Move to Account Info step
        });
    }
    
    // Monitor form sections for progress
    const usernameField = document.getElementById('id_username');
    if (usernameField) {
        usernameField.addEventListener('blur', function() {
            if (this.value) {
                updateProgress(2); // Move to Personnel Data step
            }
        });
    }
    
    const surnameField = document.getElementById('id_surname');
    if (surnameField) {
        surnameField.addEventListener('blur', function() {
            if (this.value) {
                updateProgress(3); // Move to Review step
            }
        });
    }
    
    // Auto-format phone number with debouncing
    const telField = document.getElementById('id_tel');
    if (telField) {
        let telTimeout;
        telField.addEventListener('input', function() {
            clearTimeout(telTimeout);
            telTimeout = setTimeout(() => {
                let value = this.value.replace(/\D/g, ''); // Remove non-digits
                
                // Auto-format to Philippine number
                if (value.length > 0 && !value.startsWith('63')) {
                    if (value.startsWith('0')) {
                        value = '63' + value.substring(1);
                    } else if (value.startsWith('9')) {
                        value = '63' + value;
                    }
                }
                
                // Format display (show +639XXXXXXXXX)
                if (value.length >= 2) {
                    this.value = '+' + value;
                }
            }, 500);
        });
    }
    
    // Serial number numeric validation with debouncing
    const serialField = document.getElementById('id_serial');
    if (serialField) {
        let serialTimeout;
        // Allow only numeric input
        serialField.addEventListener('input', function() {
            clearTimeout(serialTimeout);
            serialTimeout = setTimeout(() => {
                // Remove non-numeric characters
                this.value = this.value.replace(/\D/g, '');
                
                // Clear error state while typing
                if (this.classList.contains('is-invalid')) {
                    this.classList.remove('is-invalid');
                    const errorSpan = this.parentElement.querySelector('.error');
                    if (errorSpan && errorSpan.textContent.includes('numeric')) {
                        errorSpan.remove();
                    }
                }
            }, 300);
        });
        
        serialField.addEventListener('blur', function() {
            const value = this.value.trim();
            
            // Validate that it contains only numbers
            if (value && !/^\d+$/.test(value)) {
                this.classList.add('is-invalid');
                const errorSpan = this.parentElement.querySelector('.error');
                if (!errorSpan) {
                    const newError = document.createElement('span');
                    newError.className = 'error';
                    newError.textContent = 'Serial number must contain only numeric digits';
                    this.parentElement.appendChild(newError);
                }
            } else if (value) {
                this.classList.add('is-valid');
                this.classList.remove('is-invalid');
                const errorSpan = this.parentElement.querySelector('.error');
                if (errorSpan && errorSpan.textContent.includes('numeric')) {
                    errorSpan.remove();
                }
            }
        });
    }

    // Form submission with loading state
    if (form) {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            
            // Add loading state
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                
                // Re-enable after 5 seconds (fallback)
                setTimeout(function() {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }, 5000);
            }
        });
    }
    
    // Character counter for textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        const maxLength = textarea.getAttribute('maxlength');
        if (maxLength) {
            const counter = document.createElement('div');
            counter.className = 'char-counter';
            counter.style.fontSize = '0.875rem';
            counter.style.color = '#6b7280';
            counter.style.marginTop = '0.25rem';
            counter.style.textAlign = 'right';
            
            const updateCounter = () => {
                const remaining = maxLength - textarea.value.length;
                counter.textContent = `${remaining} characters remaining`;
                if (remaining < 20) {
                    counter.style.color = '#ef4444';
                } else {
                    counter.style.color = '#6b7280';
                }
            };
            
            textarea.addEventListener('input', updateCounter);
            textarea.parentElement.appendChild(counter);
            updateCounter();
        }
    });
});
