/**
Camera Component - Handles camera initialization and management
*/
import { state } from '../config.js';

class Camera {
    constructor(elements) {
        this.elements = elements;
        this.stream = null;
        this.resizeHandler = null;
    }

    async init() {
        try {
            const constraints = {
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: 3840 },
                    height: { ideal: 2160 },
                    // Request the widest practical camera frame.
                    // advanced: [
                    //     { focusMode: 'continuous' },
                    //     { focusDistance: { min: 0, max: 2 } }
                    // ]
                },
                audio: false
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            state.stream = this.stream;
            this.elements.video.srcObject = this.stream;

            this.elements.video.onloadedmetadata = () => {
                const video = this.elements.video;
                const container = video.parentElement;
                const { videoWidth, videoHeight } = video;
                const rotatedAspectRatio = videoHeight / videoWidth;

                const layoutRotatedVideo = () => {
                    const rect = container.getBoundingClientRect();
                    if (!rect.width || !rect.height) return;

                    const displayWidth = Math.min(rect.width, rect.height * rotatedAspectRatio);
                    const displayHeight = Math.min(rect.height, rect.width / rotatedAspectRatio);

                    // The element is rotated 90deg, so its pre-transform dimensions are swapped.
                    video.style.width = `${displayHeight}px`;
                    video.style.height = `${displayWidth}px`;
                };

                video.style.position = 'absolute';
                video.style.left = '50%';
                video.style.top = '50%';
                video.style.transform = 'translate(-50%, -50%) rotate(90deg) scale(1)';
                video.style.transformOrigin = 'center center';
                video.style.maxWidth = 'none';
                video.style.maxHeight = 'none';
                video.style.objectFit = 'contain';
                layoutRotatedVideo();

                if (this.resizeHandler) {
                    window.removeEventListener('resize', this.resizeHandler);
                }
                this.resizeHandler = layoutRotatedVideo;
                window.addEventListener('resize', this.resizeHandler);

                video.play();
                this.checkCameraCapabilities();
            };
            window.App?.toast?.show('Camera da san sang', 'success');
            return true;
        } catch (error) {
            console.error('Camera error:', error);
            this.elements.cameraError.classList.remove('hidden');
            this.elements.video.classList.add('hidden');
            this.elements.video.style.transform = '';
            window.App?.toast?.show('Khong the truy cap camera. Vui long cap quyen.', 'error');
            return false;
        }
    }

    getVideoElement() {
        return this.elements.video;
    }

    isReady() {
        return this.elements.video.videoWidth > 0 && this.elements.video.videoHeight > 0;
    }

    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.resizeHandler) {
            window.removeEventListener('resize', this.resizeHandler);
            this.resizeHandler = null;
        }
    }

    startDocumentDetection() {
        // Empty function to maintain compatibility
    }

    checkCameraCapabilities() {
        const track = this.stream?.getVideoTracks()[0];
        if (!track) return;
        const capabilities = track.getCapabilities();
        this.hasFocusControl = 'focusMode' in capabilities || 'focusDistance' in capabilities;

        if (this.hasFocusControl) {
            console.log('Camera supports focus control:', capabilities);
        }
    }

    /**
     * Set camera focus mode and distance
     * @param {string} mode - 'manual', 'continuous', or 'single-shot'
     * @param {number} [distance] - Focus distance (0-1)
     */
    setFocus(mode, distance) {
        const track = this.stream?.getVideoTracks()[0];
        if (!track || !this.hasFocusControl) return false;

        try {
            const constraints = {};

            if ('focusMode' in track.getCapabilities()) {
                constraints.focusMode = mode;
            }

            if (distance !== undefined && 'focusDistance' in track.getCapabilities()) {
                constraints.focusDistance = distance;
            }

            return track.applyConstraints({ advanced: [constraints] });
        } catch (error) {
            console.error('Failed to set focus:', error);
            return false;
        }
    }

    triggerFocus() {
        return this.setFocus('continuous');
    }
}

export { Camera };
