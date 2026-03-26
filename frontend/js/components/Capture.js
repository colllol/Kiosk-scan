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

        // Apply brightness and contrast enhancement on canvas for preview
        // This makes preview brighter and sharper (PDF will be enhanced on backend)
        this.applyBrightnessContrast();

        // Convert to blob immediately (NO sharpening, NO extra processing)
        this.fastConvertToBlob(outputWidth, outputHeight);
    }

    applyBrightnessContrast() {
        // Apply brightness and contrast enhancement for preview
        // PDF will have more aggressive enhancement on backend
        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        
        const brightness = 20;  // +20 brightness
        const contrast = 1.3;   // 1.3x contrast
        
        // Apply brightness and contrast to each pixel
        for (let i = 0; i < data.length; i += 4) {
            // Apply brightness
            data[i] = Math.min(255, data[i] + brightness);     // R
            data[i + 1] = Math.min(255, data[i + 1] + brightness); // G
            data[i + 2] = Math.min(255, data[i + 2] + brightness); // B
            
            // Apply contrast
            data[i] = Math.min(255, Math.max(0, (data[i] - 128) * contrast + 128));
            data[i + 1] = Math.min(255, Math.max(0, (data[i + 1] - 128) * contrast + 128));
            data[i + 2] = Math.min(255, Math.max(0, (data[i + 2] - 128) * contrast + 128));
        }
        
        this.ctx.putImageData(imageData, 0, 0);
    }

    fastConvertToBlob(width, height) {
        // Use high quality for best PDF output (backend will enhance further)
        const quality = CONFIG.JPEG_QUALITY || 1.0;

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
        }, 'image/jpeg', quality);
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