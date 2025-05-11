
// Common script for both logged-in and logged-out states

// Image fallback handler function
function handleImageError(img) {
    img.src = '/static/images/fallback_logo.png';
    img.onerror = null; // Prevent infinite loop
}

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu functionality
    const hamburger = document.querySelector('.hamburger');
    const closeBtn = document.querySelector('.closebtn');
    const navRight = document.getElementById('navbarRight');
    
    if (hamburger && closeBtn && navRight) {
        hamburger.addEventListener('click', function() {
            navRight.style.left = "0"; // Show menu
            document.body.style.overflow = 'hidden'; // Prevent scrolling
        });
        
        closeBtn.addEventListener('click', function() {
            navRight.style.left = "-100%"; // Hide menu
            document.body.style.overflow = ''; // Enable scrolling
        });
    }
    
    // Logo fallback handling
    const logoImg = document.querySelector('.logo-img');
    if (logoImg) {
        logoImg.onerror = function() {
            this.src = '/static/images/fallback_logo.png';
            this.onerror = null; // Prevent infinite loop
        };
    }
    
    // Mobile dropdown menu
    const dropBtn = document.getElementById('dropBtn');
    if (dropBtn) {
        dropBtn.addEventListener('click', function(e) {
            // Only handle click on mobile
            if (window.innerWidth <= 600) {
                e.preventDefault();
                const dropdown = this.parentElement;
                dropdown.classList.toggle('active');
                const dropdownContent = dropdown.querySelector('.dropdown-content');
                if (dropdownContent) {
                    if (dropdownContent.style.display === 'block') {
                        dropdownContent.style.display = 'none';
                    } else {
                        dropdownContent.style.display = 'block';
                    }
                }
            }
        });
    }
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 600) {
            const dropdown = document.querySelector('.dropdown.active');
            if (dropdown && !dropdown.contains(e.target)) {
                dropdown.classList.remove('active');
                const dropdownContent = dropdown.querySelector('.dropdown-content');
                if (dropdownContent) {
                    dropdownContent.style.display = 'none';
                }
            }
        }
    });
    
    // Toast notification system
    window.showToast = function(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            // Create toast container if it doesn't exist
            const container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let icon = '🔔'; // Default info icon
        if (type === 'success') icon = '✅';
        if (type === 'error') icon = '❌';
        if (type === 'warning') icon = '⚠️';
        
        toast.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <span class="toast-message">${message}</span>
            <span class="toast-close">×</span>
        `;
        
        document.querySelector('.toast-container').appendChild(toast);
        
        // Add click event to close button
        toast.querySelector('.toast-close').addEventListener('click', function() {
            toast.remove();
        });
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 3000);
    };
});

// Helper function to convert markdown to HTML
function markdownToHTML(markdown) {
    if (!markdown) return '';
    
    // Basic markdown conversion
    let html = markdown
        // Headers
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        
        // Bold and italic
        .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/gim, '<em>$1</em>')
        
        // Lists
        .replace(/^\s*\d+\.\s+(.*$)/gim, '<li>$1</li>')
        .replace(/^\s*\-\s+(.*$)/gim, '<li>$1</li>')
        
        // Links
        .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
        
        // Paragraphs
        .replace(/^\s*(\n)?(.+)/gim, function(m) {
            return /\<(\/)?(h\d|ul|ol|li|blockquote|pre|img)/.test(m) ? m : '<p>'+m+'</p>';
        })
        
        // Line breaks
        .replace(/\n/gim, '<br>');
    
    // Convert list items to proper lists
    html = html.replace(/<li>.*?<\/li>/gim, function(m) {
        return '<ul>' + m + '</ul>';
    });
    
    // Remove duplicate ul tags
    html = html.replace(/<\/ul><ul>/gim, '');
    
    return html;
};
