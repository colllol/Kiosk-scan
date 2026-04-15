/**
API Component - OPTIMIZED upload
*/
import { CONFIG, state } from '../config.js';

class Api {
    constructor(imageStore, elements) {
        this.imageStore = imageStore;
        this.elements = elements;
        this.documentIds = [];
        // OPTIMIZATION 3: Tăng parallel uploads từ 5 → 10 để tận dụng bandwidth
        this.MAX_PARALLEL_UPLOADS = 10;
    }

    /**
     * Get selected service ID and name from the combo box
     */
    getSelectedService() {
        const select = document.getElementById('service-select');
        if (!select) {
            return { serviceId: null, serviceName: null };
        }
        const value = select.value;

        // Check if no service selected (value is # or empty)
        if (value === '#' || value === '' || !value) {
            return { serviceId: null, serviceName: null };
        }

        const text = select.options[select.selectedIndex]?.text || '';

        // Extract service name - check if first char is emoji, if so remove it
        let serviceName = text.trim();
        const firstChar = serviceName.codePointAt(0);
        // Check if first character is an emoji (Unicode > 0xFFFF)
        if (firstChar && firstChar > 0xFFFF) {
            // Remove the emoji (which may be 2 UTF-16 code units)
            serviceName = serviceName.substring(1).trim();
            // If there's still a space at the start, remove it
            if (serviceName.startsWith(' ')) {
                serviceName = serviceName.substring(1).trim();
            }
        }

        return {
            serviceId: parseInt(value),
            serviceName: serviceName
        };
    }

    async uploadImage(imageModel) {
        const formData = new FormData();
        // Gửi PNG lossless thay vì JPEG để giữ chất lượng 100%
        formData.append('file', imageModel.blob, `img_${Date.now()}.png`);

        try {
            const response = await fetch(CONFIG.API_UPLOAD, {
                method: 'POST',
                body: formData,
                cache: 'no-cache'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            return data.id;
        } catch (error) {
            console.error('Upload error:', error);
            throw error;
        }
    }

    async uploadAllImages() {
        if (this.imageStore.count === 0 && !document.getElementById('service-select').value === '#') {
            window.App?.toast?.show('Vui lòng chụp ít nhất 1 ảnh', 'error');
            return [];
        }

        state.isLoading = true;
        this.setLoading(true);

        try {
            const images = this.imageStore.getAll();
            
            // PARALLEL upload (5 at a time)
            const ids = await this.uploadParallel(images);
            
            this.documentIds = ids;
            return ids;
        } catch (error) {
            console.error('Upload error:', error);
            window.App?.toast?.show('Lỗi upload: ' + error.message, 'error');
            return [];
        } finally {
            state.isLoading = false;
            this.setLoading(false);
        }
    }

    async uploadParallel(images) {
        const ids = new Array(images.length);
        const queue = [...images];
        const inProgress = new Set();
        
        return new Promise((resolve, reject) => {
            const uploadNext = async () => {
                if (queue.length === 0 && inProgress.size === 0) {
                    resolve(ids.filter(id => id !== undefined));
                    return;
                }

                while (inProgress.size < this.MAX_PARALLEL_UPLOADS && queue.length > 0) {
                    const image = queue.shift();
                    const index = images.indexOf(image);
                    inProgress.add(index);

                    this.uploadImage(image)
                        .then(id => {
                            ids[index] = id;
                        })
                        .catch(error => {
                            reject(error);
                        })
                        .finally(() => {
                            inProgress.delete(index);
                            uploadNext();
                        });
                }
            };

            uploadNext();
        });
    }

    async createPDF() {
        // Get selected service
        const service = this.getSelectedService();
        const hasService = service.serviceId !== null;
        const hasImages = this.imageStore.count > 0;

        // Validate according to requirements:
        // 1. Có ảnh và chọn dịch vụ (value != #) -> upload ảnh và gửi đi
        if (hasImages && hasService) {
            // Proceed with upload and create PDF
        }
        // 2. Có ảnh và KHÔNG chọn dịch vụ (value == #) -> lỗi, không upload
        else if (hasImages && !hasService) {
            window.App?.toast?.show('xin vui lòng chọn dịch vụ', 'error');
            return;
        }
        // 3. Không có ảnh và ĐÃ chọn dịch vụ (value != #) -> lỗi, không upload
        else if (!hasImages && hasService) {
            window.App?.toast?.show('xin vui lòng tải ảnh lên', 'error');
            return;
        }
        // 4. Không có ảnh và KHÔNG chọn dịch vụ (value == #) -> lỗi, không upload
        else if (!hasImages && !hasService) {
            window.App?.toast?.show('xin vui lòng tải ảnh lên và chọn dịch vụ', 'error');
            return;
        }

        if (state.isLoading) return;

        if (this.documentIds.length !== this.imageStore.count) {
            const ids = await this.uploadAllImages();
            if (ids.length === 0) return;
        }

        state.isLoading = true;
        this.setLoading(true);

        try {
            const response = await fetch(CONFIG.API_EXPORT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ids: this.documentIds,
                    serviceId: service.serviceId,
                    serviceName: service.serviceName
                })
            });

            if (!response.ok) {
                throw new Error('Lỗi tạo PDF');
            }

            await response.blob();
            this.documentIds = [];
            this.clearAllImages();

            window.App?.toast?.show('PDF đã tạo!', 'success');

            setTimeout(() => {
                window.location.href = 'index.html';
            }, 400);
        } catch (error) {
            window.App?.toast?.show('Lỗi: ' + error.message, 'error');
        } finally {
            state.isLoading = false;
            this.setLoading(false);
        }
    }

    clearAllImages() {
        this.documentIds = [];
        this.imageStore.clear();
        window.App?.imageList?.clear();
        window.App?.updateUI();
        localStorage.removeItem('webscan_images');
    }

    setLoading(loading) {
        if (loading) {
            this.elements.loadingOverlay.classList.remove('hidden');
            this.elements.pdfBtn.disabled = true;
            this.elements.captureBtn.disabled = true;
        } else {
            this.elements.loadingOverlay.classList.add('hidden');
            this.elements.pdfBtn.disabled = false;
            this.elements.captureBtn.disabled = false;
        }
    }

    clearDocumentIds() {
        this.documentIds = [];
    }

    /**
     * Chứng thực tài liệu - độc lập sự kiện, không dùng chung với createPDF
     * Gửi ảnh lên backend kèm serviceID=99 và serviceName lấy từ localhost:5431
     */
    async certifyDocuments() {
        const hasImages = this.imageStore.count > 0;

        if (!hasImages) {
            window.App?.toast?.show('Vui lòng chụp ít nhất 1 ảnh trước khi chứng thực', 'error');
            return;
        }

        state.isLoading = true;
        this.setLoading(true);

        try {
            // Step 1: Fetch fullName từ localhost:5431
            let serviceName = 'Chứng thực tài liệu';
            try {
                const response = await fetch('http://localhost:5431/');
                if (response.ok) {
                    const data = await response.json();
                    // Cấu trúc: data.data.cardObj.fullName
                    const fullName = data?.data?.cardObj?.fullName || null;
                    if (fullName) {
                        serviceName = fullName;
                    }
                }
            } catch (err) {
                console.warn('Could not fetch fullName from localhost:5431:', err.message);
            }

            // Step 2: Upload all images
            const ids = await this.uploadAllImages();
            if (ids.length === 0) {
                window.App?.toast?.show('Lỗi: Không thể upload ảnh', 'error');
                return;
            }

            window.App?.toast?.show(`Đã upload ${ids.length} ảnh. Đang xử lý...`, 'info');

            // Step 3: Call export endpoint với serviceID=99 và serviceName từ API
            const response = await fetch(CONFIG.API_EXPORT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ids: ids,
                    filename: null,
                    serviceId: 99,
                    serviceName: serviceName
                })
            });

            if (!response.ok) {
                throw new Error('Lỗi xử lý tài liệu');
            }

            // Reset
            this.documentIds = [];
            this.imageStore.clear();
            window.App?.imageList?.clear();
            window.App?.updateUI();
            localStorage.removeItem('webscan_images');

            window.App?.toast?.show('Đã chứng thực xong! Đang chuyển trang...', 'success');

            // Navigate to dịch vụ công
            setTimeout(() => {
                window.location.href = 'https://dichvucong.thainguyen.gov.vn/nop-ho-so?MaTTHCDP=2.000815.000.00.00.H55&MaCoQuanThucHien=H55.242&vnconnect=1&MaDVC=2.000815.000.00.00.H55.02&MDT=MzQ1ZTQwMDctY2ZlMS00YmQ4LTgxNjctN2MxZTYzYjUzNjU3';
            }, 1500);

        } catch (error) {
            console.error('Certify error:', error);
            window.App?.toast?.show('Lỗi: ' + error.message, 'error');
        } finally {
            state.isLoading = false;
            this.setLoading(false);
        }
    }
}

export { Api };