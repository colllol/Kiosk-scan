// Capture.js
import { ImageModel } from '../models/ImageModel.js';
import { state } from '../config.js';

class Capture {
    constructor(elements, imageStore) {
        this.elements = elements;
        this.imageStore = imageStore;
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d', {
            alpha: false,
            desynchronized: true,
            willReadFrequently: false
        });
        this.cachedWidth = 0;
        this.cachedHeight = 0;
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

        // Flash effect
        this.elements.flash.classList.add('flash-active');
        setTimeout(() => this.elements.flash.classList.remove('flash-active'), 50);

        // Rotate -90° (camera đặt ngang)
        const outputWidth = videoHeight;
        const outputHeight = videoWidth;

        if (this.cachedWidth !== outputWidth || this.cachedHeight !== outputHeight) {
            this.canvas.width = outputWidth;
            this.canvas.height = outputHeight;
            this.cachedWidth = outputWidth;
            this.cachedHeight = outputHeight;
        }

        this.ctx.save();
        this.ctx.translate(outputWidth / 2, outputHeight / 2);
        this.ctx.rotate(-Math.PI / 2);
        this.ctx.drawImage(video, -videoWidth / 2, -videoHeight / 2, videoWidth, videoHeight);
        this.ctx.restore();

        // Lưu ảnh gốc (đã xoay) - Backend sẽ xử lý auto-crop
        this.saveImage(outputWidth, outputHeight);
    }

    async saveImage(width, height) {
        const blob = await new Promise(resolve => this.canvas.toBlob(resolve, 'image/png'));
        const imageModel = new ImageModel(blob, width, height);
        this.imageStore.add(imageModel);
        this.batchUpdateUI(imageModel);
        window.App?.toast?.show('Đã chụp ảnh', 'success');
    }

    batchUpdateUI(imageModel) {
        requestAnimationFrame(() => {
            window.App?.imageList?.render(imageModel, this.imageStore.count - 1);
            window.App?.updateUI();
            setTimeout(() => window.App?.saveImages(), 100);
        });
    }
}

export { Capture };