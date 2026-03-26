/**
 * Webcam Scan Document - Main Application
 * Entry point that initializes all components
 */

class App {
    constructor() {
        this.elements = {
            video: document.getElementById('video'),
            captureBtn: document.getElementById('capture-btn'),
            imageList: document.getElementById('image-list'),
            imageCount: document.getElementById('image-count'),
            pdfBtn: document.getElementById('pdf-btn'),
            resetBtn: document.getElementById('reset-btn'),
            flash: document.getElementById('flash'),
            cameraError: document.getElementById('camera-error'),
            loadingOverlay: document.getElementById('loading-overlay'),
            lightbox: document.getElementById('lightbox'),
            lightboxImage: document.getElementById('lightbox-image'),
            lightboxClose: document.getElementById('lightbox-close'),
            lightboxPrev: document.getElementById('lightbox-prev'),
            lightboxNext: document.getElementById('lightbox-next'),
            lightboxCounter: document.getElementById('lightbox-counter'),
            lightboxContent: document.getElementById('lightbox-content'),
            toastContainer: document.getElementById('toast-container'),

        };

        // Initialize image store
        this.imageStore = new ImageStore();

        // Initialize components
        this.toast = null;
        this.camera = null;
        this.capture = null;
        this.imageList = null;
        this.lightbox = null;
        this.api = null;
    }

    async init() {
        // Initialize toast
        this.toast = new Toast(this.elements.toastContainer);

        // Initialize components
        this.camera = new Camera(this.elements);
        this.capture = new Capture(this.elements, this.imageStore);
        this.imageList = new ImageList(this.elements, this.imageStore);
        this.lightbox = new Lightbox(this.elements, this.imageStore);
        this.api = new Api(this.imageStore, this.elements);

        // Setup event listeners
        this.setupEventListeners();

        // Initialize components that need setup
        this.imageList.init();
        this.lightbox.init();

        // Initialize camera
        await this.camera.init();

// Handle video play
        this.elements.video.addEventListener('play', () => {
            this.elements.cameraError.classList.add('hidden');
            this.elements.video.classList.remove('hidden');
        });

        // Load saved images
        this.loadImages();

        // Setup cleanup on page unload
        this.setupCleanup();
    }

    setupEventListeners() {
        // Capture button
        this.elements.captureBtn.addEventListener('click', () => this.capture.capture());

        // Reset button
        this.elements.resetBtn.addEventListener('click', () => this.resetImages());

        // PDF button
        this.elements.pdfBtn.addEventListener('click', () => this.api.createPDF());
    }

    updateUI() {
        const count = this.imageStore.count;
        this.elements.imageCount.textContent = `(${count})`;
        this.elements.pdfBtn.disabled = count === 0 || state.isLoading;

        // Show empty message if no images
        if (count === 0 && !document.getElementById('empty-message')) {
            this.elements.imageList.innerHTML = `
                <div id="empty-message" class="col-span-full text-center py-12 text-gray-500">
                    <i class="fas fa-camera-retro text-5xl mb-4 opacity-50"></i>
                    <p>Chưa có ảnh nào</p>
                    <p class="text-sm mt-1">Nhấn nút "Chụp ảnh" để bắt đầu</p>
                </div>
            `;
        }
    }

    resetImages() {
        if (this.imageStore.count === 0) return;

        // Clear all images without confirmation
        this.imageStore.clear();
        this.imageList.clear();
        this.api?.clearDocumentIds();
        this.updateUI();
        localStorage.removeItem('webscan_images');
        this.toast.show('Đã xóa tất cả ảnh', 'info');
    }

    saveImages() {
        const metadata = this.imageStore.getAll().map(img => img.toJSON());
        localStorage.setItem('webscan_images', JSON.stringify(metadata));
    }

    loadImages() {
        const stored = localStorage.getItem('webscan_images');
        if (stored) {
            // Images cannot be restored from localStorage (blobs are not serializable)
            // Clear the metadata
            localStorage.removeItem('webscan_images');
        }
    }

    setupCleanup() {
        window.addEventListener('beforeunload', () => {
            // Revoke all URLs to free memory
            this.imageStore.clear();

            // Stop camera stream
            this.camera?.stop();
        });
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.App = new App();
    window.App.init();
});
