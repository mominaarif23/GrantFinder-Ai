/**
 * GrantFinder AI — Universal Form & Input Validation Engine
 * Institutional validation rules, real-time micro-feedback, and form submission guards.
 * Strict Zero Emoji Policy.
 */

(function() {
    'use strict';

    const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
    const URL_REGEX = /^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/;
    const PHONE_REGEX = /^[+]?[\d\s\-().]{7,20}$/;

    /**
     * Determine validation error for a single input element.
     * Returns null if valid, or a descriptive string message if invalid.
     */
    function getValidationErrorMessage(input) {
        if (!input || input.disabled || input.type === 'hidden') {
            return null;
        }

        const value = (input.value !== undefined) ? input.value.trim() : '';
        const isRequired = input.hasAttribute('required') || input.dataset.required === 'true';
        const type = (input.getAttribute('type') || '').toLowerCase();
        const id = (input.id || '').toLowerCase();
        const name = (input.name || '').toLowerCase();
        const customValidate = input.dataset.validate;

        // 1. Required Check
        if (isRequired && !value) {
            const label = getFieldLabel(input);
            return `${label} is required.`;
        }

        // If not required and empty, skip format validation
        if (!isRequired && !value) {
            return null;
        }

        // 2. Email Validation
        if (type === 'email' || customValidate === 'email' || id === 'email' || name === 'email' || id.includes('email') || name.includes('email')) {
            if (!EMAIL_REGEX.test(value)) {
                return 'Please enter a valid email address (e.g. applicant@university.edu).';
            }
        }

        // 3. Password Validation
        if (type === 'password' && (id === 'password' || name === 'password' || id === 'newpassword' || name === 'new_password')) {
            const minLen = parseInt(input.getAttribute('minlength') || '6', 10);
            if (value.length < minLen) {
                return `Password must be at least ${minLen} characters long.`;
            }
        }

        // 4. Confirm Password Match
        const matchTargetId = input.dataset.match || (id.includes('confirm') ? 'password' : (id.includes('confirmnew') ? 'newpassword' : null));
        if (matchTargetId) {
            const targetEl = document.getElementById(matchTargetId) || document.querySelector(`input[name="${matchTargetId}"]`);
            if (targetEl && targetEl.value !== input.value) {
                return 'Passwords do not match.';
            }
        }

        // 5. Name Validation
        if (id === 'name' || name === 'name' || id === 'profilename' || id === 'wizardname' || customValidate === 'name') {
            if (value.length < 2) {
                return 'Please enter your full legal name (at least 2 characters).';
            }
            if (!/^[a-zA-Z\s.'\-]+$/.test(value)) {
                return 'Name should only contain letters, spaces, hyphens, and periods.';
            }
        }

        // 6. URL Validation
        if (type === 'url' || customValidate === 'url' || id.includes('link') || name.includes('link') || id.includes('source_link') || name.includes('source_link')) {
            if (!URL_REGEX.test(value)) {
                return 'Please enter a valid website URL starting with http:// or https://';
            }
        }

        // 7. Phone Number Validation
        if (type === 'tel' || customValidate === 'phone' || id.includes('phone') || name.includes('phone')) {
            if (!PHONE_REGEX.test(value)) {
                return 'Please enter a valid contact phone number with country code (e.g. +92 300 1234567).';
            }
        }

        // 8. 6-Digit OTP / Verification Code
        if (id === 'resetcode' || name === 'reset_code' || customValidate === 'otp') {
            const cleanDigits = value.replace(/\s+/g, '');
            if (cleanDigits.length < 6) {
                return 'Verification code must be at least 6 digits.';
            }
        }

        // 9. CGPA Validation (when numeric CGPA is specified)
        if (id === 'cgpa' || customValidate === 'cgpa') {
            const num = parseFloat(value);
            if (isNaN(num) || num < 0.0 || num > 4.0) {
                return 'CGPA must be a valid number between 0.0 and 4.0.';
            }
        }

        // 10. General minlength / maxlength
        const minLen = input.getAttribute('minlength');
        if (minLen && value.length < parseInt(minLen, 10)) {
            const label = getFieldLabel(input);
            return `${label} must be at least ${minLen} characters.`;
        }

        return null;
    }

    /**
     * Extract human-readable label for the field.
     */
    function getFieldLabel(input) {
        if (input.dataset.label) return input.dataset.label;
        if (input.id) {
            const labelEl = document.querySelector(`label[for="${input.id}"]`);
            if (labelEl) {
                return labelEl.innerText.replace(/[*:]/g, '').trim();
            }
        }
        if (input.placeholder && !input.placeholder.includes('••••')) {
            return input.placeholder.replace(/[.e.g]/g, '').trim();
        }
        return 'This field';
    }

    /**
     * Find or create the field error container element.
     */
    function getOrCreateErrorElement(input) {
        const errorId = `err_${input.id || input.name || Math.random().toString(36).substring(2, 7)}`;
        let errorEl = document.getElementById(errorId);

        if (!errorEl) {
            errorEl = document.createElement('div');
            errorEl.id = errorId;
            errorEl.className = 'field-error-msg hidden';

            // Insert after input or after its relative container wrapper (e.g. password toggle wrapper)
            const parent = input.closest('.relative') || input.parentElement;
            if (parent && parent.parentElement) {
                if (parent.classList.contains('relative') || parent.classList.contains('flex')) {
                    parent.insertAdjacentElement('afterend', errorEl);
                } else {
                    input.insertAdjacentElement('afterend', errorEl);
                }
            } else {
                input.insertAdjacentElement('afterend', errorEl);
            }
        }
        return errorEl;
    }

    /**
     * Validate an individual input element.
     */
    function validateField(input) {
        if (!input || input.type === 'hidden' || input.disabled) return true;

        const errorMsg = getValidationErrorMessage(input);
        const errorEl = getOrCreateErrorElement(input);

        if (errorMsg) {
            input.classList.add('input-error');
            input.classList.remove('input-valid');
            if (errorEl) {
                errorEl.innerText = errorMsg;
                errorEl.classList.remove('hidden');
            }
            return false;
        } else {
            input.classList.remove('input-error');
            if (input.value && input.value.trim().length > 0) {
                input.classList.add('input-valid');
            } else {
                input.classList.remove('input-valid');
            }
            if (errorEl) {
                errorEl.innerText = '';
                errorEl.classList.add('hidden');
            }
            return true;
        }
    }

    /**
     * Clear all errors for a given input element.
     */
    function clearFieldError(input) {
        if (!input) return;
        input.classList.remove('input-error');
        const errorId = `err_${input.id || input.name}`;
        const errorEl = document.getElementById(errorId);
        if (errorEl) {
            errorEl.innerText = '';
            errorEl.classList.add('hidden');
        }
    }

    /**
     * Validate all fields within a form or container element.
     */
    function validateForm(form) {
        if (!form) return true;

        const elements = Array.from(form.querySelectorAll('input, select, textarea'));
        let isValid = true;
        let firstInvalid = null;

        elements.forEach(el => {
            if (el.type === 'hidden' || el.disabled || el.type === 'submit' || el.type === 'button') {
                return;
            }
            const fieldValid = validateField(el);
            if (!fieldValid) {
                isValid = false;
                if (!firstInvalid) {
                    firstInvalid = el;
                }
            }
        });

        if (!isValid && firstInvalid) {
            firstInvalid.focus();
            form.classList.remove('animate-shake');
            void form.offsetWidth; // trigger reflow
            form.classList.add('animate-shake');
            setTimeout(() => form.classList.remove('animate-shake'), 400);
        }

        return isValid;
    }

    /**
     * Clear all validation errors in a form.
     */
    function clearFormErrors(form) {
        if (!form) return;
        const elements = form.querySelectorAll('input, select, textarea');
        elements.forEach(clearFieldError);
    }

    /**
     * Password strength evaluation.
     */
    function evaluatePasswordStrength(password) {
        if (!password) return { score: 0, label: 'Empty', className: '' };
        let score = 0;
        if (password.length >= 6) score += 1;
        if (password.length >= 8) score += 1;
        if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score += 1;
        if (/[0-9]/.test(password)) score += 1;
        if (/[^A-Za-z0-9]/.test(password)) score += 1;

        if (score <= 2) {
            return { score: 1, label: 'Weak', className: 'password-strength-weak' };
        } else if (score <= 4) {
            return { score: 2, label: 'Moderate', className: 'password-strength-medium' };
        } else {
            return { score: 3, label: 'Strong', className: 'password-strength-strong' };
        }
    }

    /**
     * Attach live validation listeners to all forms and inputs.
     */
    function initializeAutoValidation() {
        const inputs = document.querySelectorAll('input, select, textarea');

        inputs.forEach(input => {
            if (input.type === 'hidden' || input.dataset.noValidate === 'true') return;

            // Validate on blur (field exit)
            input.addEventListener('blur', () => {
                if (input.value && input.value.trim().length > 0 || input.hasAttribute('required')) {
                    validateField(input);
                }
            });

            // Re-validate in real-time as user corrects an error
            input.addEventListener('input', () => {
                if (input.classList.contains('input-error')) {
                    validateField(input);
                }

                // Live matching for confirmation fields
                if (input.dataset.match || input.id.includes('confirm')) {
                    validateField(input);
                }
            });
        });

        // Auto-intercept standard forms
        const forms = document.querySelectorAll('form:not([data-no-validate="true"])');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!validateForm(form)) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            });
        });
    }

    // Initialize upon DOM readiness
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeAutoValidation);
    } else {
        initializeAutoValidation();
    }

    // Expose public API on window
    window.GrantFinderValidator = {
        validateField,
        validateForm,
        clearFieldError,
        clearFormErrors,
        getValidationErrorMessage,
        evaluatePasswordStrength,
        isValidEmail: (email) => EMAIL_REGEX.test(email || ''),
        isValidUrl: (url) => URL_REGEX.test(url || '')
    };

})();
