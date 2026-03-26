/**
ImageList Component - OPTIMIZED rendering
*/
class ImageList {
    constructor(elements, imageStore) {
        this.elements = elements;
        this.imageStore = imageStore;
        this.sortable = null;
        this.renderQueue = [];
        this.isProcessingQueue = false;
    }

    init() {
        this.setupSortable();
    }

    setupSortable() {
        this.sortable = new Sortable(this.elements.imageList, {
            animation: 100,  // Faster animation
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'dragging',
            handle: '.image-item',
            delay: 30,  // Reduced delay
            delayOnTouchOnly: true,
            onEnd: (evt) => this.onReorder(evt)
        });
    }

    render(imageModel, index) {
        // Queue render for batching
        this.renderQueue.push({ imageModel, index });
        
        if (!this.isProcessingQueue) {
            this.processRenderQueue();
        }
    }

    processRenderQueue() {
        this.isProcessingQueue = true;
        
        requestAnimationFrame(() => {
            // Process all queued renders at once
            while (this.renderQueue.length > 0) {
                const { imageModel, index } = this.renderQueue.shift();
                this.renderSingle(imageModel, index);
            }
            
            this.isProcessingQueue = false;
        });
    }

    renderSingle(imageModel, index) {
        // Remove empty message
        const emptyMessage = document.getElementById('empty-message');
        if (emptyMessage) emptyMessage.remove();

        const div = document.createElement('div');
        div.className = 'image-item';
        div.dataset.id = imageModel.id;
        div.dataset.index = index;

        // Optimized HTML (no extra spaces)
        div.innerHTML = `<img src="${imageModel.url}" alt="Ảnh ${index + 1}" loading="lazy" decoding="async"><button class="delete-btn" data-id="${imageModel.id}"><i class="fas fa-times"></i></button><span class="image-number">${index + 1}</span>`;

        // Click handler
        div.addEventListener('click', (e) => {
            if (!e.target.closest('.delete-btn')) {
                window.App?.lightbox?.open(index, { rotated: true });
            }
        });

        // Delete handler
        div.querySelector('.delete-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.delete(imageModel.id);
        });

        this.elements.imageList.appendChild(div);
    }

    delete(id) {
        const removed = this.imageStore.remove(id);
        if (removed) {
            const item = this.elements.imageList.querySelector(`[data-id="${id}"]`);
            if (item) item.remove();
            
            this.updateNumbers();
            window.App?.updateUI();
            
            // Debounced save
            setTimeout(() => window.App?.saveImages(), 100);
            
            window.App?.toast?.show('Đã xóa', 'info');
        }
    }

    clear() {
        this.imageStore.clear();
        this.elements.imageList.innerHTML = `<div id="empty-message" class="col-span-full text-center py-12 text-gray-500"><i class="fas fa-camera-retro text-5xl mb-4 opacity-50"></i><p>Chưa có ảnh nào</p><p class="text-sm mt-1">Nhấn nút "Chụp ảnh" để bắt đầu</p></div>`;
    }

    onReorder(evt) {
        const newOrder = [];
        const items = this.elements.imageList.querySelectorAll('.image-item');

        items.forEach((item, index) => {
            const id = parseInt(item.dataset.id);
            const imageModel = this.imageStore.get(id);
            if (imageModel) {
                newOrder.push(imageModel);
                item.querySelector('.image-number').textContent = index + 1;
            }
        });

        this.imageStore.reorder(newOrder);
        setTimeout(() => window.App?.saveImages(), 100);
    }

    updateNumbers() {
        const items = this.elements.imageList.querySelectorAll('.image-item');
        items.forEach((item, index) => {
            item.dataset.index = index;
            item.querySelector('.image-number').textContent = index + 1;
        });
    }
}

window.ImageList = ImageList;