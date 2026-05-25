/**
Configuration for Webcam Scan Document App
*/
const CONFIG = {
    SCAN_PROFILE: 'smallDocument',
    SCAN_PROFILES: {
        balanced: {
            cameraWidth: 2560,
            cameraHeight: 1440,
            cameraFrameRate: 12,
            detectionMaxDim: 960,
            detectionIntervalMs: 320,
            outputMaxLongSide: 2400,
            cropRoiPadding: 0.10,
            jpegQuality: 0.94,
        },
        smallDocument: {
            cameraWidth: 3840,
            cameraHeight: 2160,
            cameraFrameRate: 10,
            detectionMaxDim: 1280,
            detectionIntervalMs: 380,
            outputMaxLongSide: 2800,
            cropRoiPadding: 0.12,
            jpegQuality: 0.95,
        },
    },
    MAX_WIDTH: 3840,          // Giảm xuống Full HD để tăng tốc độ
    MAX_HEIGHT: 2160,
    JPEG_QUALITY: 0.95,
    VIRTUAL_SCROLL_THRESHOLD: 50,
    API_UPLOAD: 'http://localhost:5000/api/upload',
    API_EXPORT: 'http://localhost:5000/api/export',
    MAX_PARALLEL_UPLOADS: 3,
    
    // Image enhancement settings for preview
    PREVIEW_BRIGHTNESS: 20,   // +20 brightness for preview
    PREVIEW_CONTRAST: 1.3     // 1.3x contrast for preview
};

CONFIG.ACTIVE_SCAN_PROFILE = CONFIG.SCAN_PROFILES[CONFIG.SCAN_PROFILE] || CONFIG.SCAN_PROFILES.balanced;

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

export { CONFIG, state };
