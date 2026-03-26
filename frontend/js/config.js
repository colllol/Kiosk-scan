/**
Configuration for Webcam Scan Document App
*/
const CONFIG = {
    MAX_WIDTH: 4608,          // Giữ nguyên độ phân giải cao
    JPEG_QUALITY: 0.95,       // Chất lượng cao (95%) để backend xử lý tốt hơn
    VIRTUAL_SCROLL_THRESHOLD: 50,
    API_UPLOAD: 'http://localhost:5000/api/upload',
    API_EXPORT: 'http://localhost:5000/api/export',
    MAX_PARALLEL_UPLOADS: 5,
    
    // Image enhancement settings for preview
    PREVIEW_BRIGHTNESS: 20,   // +20 brightness for preview
    PREVIEW_CONTRAST: 1.3     // 1.3x contrast for preview
};

// App State
const state = {
    images: [],
    documentIds: [],
    stream: null,
    sortable: null,
    currentLightboxIndex: 0,
    isLoading: false,
    pinchStartDistance: 0,
    currentScale: 1
};