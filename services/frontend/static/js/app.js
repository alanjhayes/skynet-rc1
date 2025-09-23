// Skynet RC1 JavaScript Application

// Global utilities
window.SkynetRC1 = {
    // CSRF token helper
    getCSRFToken: function() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (!token) {
            console.warn('CSRF token not found. Make sure {% csrf_token %} is included in your template.');
            return '';
        }
        return token;
    },
    
    // API request helper
    apiRequest: async function(url, options = {}) {
        const defaults = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            }
        };
        
        const config = {
            ...defaults,
            ...options,
            headers: {
                ...defaults.headers,
                ...options.headers
            }
        };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    },
    
    // Show notification
    showNotification: function(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 1055; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    },
    
    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // Format date
    formatDate: function(dateString) {
        const options = { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit' 
        };
        return new Date(dateString).toLocaleDateString(undefined, options);
    }
};

// Initialize tooltips and popovers when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-focus on input fields in modals
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('shown.bs.modal', function() {
            const firstInput = modal.querySelector('input[type="text"], input[type="email"], textarea');
            if (firstInput) {
                firstInput.focus();
            }
        });
    });
});

// File upload helper
window.FileUploader = {
    upload: async function(file, progressCallback) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('csrfmiddlewaretoken', SkynetRC1.getCSRFToken());
        
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            // Progress tracking
            if (progressCallback) {
                xhr.upload.addEventListener('progress', function(e) {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        progressCallback(percentComplete);
                    }
                });
            }
            
            xhr.addEventListener('load', function() {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (e) {
                        reject(new Error('Invalid JSON response'));
                    }
                } else {
                    try {
                        const error = JSON.parse(xhr.responseText);
                        reject(new Error(error.error || `HTTP ${xhr.status}`));
                    } catch (e) {
                        reject(new Error(`HTTP ${xhr.status}`));
                    }
                }
            });
            
            xhr.addEventListener('error', function() {
                reject(new Error('Network error'));
            });
            
            xhr.open('POST', '/api/upload/');
            xhr.send(formData);
        });
    }
};

// Chat utilities
window.ChatUtils = {
    // Escape HTML to prevent XSS
    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    // Format message content (basic markdown-like formatting)
    formatMessage: function(content) {
        // Escape HTML first
        content = this.escapeHtml(content);
        
        // Basic formatting
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); // Bold
        content = content.replace(/\*(.*?)\*/g, '<em>$1</em>'); // Italic
        content = content.replace(/`(.*?)`/g, '<code>$1</code>'); // Code
        content = content.replace(/\n/g, '<br>'); // Line breaks
        
        return content;
    },
    
    // Scroll to bottom of chat
    scrollToBottom: function(containerId = 'messages-container') {
        const container = document.getElementById(containerId);
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }
};

// Document utilities
window.DocumentUtils = {
    // Get file type icon
    getFileIcon: function(mimeType) {
        if (mimeType.includes('pdf')) return 'fa-file-pdf';
        if (mimeType.includes('word') || mimeType.includes('document')) return 'fa-file-word';
        if (mimeType.includes('text')) return 'fa-file-alt';
        if (mimeType.includes('image')) return 'fa-file-image';
        return 'fa-file';
    },
    
    // Get file type badge class
    getFileTypeBadge: function(mimeType) {
        if (mimeType.includes('pdf')) return 'badge-danger';
        if (mimeType.includes('word') || mimeType.includes('document')) return 'badge-info';
        if (mimeType.includes('text')) return 'badge-success';
        return 'badge-secondary';
    }
};

// Error handling
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    // Don't show error notifications for every JS error in production
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        SkynetRC1.showNotification('A JavaScript error occurred. Check the console for details.', 'warning');
    }
});

// Service worker registration (if available)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(err) {
                console.log('ServiceWorker registration failed');
            });
    });
}