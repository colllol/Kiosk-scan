/**
Capture Component - ULTRA FAST image capture
*/
class Capture {
    constructor(elements, imageStore) {
        this.elements = elements;
        this.imageStore = imageStore;

        // Pre-create and reuse canvas (CRITICAL for performance)
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d', {
            alpha: false,
            desynchronized: true,
            willReadFrequently: false
        });

        // Cache dimensions
        this.cachedWidth = 0;
        this.cachedHeight = 0;

        // Debounce save operations
        this.saveTimeout = null;
    }

    capture() {
        if (state.isLoading) return;

        const video = this.elements.video;
        const videoWidth = video.videoWidth;
        const videoHeight = video.videoHeight;

        if (videoWidth === 0 || videoHeight === 0) {
            window.App?.toast?.show('Camera chưa sẵn sàng', 'error');
            return;
        }

        // Minimal flash effect (50ms instead of 300ms)
        this.elements.flash.classList.add('flash-active');
        setTimeout(() => this.elements.flash.classList.remove('flash-active'), 50);

        // --- OPTIMIZED: Rotate -90 degrees ---
        const outputWidth = videoHeight;
        const outputHeight = videoWidth;

        // Resize canvas only if dimensions changed
        if (this.cachedWidth !== outputWidth || this.cachedHeight !== outputHeight) {
            this.canvas.width = outputWidth;
            this.canvas.height = outputHeight;
            this.cachedWidth = outputWidth;
            this.cachedHeight = outputHeight;
        }

        // Fast rotate and capture
        this.ctx.save();
        this.ctx.translate(outputWidth / 2, outputHeight / 2);
        this.ctx.rotate(-Math.PI / 2);
        this.ctx.drawImage(video, -videoWidth / 2, -videoHeight / 2, videoWidth, videoHeight);
        this.ctx.restore();

        // Convert to blob immediately (NO sharpening, NO brightness/contrast, NO extra processing)
        this.fastConvertToBlob(outputWidth, outputHeight);
    }

    fastConvertToBlob(width, height) {
        // Sử dụng PNG lossless để giữ chất lượng 100%
        this.canvas.toBlob((blob) => {
            if (!blob) return;

            const imageModel = new ImageModel(blob, width, height);
            this.imageStore.add(imageModel);

            // DEBOUNCED: Batch UI updates (wait 50ms)
            if (this.saveTimeout) clearTimeout(this.saveTimeout);
            this.saveTimeout = setTimeout(() => {
                this.batchUpdateUI(imageModel);
            }, 50);

            // Immediate toast (no wait)
            window.App?.toast?.show('Đã chụp', 'success');
        }, 'image/png', 1.0);
    }

    batchUpdateUI(imageModel) {
        // Single batch update instead of multiple calls
        requestAnimationFrame(() => {
            window.App?.imageList?.render(imageModel, this.imageStore.count - 1);
            window.App?.updateUI();

            // Async save to localStorage (non-blocking)
            setTimeout(() => {
                window.App?.saveImages();
            }, 100);
        });
    }
}

window.Capture = Capture;