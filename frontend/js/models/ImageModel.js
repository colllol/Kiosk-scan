/**
 * Image Model - Data model for captured images
 */

class ImageModel {
    constructor(blob, width, height) {
        this.id = Date.now();
        this.blob = blob;
        this.url = URL.createObjectURL(blob);
        this.width = width;
        this.height = height;
        this.timestamp = new Date().toISOString();
    }

    static fromData(data) {
        const image = new ImageModel(data.blob, data.width, data.height);
        image.id = data.id;
        image.timestamp = data.timestamp;
        return image;
    }

    revokeUrl() {
        if (this.url) {
            URL.revokeObjectURL(this.url);
            this.url = null;
        }
    }

async rotate(degrees = -90) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Swap width/height for 90 degree rotation
        canvas.width = this.height;
        canvas.height = this.width;
        
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.rotate(degrees * Math.PI / 180);
        
        const img = await this.loadImage();
        ctx.drawImage(img, -img.width / 2, -img.height / 2);
        
        return new Promise((resolve) => {
            canvas.toBlob((blob) => {
                resolve(new ImageModel(blob, canvas.width, canvas.height));
            }, 'image/jpeg', 0.9);
        });
    }
    
    loadImage() {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => resolve(img);
            img.src = this.url;
        });
    }
    
    toJSON() {
        return {
            id: this.id,
            width: this.width,
            height: this.height,
            timestamp: this.timestamp
        };
    }
}

// Image Store - manages the collection of images
class ImageStore {
    constructor() {
        this.images = [];
    }

    add(imageModel) {
        this.images.push(imageModel);
    }

    remove(id) {
        const index = this.images.findIndex(img => img.id === id);
        if (index !== -1) {
            this.images[index].revokeUrl();
            this.images.splice(index, 1);
            return true;
        }
        return false;
    }

    get(id) {
        return this.images.find(img => img.id === id);
    }

    getByIndex(index) {
        return this.images[index];
    }

    findIndex(id) {
        return this.images.findIndex(img => img.id === id);
    }

    clear() {
        this.images.forEach(img => img.revokeUrl());
        this.images = [];
    }

    get count() {
        return this.images.length;
    }

    getAll() {
        return [...this.images];
    }

    reorder(newOrder) {
        this.images = newOrder;
    }
}

// Helper function to send rotated image to backend
window.sendToBackend = async (imageModel) => {
    try {
        const rotatedImage = await imageModel.rotate(-90);
        // Your existing backend sending logic here
        console.log('Sending rotated image to backend', rotatedImage);
    } catch (error) {
        console.error('Error rotating/sending image:', error);
    }
};

// Export for global use
window.ImageModel = ImageModel;
window.ImageStore = ImageStore;
