/**
 * Toast Component - Handles notification messages
 */

class Toast {
    constructor(container) {
        this.container = container;
    }

    show(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type} px-6 py-4 rounded-lg text-white shadow-lg flex items-center gap-3`;

        const iconMap = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            info: 'fas fa-info-circle'
        };

        toast.innerHTML = `
            <i class="${iconMap[type]} text-xl"></i>
            <span>${message}</span>
        `;

        this.container.appendChild(toast);

        // Auto remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

export { Toast };
