/**
Camera Component - Handles camera initialization and management
*/
import { state } from '../config.js';

class Camera {
    constructor(elements) {
        this.elements = elements;
        this.stream = null;
    }

    async init() {
        try {
            const constraints = {
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: 3840 },
                    height: { ideal: 2160 },
                    // Yêu cầu góc nhìn rộng nhất
                    // advanced: [
                    //     { focusMode: '0.27' },  // Tự động chỉnh tiêu cự liên tục
                    //     { focusDistance: { min: 0, max: 2 } }  // Cho phép điều chỉnh khoảng cách
                    // ]
                },
                audio: false
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            // Khởi tạo camera không cần phát hiện tài liệu
            state.stream = this.stream;
            this.elements.video.srcObject = this.stream;

            this.elements.video.onloadedmetadata = () => {
                const video = this.elements.video;
                const container = video.parentElement;

                const { videoWidth, videoHeight } = video;

                // Tính tỉ lệ hiển thị sau khi xoay 90 độ
                const rotatedAspectRatio = videoHeight / videoWidth;

                // Áp dụng aspect-ratio cho container
                container.style.aspectRatio = String(rotatedAspectRatio);
                container.style.height = 'auto';          // bỏ chiều cao cố định
                container.style.maxHeight = '100%';       // giới hạn nếu cần

                // Thiết lập video
                video.style.transform = 'rotate(-90deg)';
                video.style.width = '100%';
                video.style.height = '100%';
                video.style.objectFit = 'contain';        // hoặc cover, fill – kết quả như nhau

                video.play();
                this.checkCameraCapabilities();
            };
            window.App?.toast?.show('Camera đã sẵn sàng', 'success');
            return true;
        } catch (error) {
            console.error('Camera error:', error);
            this.elements.cameraError.classList.remove('hidden');
            this.elements.video.classList.add('hidden');
                this.elements.video.style.transform = '';
            window.App?.toast?.show('Không thể truy cập camera. Vui lòng cấp quyền.', 'error');
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
    }

    // Hàm này không còn cần thiết cho việc chụp chính vì đã xử lý trong Capture.js
    // async captureFullFrame() {
    //     // Deprecated in favor of Capture.js logic
    // }

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