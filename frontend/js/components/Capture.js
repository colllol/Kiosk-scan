// Capture.js
import { ImageModel } from '../models/ImageModel.js';
import { CONFIG, state } from '../config.js';

class Capture {
    constructor(elements, imageStore, documentScanner = null) {
        this.elements = elements;
        this.imageStore = imageStore;
        this.documentScanner = documentScanner;
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d', {
            alpha: false,
            desynchronized: true,
            willReadFrequently: false
        });
        this.cachedWidth = 0;
        this.cachedHeight = 0;
    }

    async capture() {
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

        if (!this.documentScanner) {
            window.App?.toast?.show('Bo phat hien tai lieu chua san sang', 'error');
            return;
        }

        const cachedDetection = this.documentScanner.getLastLiveDetectionForCanvas(
            outputWidth,
            outputHeight,
        );
        if (!cachedDetection) {
            window.App?.toast?.show('Chua phat hien tai lieu, vui long dua tai lieu vao khung', 'error');
            return;
        }

        const preparedCrop = this.documentScanner.prepareCropInputFromRotatedVideo(
            video,
            outputWidth,
            outputHeight,
            cachedDetection,
        );
        const frameCanvas = preparedCrop.canvas;
        const cropDetection = preparedCrop.detection;
        const previewCanvas = this.createPreviewCanvas(frameCanvas);
        const previewBlob = await this.canvasToBlob(previewCanvas, 'image/jpeg', 0.72);
        const imageModel = new ImageModel(previewBlob, previewCanvas.width, previewCanvas.height);
        imageModel.isFinal = false;
        imageModel.processing = true;

        this.imageStore.add(imageModel);
        this.batchUpdateUI(imageModel);
        window.App?.toast?.show('Da chup anh', 'success');

        imageModel.readyPromise = this.processFinalImage(frameCanvas, cropDetection, imageModel);
    }

    async processFinalImage(frameCanvas, cachedDetection, imageModel) {
        try {
            await this.deferWork();
            const cropped = await this.documentScanner.cropCanvas(frameCanvas, cachedDetection);
            if (!cropped) {
                throw new Error('Cannot crop document');
            }

            const resized = this.resizeCanvasToLongSide(cropped, CONFIG.ACTIVE_SCAN_PROFILE.outputMaxLongSide);
            const outputCanvas = this.enhanceForText(resized);
            const thumbnailBlob = await this.createThumbnailBlob(outputCanvas);
            const blob = await this.canvasToBlob(outputCanvas, 'image/jpeg', CONFIG.ACTIVE_SCAN_PROFILE.jpegQuality);
            imageModel.updateBlob(blob, outputCanvas.width, outputCanvas.height, thumbnailBlob);
            imageModel.isFinal = true;
            imageModel.processing = false;
            imageModel.processingError = null;

            window.App?.imageList?.update(imageModel);
            window.App?.saveImages();
            window.App?.api?.enqueueUpload(imageModel)?.catch((uploadError) => {
                console.warn('[Capture] Background upload failed:', uploadError);
            });
            return imageModel;
        } catch (error) {
            console.warn('[Capture] Frontend document crop failed:', error);
            imageModel.processing = false;
            imageModel.processingError = error;
            window.App?.imageList?.update(imageModel);
            window.App?.toast?.show('Crop anh loi, vui long thu lai', 'error');
            return imageModel;
        }
    }

    createPreviewCanvas(sourceCanvas) {
        const maxPreviewWidth = 420;
        const scale = Math.min(1, maxPreviewWidth / sourceCanvas.width);
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(sourceCanvas.width * scale));
        canvas.height = Math.max(1, Math.round(sourceCanvas.height * scale));
        canvas.getContext('2d', { alpha: false }).drawImage(sourceCanvas, 0, 0, canvas.width, canvas.height);
        return canvas;
    }

    async createThumbnailBlob(sourceCanvas) {
        const thumbnailCanvas = this.createPreviewCanvas(sourceCanvas);
        return this.canvasToBlob(thumbnailCanvas, 'image/jpeg', 0.74);
    }

    resizeCanvasToLongSide(sourceCanvas, maxLongSide) {
        const currentLongSide = Math.max(sourceCanvas.width, sourceCanvas.height);
        if (!maxLongSide || currentLongSide <= maxLongSide) {
            return sourceCanvas;
        }

        const scale = maxLongSide / currentLongSide;
        const canvas = document.createElement('canvas');
        canvas.width = Math.max(1, Math.round(sourceCanvas.width * scale));
        canvas.height = Math.max(1, Math.round(sourceCanvas.height * scale));
        canvas.getContext('2d', { alpha: false }).drawImage(sourceCanvas, 0, 0, canvas.width, canvas.height);
        return canvas;
    }

    enhanceForText(canvas) {
        const scratch = document.createElement('canvas');
        scratch.width = canvas.width;
        scratch.height = canvas.height;

        const scratchCtx = scratch.getContext('2d', { alpha: false });
        scratchCtx.drawImage(canvas, 0, 0);

        const ctx = canvas.getContext('2d', {
            alpha: false,
            willReadFrequently: false
        });
        ctx.save();
        ctx.filter = 'contrast(1.12) brightness(1.03) saturate(0.96)';
        ctx.drawImage(scratch, 0, 0);
        ctx.restore();

        return canvas;
    }

    async saveImage(sourceCanvas) {
        const blob = await this.canvasToBlob(sourceCanvas, 'image/jpeg', CONFIG.ACTIVE_SCAN_PROFILE.jpegQuality);
        const imageModel = new ImageModel(blob, sourceCanvas.width, sourceCanvas.height);
        imageModel.updateThumbnail(await this.createThumbnailBlob(sourceCanvas));
        this.imageStore.add(imageModel);
        this.batchUpdateUI(imageModel);
        window.App?.toast?.show('Đã chụp ảnh', 'success');
    }

    canvasToBlob(canvas, type, quality) {
        return new Promise((resolve, reject) => {
            canvas.toBlob((blob) => {
                if (blob) resolve(blob);
                else reject(new Error('Cannot encode image'));
            }, type, quality);
        });
    }

    deferWork() {
        return new Promise((resolve) => {
            if ('requestIdleCallback' in window) {
                window.requestIdleCallback(resolve, { timeout: 120 });
            } else {
                setTimeout(resolve, 0);
            }
        });
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
