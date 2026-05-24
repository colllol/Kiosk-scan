const MODEL_URLS = [
    '/best.onnx',
    'http://localhost:5000/api/model/document.onnx',
];
const INPUT_SIZE = 640;
const LIVE_DETECTION_MAX_DIM = 1280;
const LIVE_DETECTION_INTERVAL_MS = 180;
const IOU_THRESHOLD = 0.45;
const SCORE_THRESHOLD = 0.55;
const MIN_DOCUMENT_AREA_RATIO = 0.01;
const MAX_DOCUMENT_AREA_RATIO = 0.985;
const MIN_BOX_ONLY_AREA_RATIO = 0.06;
const MIN_DOCUMENT_SHORT_SIDE_RATIO = 0.07;
const CANNY_LOW = 60;
const CANNY_HIGH = 160;
const CONTOUR_APPROX_RATIO = 0.035;
const CORNER_CANNY_LOW = 45;
const CORNER_CANNY_HIGH = 140;
const CORNER_APPROX_RATIO = 0.03;

class DocumentScanner {
    constructor() {
        this.cvReady = false;
        this.session = null;
        this.initPromise = null;
        this.frameCanvas = document.createElement('canvas');
        this.frameCtx = this.frameCanvas.getContext('2d', { willReadFrequently: true });
        this.prepCanvas = document.createElement('canvas');
        this.prepCanvas.width = INPUT_SIZE;
        this.prepCanvas.height = INPUT_SIZE;
        this.prepCtx = this.prepCanvas.getContext('2d', { willReadFrequently: true });
        this.liveVideo = null;
        this.overlay = null;
        this.statusEl = null;
        this.liveRunning = false;
        this.liveBusy = false;
        this.liveFrameId = 0;
        this.lastLiveDetection = null;
        this.lastLiveDetectAt = 0;
    }

    init() {
        if (!this.initPromise) {
            this.initPromise = Promise.all([this.waitForOpenCv(), this.loadModel()]).catch((error) => {
                console.warn('[DocumentScanner] init warning:', error);
            });
        }
        return this.initPromise;
    }

    waitForOpenCv(timeoutMs = 15000) {
        if (window.cv?.Mat && window.cv?.imread) {
            this.cvReady = true;
            return Promise.resolve(true);
        }

        return new Promise((resolve) => {
            const started = performance.now();
            const timer = window.setInterval(() => {
                if (window.cv?.Mat && window.cv?.imread) {
                    window.clearInterval(timer);
                    this.cvReady = true;
                    resolve(true);
                    return;
                }
                if (performance.now() - started > timeoutMs) {
                    window.clearInterval(timer);
                    resolve(false);
                }
            }, 100);
        });
    }

    async loadModel() {
        if (!window.ort?.InferenceSession) {
            console.warn('[DocumentScanner] onnxruntime-web is not loaded; using OpenCV contour fallback.');
            return null;
        }

        if (window.ort.env?.wasm) {
            window.ort.env.wasm.numThreads = 1;
        }

        for (const url of MODEL_URLS) {
            try {
                this.session = await window.ort.InferenceSession.create(`${url}?t=${Date.now()}`, {
                    executionProviders: ['wasm'],
                    graphOptimizationLevel: 'all',
                });
                console.info(`[DocumentScanner] YOLO model loaded: ${url}`);
                return this.session;
            } catch (error) {
                console.warn(`[DocumentScanner] Cannot load YOLO ONNX from ${url}.`, error);
            }
        }

        this.session = null;
        console.warn('[DocumentScanner] Cannot load any YOLO ONNX model; using OpenCV contour fallback.');
        return this.session;
    }

    async cropCanvas(inputCanvas, detection = null) {
        await this.init();
        this.frameCanvas.width = inputCanvas.width;
        this.frameCanvas.height = inputCanvas.height;
        this.frameCtx.drawImage(inputCanvas, 0, 0);

        const cropDetection = detection
            || this.getLastLiveDetectionForCanvas(inputCanvas.width, inputCanvas.height)
            || await this.detectDocument();
        if (!cropDetection) return null;
        return this.cropAndDeskew(cropDetection.box, cropDetection.corners);
    }

    getLastLiveDetectionForCanvas(targetWidth, targetHeight) {
        if (!this.lastLiveDetection || !this.liveVideo?.videoWidth || !this.liveVideo?.videoHeight) {
            return null;
        }

        const sourceWidth = this.liveVideo.videoWidth;
        const transformPoint = (point) => ({
            x: clamp(point.y, 0, targetWidth),
            y: clamp(sourceWidth - point.x, 0, targetHeight),
        });

        const corners = this.lastLiveDetection.corners
            ? this.lastLiveDetection.corners.map(transformPoint)
            : boxToPoints(this.lastLiveDetection.box).map(transformPoint);
        const orderedCorners = orderPoints(corners);
        return {
            ...this.lastLiveDetection,
            box: pointsToBox(orderedCorners, targetWidth, targetHeight),
            corners: orderedCorners,
            source: `${this.lastLiveDetection.source}-cached`,
        };
    }

    startLiveDetection(video, overlay, statusEl = null) {
        if (!video || !overlay) return;
        this.liveVideo = video;
        this.overlay = overlay;
        this.statusEl = statusEl;
        this.liveRunning = true;
        this.setStatus('Dang nhan dien tai lieu...');
        this.liveFrameId = window.requestAnimationFrame(() => this.liveLoop());
    }

    stopLiveDetection() {
        this.liveRunning = false;
        if (this.liveFrameId) window.cancelAnimationFrame(this.liveFrameId);
        this.liveFrameId = 0;
        this.lastLiveDetection = null;
        this.clearOverlay();
    }

    async liveLoop() {
        if (!this.liveRunning) return;

        const video = this.liveVideo;
        const now = performance.now();
        if (
            !this.liveBusy
            && now - this.lastLiveDetectAt >= LIVE_DETECTION_INTERVAL_MS
            && video?.readyState >= 2
            && video.videoWidth > 0
            && video.videoHeight > 0
        ) {
            this.liveBusy = true;
            this.lastLiveDetectAt = now;
            try {
                const scale = Math.min(1, LIVE_DETECTION_MAX_DIM / Math.max(video.videoWidth, video.videoHeight));
                this.frameCanvas.width = Math.max(1, Math.round(video.videoWidth * scale));
                this.frameCanvas.height = Math.max(1, Math.round(video.videoHeight * scale));
                this.frameCtx.drawImage(video, 0, 0, this.frameCanvas.width, this.frameCanvas.height);
                const detection = await this.detectDocument();
                this.lastLiveDetection = detection
                    ? scaleDetection(detection, video.videoWidth / this.frameCanvas.width, video.videoHeight / this.frameCanvas.height)
                    : null;
                this.drawOverlay(detection);
            } catch (error) {
                console.warn('[DocumentScanner] live detection failed:', error);
                this.clearOverlay();
                this.setStatus('Nhan dien tai lieu bi loi.');
            } finally {
                this.liveBusy = false;
            }
        }

        this.liveFrameId = window.requestAnimationFrame(() => this.liveLoop());
    }

    async detectDocument() {
        if (this.session) {
            try {
                const detection = await this.detectWithYolo();
                if (detection) return detection;
            } catch (error) {
                console.warn('[DocumentScanner] YOLO detection failed; switching to contour fallback.', error);
                this.session = null;
            }
        }

        return this.cvReady ? this.detectDocumentContour() : null;
    }

    drawOverlay(detection) {
        if (!this.overlay) return;

        const metrics = this.updateOverlaySize();

        const ctx = this.overlay.getContext('2d');
        ctx.clearRect(0, 0, this.overlay.width, this.overlay.height);

        if (!detection) {
            this.setStatus(this.cvReady || this.session ? 'Dua tai lieu vao khung camera.' : 'Dang tai bo phat hien tai lieu...');
            return;
        }

        const corners = detection.corners ? orderPoints(detection.corners) : boxToPoints(detection.box);
        const drawCorners = corners.map((point) => mapFramePoint(point, metrics));
        const { x, y, score } = detection.box;
        const labelPoint = mapFramePoint({ x: x + 10, y: Math.max(28, y - 10) }, metrics);

        ctx.save();
        ctx.lineJoin = 'round';
        ctx.shadowColor = 'rgba(0, 0, 0, 0.55)';
        ctx.shadowBlur = 8;
        ctx.strokeStyle = '#07110e';
        ctx.lineWidth = 9;
        drawPointPath(ctx, drawCorners);
        ctx.stroke();

        ctx.shadowBlur = 0;
        ctx.strokeStyle = '#47d7ac';
        ctx.lineWidth = 5;
        drawPointPath(ctx, drawCorners);
        ctx.stroke();

        ctx.fillStyle = 'rgba(71, 215, 172, 0.16)';
        drawPointPath(ctx, drawCorners);
        ctx.fill();

        drawCornerHandles(ctx, drawCorners);

        const label = `${detection.source}${score ? ` ${(score * 100).toFixed(0)}%` : ''}`;
        ctx.fillStyle = '#47d7ac';
        ctx.font = '24px sans-serif';
        ctx.fillText(label, labelPoint.x, labelPoint.y);
        ctx.restore();

        this.setStatus(`${label}. Da phat hien tai lieu.`);
    }

    updateOverlaySize() {
        const width = Math.max(1, Math.round(this.overlay.clientWidth || this.frameCanvas.width));
        const height = Math.max(1, Math.round(this.overlay.clientHeight || this.frameCanvas.height));
        if (this.overlay.width !== width) this.overlay.width = width;
        if (this.overlay.height !== height) this.overlay.height = height;

        return getFrameToOverlayMetrics(
            this.frameCanvas.width,
            this.frameCanvas.height,
            width,
            height,
            this.liveVideo,
            this.overlay,
        );
    }

    clearOverlay() {
        if (!this.overlay) return;
        this.updateOverlaySize();
        const ctx = this.overlay.getContext('2d');
        ctx.clearRect(0, 0, this.overlay.width, this.overlay.height);
    }

    setStatus(message) {
        if (this.statusEl) this.statusEl.textContent = message;
    }

    async detectWithYolo() {
        this.prepCtx.fillStyle = '#000';
        this.prepCtx.fillRect(0, 0, INPUT_SIZE, INPUT_SIZE);

        const scale = Math.min(INPUT_SIZE / this.frameCanvas.width, INPUT_SIZE / this.frameCanvas.height);
        const drawW = this.frameCanvas.width * scale;
        const drawH = this.frameCanvas.height * scale;
        const padX = (INPUT_SIZE - drawW) / 2;
        const padY = (INPUT_SIZE - drawH) / 2;
        this.prepCtx.drawImage(this.frameCanvas, padX, padY, drawW, drawH);

        const image = this.prepCtx.getImageData(0, 0, INPUT_SIZE, INPUT_SIZE).data;
        const input = new Float32Array(3 * INPUT_SIZE * INPUT_SIZE);
        const plane = INPUT_SIZE * INPUT_SIZE;
        for (let i = 0; i < plane; i += 1) {
            input[i] = image[i * 4] / 255;
            input[i + plane] = image[i * 4 + 1] / 255;
            input[i + plane * 2] = image[i * 4 + 2] / 255;
        }

        const tensor = new window.ort.Tensor('float32', input, [1, 3, INPUT_SIZE, INPUT_SIZE]);
        const output = await this.session.run({ [this.session.inputNames[0]]: tensor });
        const result = output[this.session.outputNames[0]];
        const boxes = this.parseYoloOutput(result, scale, padX, padY);
        return boxes[0] ? { box: boxes[0], source: 'YOLO' } : null;
    }

    parseYoloOutput(result, scale, padX, padY) {
        const data = result.data;
        const dims = result.dims;
        const rows = dims[1] < dims[2] ? dims[2] : dims[1];
        const cols = dims[1] < dims[2] ? dims[1] : dims[2];
        const transposed = dims[1] < dims[2];
        const candidates = [];

        for (let i = 0; i < rows; i += 1) {
            const at = (c) => (transposed ? data[c * rows + i] : data[i * cols + c]);
            const cx = at(0);
            const cy = at(1);
            const w = at(2);
            const h = at(3);
            let score = at(4);
            for (let c = 5; c < cols; c += 1) score = Math.max(score, at(c));
            if (score < SCORE_THRESHOLD) continue;

            const x = (cx - w / 2 - padX) / scale;
            const y = (cy - h / 2 - padY) / scale;
            candidates.push({
                x: clamp(x, 0, this.frameCanvas.width),
                y: clamp(y, 0, this.frameCanvas.height),
                w: clamp(w / scale, 0, this.frameCanvas.width),
                h: clamp(h / scale, 0, this.frameCanvas.height),
                score,
            });
        }

        return nms(candidates).slice(0, 1);
    }

    detectDocumentContour() {
        const src = window.cv.imread(this.frameCanvas);
        const gray = new window.cv.Mat();
        const blur = new window.cv.Mat();
        const edges = new window.cv.Mat();
        const binary = new window.cv.Mat();
        const kernel = window.cv.Mat.ones(7, 7, window.cv.CV_8U);
        const contours = new window.cv.MatVector();
        const hierarchy = new window.cv.Mat();
        let best = null;

        window.cv.cvtColor(src, gray, window.cv.COLOR_RGBA2GRAY);
        window.cv.GaussianBlur(gray, blur, new window.cv.Size(5, 5), 0);
        window.cv.Canny(blur, edges, CANNY_LOW, CANNY_HIGH);
        window.cv.findContours(edges, contours, hierarchy, window.cv.RETR_EXTERNAL, window.cv.CHAIN_APPROX_SIMPLE);
        best = this.findBestContourBox(contours, best);

        contours.delete();
        hierarchy.delete();

        const brightContours = new window.cv.MatVector();
        const brightHierarchy = new window.cv.Mat();
        window.cv.threshold(blur, binary, 0, 255, window.cv.THRESH_BINARY + window.cv.THRESH_OTSU);
        window.cv.morphologyEx(binary, binary, window.cv.MORPH_CLOSE, kernel);
        window.cv.findContours(binary, brightContours, brightHierarchy, window.cv.RETR_EXTERNAL, window.cv.CHAIN_APPROX_SIMPLE);
        best = this.findBestContourBox(brightContours, best);

        src.delete();
        gray.delete();
        blur.delete();
        edges.delete();
        binary.delete();
        kernel.delete();
        brightContours.delete();
        brightHierarchy.delete();

        return best ? { box: best.box, corners: best.corners, source: 'Contour' } : null;
    }

    findBestContourBox(contours, currentBest) {
        let best = currentBest;
        const frameArea = this.frameCanvas.width * this.frameCanvas.height;
        const minShortSide = Math.min(this.frameCanvas.width, this.frameCanvas.height) * MIN_DOCUMENT_SHORT_SIDE_RATIO;
        const minArea = frameArea * MIN_DOCUMENT_AREA_RATIO;
        const maxArea = frameArea * MAX_DOCUMENT_AREA_RATIO;

        for (let i = 0; i < contours.size(); i += 1) {
            const contour = contours.get(i);
            const area = window.cv.contourArea(contour);
            if (area < minArea || area > maxArea) {
                contour.delete();
                continue;
            }

            const rect = normalizeCvRect(window.cv.boundingRect(contour));
            const rectArea = rect.w * rect.h;
            const fillRatio = rectArea > 0 ? area / rectArea : 0;
            const aspect = rect.w / rect.h;
            const shortSide = Math.min(rect.w, rect.h);
            if (aspect < 0.45 || aspect > 2.25 || fillRatio < 0.35 || shortSide < minShortSide) {
                contour.delete();
                continue;
            }

            const peri = window.cv.arcLength(contour, true);
            const approx = new window.cv.Mat();
            window.cv.approxPolyDP(contour, approx, CONTOUR_APPROX_RATIO * peri, true);
            const corners = approx.rows === 4 ? pointsFromMat(approx) : null;
            if (!corners && area / frameArea < MIN_BOX_ONLY_AREA_RATIO) {
                approx.delete();
                contour.delete();
                continue;
            }

            const portraitAspect = Math.min(aspect, 1 / aspect);
            const documentAspectScore = 1 - Math.min(1, Math.abs(portraitAspect - 0.707) / 0.35);
            const score = area * fillRatio * (corners ? 4 : 1) * (0.7 + documentAspectScore * 0.3);
            if (!best || score > best.score) best = { area, score, box: rect, corners };
            approx.delete();
            contour.delete();
        }

        return best;
    }

    cropAndDeskew(box, corners = null) {
        const src = window.cv.imread(this.frameCanvas);
        let roi = null;
        let output;

        if (corners?.length === 4) {
            output = warpDocument(src, corners);
        } else {
            const roiRect = expandRect(box, 0.06, src.cols, src.rows);
            roi = src.roi(roiRect);
            const points = findDocumentCorners(roi);
            if (points) {
                output = warpDocument(src, points.map((p) => ({ x: p.x + roiRect.x, y: p.y + roiRect.y })));
            } else {
                output = roi.clone();
            }
        }

        const normalized = normalizeOrientation(output);
        const enhanced = enhanceCroppedDocument(normalized);
        const canvas = document.createElement('canvas');
        window.cv.imshow(canvas, enhanced);

        src.delete();
        if (roi) roi.delete();
        output.delete();
        normalized.delete();
        enhanced.delete();
        return canvas;
    }
}

function enhanceCroppedDocument(mat) {
    const blurred = new window.cv.Mat();
    const enhanced = new window.cv.Mat();
    window.cv.GaussianBlur(mat, blurred, new window.cv.Size(0, 0), 1.0);
    window.cv.addWeighted(mat, 1.18, blurred, -0.18, 4, enhanced);
    blurred.delete();
    return enhanced;
}

function findDocumentCorners(mat) {
    const gray = new window.cv.Mat();
    const blur = new window.cv.Mat();
    const edges = new window.cv.Mat();
    const contours = new window.cv.MatVector();
    const hierarchy = new window.cv.Mat();
    let best = null;
    let bestArea = 0;
    const matArea = mat.cols * mat.rows;

    window.cv.cvtColor(mat, gray, window.cv.COLOR_RGBA2GRAY);
    window.cv.GaussianBlur(gray, blur, new window.cv.Size(5, 5), 0);
    window.cv.Canny(blur, edges, CORNER_CANNY_LOW, CORNER_CANNY_HIGH);
    window.cv.findContours(edges, contours, hierarchy, window.cv.RETR_EXTERNAL, window.cv.CHAIN_APPROX_SIMPLE);

    for (let i = 0; i < contours.size(); i += 1) {
        const contour = contours.get(i);
        const peri = window.cv.arcLength(contour, true);
        const approx = new window.cv.Mat();
        window.cv.approxPolyDP(contour, approx, CORNER_APPROX_RATIO * peri, true);
        const area = window.cv.contourArea(approx);
        const rect = normalizeCvRect(window.cv.boundingRect(approx));
        const rectArea = rect.w * rect.h;
        const aspect = rect.w / rect.h;
        const fillRatio = rectArea > 0 ? area / rectArea : 0;
        if (approx.rows === 4 && area >= matArea * 0.18 && area <= matArea * 0.98 && aspect >= 0.45 && aspect <= 2.25 && fillRatio >= 0.35 && area > bestArea) {
            bestArea = area;
            best = pointsFromMat(approx);
        }
        approx.delete();
        contour.delete();
    }

    gray.delete();
    blur.delete();
    edges.delete();
    contours.delete();
    hierarchy.delete();
    return best ? orderPoints(best) : null;
}

function warpDocument(src, points) {
    const [tl, tr, br, bl] = orderPoints(points);
    const width = Math.max(1, Math.round(Math.max(distance(br, bl), distance(tr, tl))));
    const height = Math.max(1, Math.round(Math.max(distance(tr, br), distance(tl, bl))));
    const dst = new window.cv.Mat();
    const srcTri = window.cv.matFromArray(4, 1, window.cv.CV_32FC2, [tl.x, tl.y, tr.x, tr.y, br.x, br.y, bl.x, bl.y]);
    const dstTri = window.cv.matFromArray(4, 1, window.cv.CV_32FC2, [0, 0, width - 1, 0, width - 1, height - 1, 0, height - 1]);
    const matrix = window.cv.getPerspectiveTransform(srcTri, dstTri);
    window.cv.warpPerspective(src, dst, matrix, new window.cv.Size(width, height), window.cv.INTER_LINEAR, window.cv.BORDER_CONSTANT);
    srcTri.delete();
    dstTri.delete();
    matrix.delete();
    return dst;
}

function normalizeOrientation(mat) {
    if (mat.cols <= mat.rows) return mat.clone();
    const rotated = new window.cv.Mat();
    window.cv.rotate(mat, rotated, window.cv.ROTATE_90_CLOCKWISE);
    return rotated;
}

function pointsFromMat(mat) {
    const points = [];
    for (let r = 0; r < mat.rows; r += 1) {
        points.push({ x: mat.intPtr(r, 0)[0], y: mat.intPtr(r, 0)[1] });
    }
    return orderPoints(points);
}

function boxToPoints(box) {
    return [
        { x: box.x, y: box.y },
        { x: box.x + box.w, y: box.y },
        { x: box.x + box.w, y: box.y + box.h },
        { x: box.x, y: box.y + box.h },
    ];
}

function pointsToBox(points, maxW, maxH) {
    const xs = points.map((point) => point.x);
    const ys = points.map((point) => point.y);
    const x = clamp(Math.min(...xs), 0, maxW);
    const y = clamp(Math.min(...ys), 0, maxH);
    const right = clamp(Math.max(...xs), 0, maxW);
    const bottom = clamp(Math.max(...ys), 0, maxH);
    return { x, y, w: right - x, h: bottom - y };
}

function scaleDetection(detection, scaleX, scaleY) {
    const scalePoint = (point) => ({ x: point.x * scaleX, y: point.y * scaleY });
    return {
        ...detection,
        box: {
            ...detection.box,
            x: detection.box.x * scaleX,
            y: detection.box.y * scaleY,
            w: detection.box.w * scaleX,
            h: detection.box.h * scaleY,
        },
        corners: detection.corners ? detection.corners.map(scalePoint) : null,
    };
}

function drawPointPath(ctx, points) {
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i += 1) ctx.lineTo(points[i].x, points[i].y);
    ctx.closePath();
}

function drawCornerHandles(ctx, points) {
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 3;
    for (const point of points) {
        ctx.beginPath();
        ctx.arc(point.x, point.y, 8, 0, Math.PI * 2);
        ctx.stroke();
    }
}

function getFrameToOverlayMetrics(frameWidth, frameHeight, overlayWidth, overlayHeight, video = null, overlay = null) {
    const objectFit = video ? window.getComputedStyle(video).objectFit : 'fill';
    const rotation = getQuarterTurnRotation(video);
    let scaleX = overlayWidth / frameWidth;
    let scaleY = overlayHeight / frameHeight;
    let offsetX = 0;
    let offsetY = 0;
    let scale = null;
    let padX = 0;
    let padY = 0;
    let drawnWidth = overlayWidth;
    let drawnHeight = overlayHeight;

    if (rotation) {
        const videoRect = video.getBoundingClientRect();
        const anchorRect = (overlay || video.parentElement).getBoundingClientRect();
        drawnWidth = videoRect.width || overlayWidth;
        drawnHeight = videoRect.height || overlayHeight;
        offsetX = videoRect.left - anchorRect.left;
        offsetY = videoRect.top - anchorRect.top;

        const preRotateWidth = drawnHeight;
        const preRotateHeight = drawnWidth;
        scale = objectFit === 'cover'
            ? Math.max(preRotateWidth / frameWidth, preRotateHeight / frameHeight)
            : Math.min(preRotateWidth / frameWidth, preRotateHeight / frameHeight);
        padX = (preRotateWidth - frameWidth * scale) / 2;
        padY = (preRotateHeight - frameHeight * scale) / 2;

        return { rotation, scale, offsetX, offsetY, padX, padY, drawnWidth, drawnHeight };
    }

    if (objectFit === 'contain' || objectFit === 'cover') {
        scale = objectFit === 'contain'
            ? Math.min(scaleX, scaleY)
            : Math.max(scaleX, scaleY);
        drawnWidth = frameWidth * scale;
        drawnHeight = frameHeight * scale;
        scaleX = scale;
        scaleY = scale;
        offsetX = (overlayWidth - drawnWidth) / 2;
        offsetY = (overlayHeight - drawnHeight) / 2;
    }

    return { scaleX, scaleY, offsetX, offsetY };
}

function getQuarterTurnRotation(video) {
    if (!video) return null;
    const transform = window.getComputedStyle(video).transform;
    if (!transform || transform === 'none') return null;

    const match = transform.match(/matrix\(([^)]+)\)/);
    if (!match) return null;
    const [a, b, c, d] = match[1].split(',').slice(0, 4).map((value) => Number.parseFloat(value.trim()));

    if (Math.abs(a) < 0.01 && Math.abs(d) < 0.01 && b > 0.9 && c < -0.9) return 'cw';
    if (Math.abs(a) < 0.01 && Math.abs(d) < 0.01 && b < -0.9 && c > 0.9) return 'ccw';
    return null;
}

function mapFramePoint(point, metrics) {
    if (metrics.rotation === 'cw') {
        const x = point.x * metrics.scale + metrics.padX;
        const y = point.y * metrics.scale + metrics.padY;
        return {
            x: metrics.offsetX + metrics.drawnWidth - y,
            y: metrics.offsetY + x,
        };
    }

    if (metrics.rotation === 'ccw') {
        const x = point.x * metrics.scale + metrics.padX;
        const y = point.y * metrics.scale + metrics.padY;
        return {
            x: metrics.offsetX + y,
            y: metrics.offsetY + metrics.drawnHeight - x,
        };
    }

    return {
        x: point.x * metrics.scaleX + metrics.offsetX,
        y: point.y * metrics.scaleY + metrics.offsetY,
    };
}

function orderPoints(points) {
    const center = points.reduce(
        (sum, point) => ({ x: sum.x + point.x / points.length, y: sum.y + point.y / points.length }),
        { x: 0, y: 0 },
    );
    const ordered = [...points].sort(
        (a, b) => Math.atan2(a.y - center.y, a.x - center.x) - Math.atan2(b.y - center.y, b.x - center.x),
    );
    const topLeftIndex = ordered.reduce((bestIndex, point, index) => {
        const best = ordered[bestIndex];
        return point.x + point.y < best.x + best.y ? index : bestIndex;
    }, 0);
    return [...ordered.slice(topLeftIndex), ...ordered.slice(0, topLeftIndex)];
}

function normalizeCvRect(rect) {
    return { x: rect.x, y: rect.y, w: rect.w ?? rect.width, h: rect.h ?? rect.height };
}

function expandRect(box, amount, maxW, maxH) {
    const padX = box.w * amount;
    const padY = box.h * amount;
    const x = Math.max(0, Math.floor(box.x - padX));
    const y = Math.max(0, Math.floor(box.y - padY));
    const w = Math.min(maxW - x, Math.floor(box.w + padX * 2));
    const h = Math.min(maxH - y, Math.floor(box.h + padY * 2));
    return new window.cv.Rect(x, y, w, h);
}

function nms(boxes) {
    const sorted = boxes.sort((a, b) => b.score - a.score);
    const keep = [];
    while (sorted.length) {
        const current = sorted.shift();
        keep.push(current);
        for (let i = sorted.length - 1; i >= 0; i -= 1) {
            if (iou(current, sorted[i]) > IOU_THRESHOLD) sorted.splice(i, 1);
        }
    }
    return keep;
}

function iou(a, b) {
    const x1 = Math.max(a.x, b.x);
    const y1 = Math.max(a.y, b.y);
    const x2 = Math.min(a.x + a.w, b.x + b.w);
    const y2 = Math.min(a.y + a.h, b.y + b.h);
    const intersection = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
    return intersection / (a.w * a.h + b.w * b.h - intersection);
}

function distance(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y);
}

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

export { DocumentScanner };
