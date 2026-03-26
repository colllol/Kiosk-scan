/**
 * Lightbox Component - Handles image preview with zoom support
 */

class Lightbox {
    constructor(elements, imageStore) {
        this.elements = elements;
        this.imageStore = imageStore;
        this.currentIndex = 0;

        // Touch state
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.isSwiping = false;
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Close button
        this.elements.lightboxClose.addEventListener('click', () => this.close());

        // Navigation buttons
        this.elements.lightboxPrev.addEventListener('click', () => this.navigate(-1));
        this.elements.lightboxNext.addEventListener('click', () => this.navigate(1));

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!this.elements.lightbox.classList.contains('hidden')) {
                if (e.key === 'Escape') this.close();
                if (e.key === 'ArrowLeft') this.navigate(-1);
                if (e.key === 'ArrowRight') this.navigate(1);
            }
        });

        // Click to close
        this.elements.lightbox.addEventListener('click', (e) => {
            if (e.target === this.elements.lightbox || e.target === this.elements.lightboxContent) {
                this.close();
            }
        });

        // Touch events
        this.elements.lightboxContent.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: false });
        this.elements.lightboxContent.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
        this.elements.lightboxContent.addEventListener('touchend', (e) => this.handleTouchEnd(e));

        // Mouse wheel zoom
        this.elements.lightboxContent.addEventListener('wheel', (e) => this.handleWheelZoom(e), { passive: false });
    }

    open(index) {
        this.currentIndex = index;
        this.updateImage();
        this.elements.lightbox.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        // Show navigation buttons if more than 1 image
        if (this.imageStore.count > 1) {
            this.elements.lightboxPrev.classList.remove('hidden');
            this.elements.lightboxNext.classList.remove('hidden');
        }
    }

    close() {
        this.elements.lightbox.classList.add('hidden');
        document.body.style.overflow = '';
        this.resetZoom();
    }

    navigate(direction) {
        this.currentIndex += direction;

        if (this.currentIndex < 0) {
            this.currentIndex = this.imageStore.count - 1;
        } else if (this.currentIndex >= this.imageStore.count) {
            this.currentIndex = 0;
        }

        this.updateImage();
    }

    updateImage() {
        const imageModel = this.imageStore.getByIndex(this.currentIndex);
        if (imageModel) {
            this.elements.lightboxImage.src = imageModel.url;
            this.elements.lightboxCounter.textContent = `${this.currentIndex + 1} / ${this.imageStore.count}`;
            this.resetZoom();
            
            // Apply maximum brightness and contrast for sharper, brighter images
            this.elements.lightboxImage.style.filter = 'brightness(1.3) contrast(1.4) saturate(1.2)';
        }
    }

    resetZoom() {
        state.currentScale = 1;
        this.elements.lightboxImage.style.transform = 'scale(1) translate(0, 0)';
        this.elements.lightboxImage.classList.remove('zoomed');
    }

    // Touch handling
    handleTouchStart(e) {
        if (e.touches.length === 2) {
            e.preventDefault();
            state.pinchStartDistance = this.getTouchDistance(e.touches);
        } else if (e.touches.length === 1) {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
            this.isSwiping = true;
        }
    }

    handleTouchMove(e) {
        if (e.touches.length === 2) {
            e.preventDefault();
            const distance = this.getTouchDistance(e.touches);
            const scale = distance / state.pinchStartDistance;
            const newScale = Math.min(Math.max(state.currentScale * scale, 1), 4);

            this.elements.lightboxImage.style.transform = `scale(${newScale})`;
            this.elements.lightboxImage.classList.toggle('zoomed', newScale > 1);
        } else if (e.touches.length === 1 && this.isSwiping) {
            const deltaY = Math.abs(e.touches[0].clientY - this.touchStartY);
            const deltaX = Math.abs(e.touches[0].clientX - this.touchStartX);

            if (deltaY > 100 && deltaY > deltaX) {
                const direction = e.touches[0].clientY > this.touchStartY ? 'down' : 'up';
                if (direction === 'up' || (state.currentScale <= 1)) {
                    this.close();
                }
                this.isSwiping = false;
            }
        }
    }

    handleTouchEnd(e) {
        if (e.touches.length < 2) {
            const scale = parseFloat(this.elements.lightboxImage.style.transform.replace('scale(', '').replace(')', '')) || 1;
            state.currentScale = scale <= 1 ? 1 : scale;
            if (state.currentScale <= 1) {
                this.resetZoom();
            }
        }
        this.isSwiping = false;
    }

    getTouchDistance(touches) {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    // Mouse wheel zoom
    handleWheelZoom(e) {
        e.preventDefault();

        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        const newScale = Math.min(Math.max(state.currentScale + delta, 1), 4);

        this.elements.lightboxImage.style.transform = `scale(${newScale})`;
        this.elements.lightboxImage.classList.toggle('zoomed', newScale > 1);
        state.currentScale = newScale;
    }
}

// Export for global use
window.Lightbox = Lightbox;
