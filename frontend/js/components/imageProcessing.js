// imageProcessing.js - Vanilla JS version of AutoEdgeCrop logic

// ================== UTILITIES ==================
function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

// ================== GRAYSCALE ==================
export function toGrayscale(imageData) {
    const { data, width, height } = imageData;
    const gray = new Uint8Array(width * height);
    for (let i = 0; i < width * height; i++) {
        const idx = i * 4;
        gray[i] = Math.round(0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2]);
    }
    return { gray, width, height };
}

// ================== GAUSSIAN BLUR (5x5 kernel) ==================
export function gaussianBlur(gray, w, h) {
    const kernel = [
        1, 4, 7, 4, 1,
        4, 16, 26, 16, 4,
        7, 26, 41, 26, 7,
        4, 16, 26, 16, 4,
        1, 4, 7, 4, 1
    ];
    const kSum = 273;
    const result = new Uint8Array(w * h);
    const half = 2;

    for (let y = half; y < h - half; y++) {
        for (let x = half; x < w - half; x++) {
            let sum = 0;
            for (let ky = -half; ky <= half; ky++) {
                for (let kx = -half; kx <= half; kx++) {
                    const pixel = gray[(y + ky) * w + (x + kx)];
                    const kernelVal = kernel[(ky + half) * 5 + (kx + half)];
                    sum += pixel * kernelVal;
                }
            }
            result[y * w + x] = Math.min(255, Math.max(0, sum / kSum));
        }
    }
    return result;
}

// ================== CANNY EDGE DETECTION ==================
function sobelGradients(gray, w, h) {
    const gx = new Int16Array(w * h);
    const gy = new Int16Array(w * h);
    const magnitude = new Uint8Array(w * h);
    const direction = new Uint8Array(w * h);

    for (let y = 1; y < h - 1; y++) {
        for (let x = 1; x < w - 1; x++) {
            const idx = y * w + x;
            // Sobel X
            gx[idx] = -gray[(y - 1) * w + (x - 1)] + gray[(y - 1) * w + (x + 1)]
                - 2 * gray[y * w + (x - 1)] + 2 * gray[y * w + (x + 1)]
                - gray[(y + 1) * w + (x - 1)] + gray[(y + 1) * w + (x + 1)];
            // Sobel Y
            gy[idx] = -gray[(y - 1) * w + (x - 1)] - 2 * gray[(y - 1) * w + x] - gray[(y - 1) * w + (x + 1)]
                + gray[(y + 1) * w + (x - 1)] + 2 * gray[(y + 1) * w + x] + gray[(y + 1) * w + (x + 1)];

            const mag = Math.sqrt(gx[idx] * gx[idx] + gy[idx] * gy[idx]);
            magnitude[idx] = Math.min(255, mag);

            let angle = Math.atan2(gy[idx], gx[idx]) * (180 / Math.PI);
            if (angle < 0) angle += 180;
            // Quantize direction: 0=horizontal, 1=diag45, 2=vertical, 3=diag135
            if ((angle >= 0 && angle < 22.5) || (angle >= 157.5 && angle <= 180)) direction[idx] = 0;
            else if (angle >= 22.5 && angle < 67.5) direction[idx] = 1;
            else if (angle >= 67.5 && angle < 112.5) direction[idx] = 2;
            else direction[idx] = 3;
        }
    }
    return { magnitude, direction, gx, gy };
}

function nonMaxSuppression(magnitude, direction, w, h) {
    const suppressed = new Uint8Array(w * h);
    for (let y = 1; y < h - 1; y++) {
        for (let x = 1; x < w - 1; x++) {
            const idx = y * w + x;
            let n1 = 0, n2 = 0;
            switch (direction[idx]) {
                case 0: // horizontal
                    n1 = magnitude[idx - 1];
                    n2 = magnitude[idx + 1];
                    break;
                case 1: // 45°
                    n1 = magnitude[(y - 1) * w + (x + 1)];
                    n2 = magnitude[(y + 1) * w + (x - 1)];
                    break;
                case 2: // vertical
                    n1 = magnitude[idx - w];
                    n2 = magnitude[idx + w];
                    break;
                case 3: // 135°
                    n1 = magnitude[(y - 1) * w + (x - 1)];
                    n2 = magnitude[(y + 1) * w + (x + 1)];
                    break;
            }
            suppressed[idx] = (magnitude[idx] >= n1 && magnitude[idx] >= n2) ? magnitude[idx] : 0;
        }
    }
    return suppressed;
}

function hysteresis(edges, suppressed, w, h, lowThreshold, highThreshold) {
    const result = new Uint8Array(w * h);
    // 2 = strong, 1 = weak, 0 = none
    for (let i = 0; i < w * h; i++) {
        const mag = suppressed[i];
        if (mag >= highThreshold) edges[i] = 2;
        else if (mag >= lowThreshold) edges[i] = 1;
    }

    // Propagate weak edges connected to strong
    for (let y = 1; y < h - 1; y++) {
        for (let x = 1; x < w - 1; x++) {
            const idx = y * w + x;
            if (edges[idx] === 2) {
                result[idx] = 255;
            } else if (edges[idx] === 1) {
                let hasStrong = false;
                for (let dy = -1; dy <= 1 && !hasStrong; dy++) {
                    for (let dx = -1; dx <= 1 && !hasStrong; dx++) {
                        if (edges[(y + dy) * w + (x + dx)] === 2) hasStrong = true;
                    }
                }
                if (hasStrong) result[idx] = 255;
            }
        }
    }
    return result;
}

export function cannyEdge(gray, w, h, lowThreshold = 50, highThreshold = 150) {
    const { magnitude, direction } = sobelGradients(gray, w, h);
    const suppressed = nonMaxSuppression(magnitude, direction, w, h);
    const edges = new Uint8Array(w * h);
    return hysteresis(edges, suppressed, w, h, lowThreshold, highThreshold);
}

// ================== CONTOUR & CORNER DETECTION ==================
function convexHull(points) {
    // Monotone chain algorithm
    if (points.length <= 1) return points.slice();
    points.sort((a, b) => a[0] !== b[0] ? a[0] - b[0] : a[1] - b[1]);

    const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);

    const lower = [];
    for (let i = 0; i < points.length; i++) {
        while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], points[i]) <= 0) lower.pop();
        lower.push(points[i]);
    }

    const upper = [];
    for (let i = points.length - 1; i >= 0; i--) {
        while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], points[i]) <= 0) upper.pop();
        upper.push(points[i]);
    }

    lower.pop();
    upper.pop();
    return lower.concat(upper);
}

function polygonArea(points) {
    let area = 0;
    for (let i = 0; i < points.length; i++) {
        const j = (i + 1) % points.length;
        area += points[i][0] * points[j][1] - points[j][0] * points[i][1];
    }
    return Math.abs(area) / 2;
}

export function findDocumentCorners(edges, w, h) {
    const scale = Math.max(1, Math.floor(Math.max(w, h) / 600));
    const sw = Math.floor(w / scale);
    const sh = Math.floor(h / scale);

    // Downsample edge map
    const sedges = new Uint8Array(sw * sh);
    for (let y = 0; y < sh; y++) {
        for (let x = 0; x < sw; x++) {
            let maxVal = 0;
            for (let dy = 0; dy < scale && (y * scale + dy) < h; dy++) {
                for (let dx = 0; dx < scale && (x * scale + dx) < w; dx++) {
                    maxVal = Math.max(maxVal, edges[(y * scale + dy) * w + (x * scale + dx)]);
                }
            }
            sedges[y * sw + x] = maxVal;
        }
    }

    // Tìm contour lớn nhất (document thường là đối tượng lớn nhất)
    const visited = new Uint8Array(sw * sh);
    let bestContour = [];
    let bestArea = 0;
    const minContourPoints = 20;
    const minAreaRatio = 0.1; // Document phải chiếm ít nhất 10% ảnh

    for (let y = 0; y < sh; y++) {
        for (let x = 0; x < sw; x++) {
            if (sedges[y * sw + x] > 0 && !visited[y * sw + x]) {
                // Flood fill để tìm contour
                const contour = [];
                const stack = [[x, y]];
                visited[y * sw + x] = 1;
                while (stack.length) {
                    const [cx, cy] = stack.pop();
                    contour.push([cx, cy]);
                    // Kiểm tra 8 hướng
                    const neighbors = [
                        [cx - 1, cy], [cx + 1, cy], [cx, cy - 1], [cx, cy + 1],
                        [cx - 1, cy - 1], [cx + 1, cy + 1], [cx - 1, cy + 1], [cx + 1, cy - 1]
                    ];
                    for (const [nx, ny] of neighbors) {
                        if (nx >= 0 && nx < sw && ny >= 0 && ny < sh &&
                            !visited[ny * sw + nx] && sedges[ny * sw + nx] > 0) {
                            visited[ny * sw + nx] = 1;
                            stack.push([nx, ny]);
                        }
                    }
                }

                // Bỏ qua contour quá nhỏ
                if (contour.length < minContourPoints) continue;

                const hull = convexHull(contour);
                if (hull.length < 4) continue;

                // Approximate thành tứ giác
                const corners = approximateQuadrilateral(hull);
                if (!corners || corners.length !== 4) continue;

                // Tính diện tích tứ giác
                const area = polygonArea(corners);
                const totalArea = sw * sh;

                // Lọc: diện tích hợp lý và aspect ratio hợp lý
                const aspectRatio = calculateAspectRatio(corners);
                const areaRatio = area / totalArea;

                // Document thường có aspect ratio từ 0.3 đến 3.0 (giấy A4 ~0.7 hoặc ~1.4 khi xoay)
                if (areaRatio > minAreaRatio && aspectRatio > 0.3 && aspectRatio < 3.0 && area > bestArea) {
                    bestArea = area;
                    bestContour = corners;
                }
            }
        }
    }

    if (bestContour.length === 4) {
        // Scale về kích thước gốc và sắp xếp theo thứ tự: top-left, top-right, bottom-right, bottom-left
        const scaledCorners = bestContour.map(([x, y]) => [x * scale, y * scale]);
        return orderCorners(scaledCorners);
    }

    // Fallback: không tìm thấy document, trả về null để giữ ảnh gốc
    return null;
}

// Tìm 4 góc của tứ giác từ convex hull
function approximateQuadrilateral(hull) {
    if (hull.length <= 4) return hull;

    let maxArea = 0;
    let bestQuad = null;

    // Simplify hull trước bằng Ramer-Douglas-Peucker
    let simplified = hull;
    if (hull.length > 12) {
        let epsilon = 3;
        while (simplified.length > 8 && epsilon < 50) {
            simplified = ramerDouglasPeucker(hull, epsilon);
            epsilon *= 2;
        }
    }

    // Nếu đã đủ 4 điểm, trả về luôn
    if (simplified.length === 4) return simplified;

    // Nếu 5-8 điểm, thử tất cả combinations
    const n = simplified.length;
    for (let i = 0; i < n - 3; i++) {
        for (let j = i + 1; j < n - 2; j++) {
            for (let k = j + 1; k < n - 1; k++) {
                for (let l = k + 1; l < n; l++) {
                    const quad = [simplified[i], simplified[j], simplified[k], simplified[l]];
                    const area = polygonArea(quad);
                    if (area > maxArea) {
                        maxArea = area;
                        bestQuad = quad;
                    }
                }
            }
        }
    }

    return bestQuad;
}

// Ramer-Douglas-Peucker algorithm
function ramerDouglasPeucker(points, epsilon) {
    if (points.length <= 2) return points;

    let maxDist = 0;
    let index = 0;
    const start = points[0];
    const end = points[points.length - 1];

    for (let i = 1; i < points.length - 1; i++) {
        const dist = pointLineDistance(points[i], start, end);
        if (dist > maxDist) {
            maxDist = dist;
            index = i;
        }
    }

    if (maxDist > epsilon) {
        const left = ramerDouglasPeucker(points.slice(0, index + 1), epsilon);
        const right = ramerDouglasPeucker(points.slice(index), epsilon);
        return left.slice(0, -1).concat(right);
    }
    return [start, end];
}

function pointLineDistance(p, a, b) {
    const [x0, y0] = p;
    const [x1, y1] = a;
    const [x2, y2] = b;
    const dx = x2 - x1;
    const dy = y2 - y1;
    const len = Math.hypot(dx, dy);
    if (len === 0) return Math.hypot(x0 - x1, y0 - y1);
    const t = ((x0 - x1) * dx + (y0 - y1) * dy) / (len * len);
    if (t <= 0) return Math.hypot(x0 - x1, y0 - y1);
    if (t >= 1) return Math.hypot(x0 - x2, y0 - y2);
    const projX = x1 + t * dx;
    const projY = y1 + t * dy;
    return Math.hypot(x0 - projX, y0 - projY);
}

// Tính aspect ratio của tứ giác
function calculateAspectRatio(corners) {
    // Tính chiều dài 2 cặp cạnh đối
    const w1 = Math.hypot(corners[1][0] - corners[0][0], corners[1][1] - corners[0][1]);
    const w2 = Math.hypot(corners[2][0] - corners[3][0], corners[2][1] - corners[3][1]);
    const h1 = Math.hypot(corners[3][0] - corners[0][0], corners[3][1] - corners[0][1]);
    const h2 = Math.hypot(corners[2][0] - corners[1][0], corners[2][1] - corners[1][1]);

    const avgW = (w1 + w2) / 2;
    const avgH = (h1 + h2) / 2;

    if (avgH === 0) return 1;
    return Math.min(avgW, avgH) / Math.max(avgW, avgH);
}

// Sắp xếp 4 góc theo thứ tự: top-left, top-right, bottom-right, bottom-left
function orderCorners(corners) {
    // Phân loại dựa trên tọa độ x, y
    // Top-left: y nhỏ nhất trong 2 điểm có x nhỏ nhất
    // Top-right: y nhỏ nhất trong 2 điểm có x lớn nhất
    // Bottom-right: y lớn nhất trong 2 điểm có x lớn nhất
    // Bottom-left: y lớn nhất trong 2 điểm có x nhỏ nhất

    // Sort by x first
    const byX = [...corners].sort((a, b) => a[0] - b[0]);

    // 2 điểm bên trái (x nhỏ hơn)
    const leftPoints = [byX[0], byX[1]].sort((a, b) => a[1] - b[1]);
    const topLeft = leftPoints[0];
    const bottomLeft = leftPoints[1];

    // 2 điểm bên phải (x lớn hơn)
    const rightPoints = [byX[2], byX[3]].sort((a, b) => a[1] - b[1]);
    const topRight = rightPoints[0];
    const bottomRight = rightPoints[1];

    return [topLeft, topRight, bottomRight, bottomLeft];
}

// ================== PERSPECTIVE WARP (HOMOGRAPHY) ==================
function computeHomography(src, dst) {
    // src, dst: arrays of 4 points [x,y]
    const A = [];
    for (let i = 0; i < 4; i++) {
        const [sx, sy] = src[i];
        const [dx, dy] = dst[i];
        A.push([sx, sy, 1, 0, 0, 0, -dx * sx, -dx * sy, -dx]);
        A.push([0, 0, 0, sx, sy, 1, -dy * sx, -dy * sy, -dy]);
    }
    // Solve Ah = 0 using SVD (simplified: Gaussian elimination with last component = 1)
    const h = solveHomographyDLT(A);
    return h;
}

function solveHomographyDLT(A) {
    // Normalize rows
    for (let i = 0; i < A.length; i++) {
        let norm = 0;
        for (let j = 0; j < A[i].length; j++) norm += A[i][j] * A[i][j];
        norm = Math.sqrt(norm);
        if (norm > 0) {
            for (let j = 0; j < A[i].length; j++) A[i][j] /= norm;
        }
    }

    // Convert to matrix for Gaussian elimination (8x9)
    const n = A.length;      // 8
    const m = A[0].length;   // 9
    // Gaussian elimination with partial pivoting
    for (let col = 0; col < m - 1; col++) {
        let maxRow = col;
        let maxVal = Math.abs(A[col][col]);
        for (let row = col + 1; row < n; row++) {
            if (Math.abs(A[row][col]) > maxVal) {
                maxVal = Math.abs(A[row][col]);
                maxRow = row;
            }
        }
        if (maxVal < 1e-12) continue;
        [A[col], A[maxRow]] = [A[maxRow], A[col]];
        for (let row = col + 1; row < n; row++) {
            const factor = A[row][col] / A[col][col];
            for (let j = col; j < m; j++) {
                A[row][j] -= factor * A[col][j];
            }
        }
    }

    // Back substitution (since last column is zero, we set h8 = 1)
    const h = new Array(m).fill(0);
    h[m - 1] = 1;
    for (let i = m - 2; i >= 0; i--) {
        let sum = 0;
        for (let j = i + 1; j < m - 1; j++) {
            sum += A[i][j] * h[j];
        }
        if (Math.abs(A[i][i]) > 1e-12) {
            h[i] = (A[i][m - 1] - sum) / A[i][i];
        } else {
            h[i] = 0;
        }
    }
    return h;
}

export function perspectiveWarp(srcCanvas, corners, dstWidth, dstHeight) {
    const srcCtx = srcCanvas.getContext('2d');
    const srcData = srcCtx.getImageData(0, 0, srcCanvas.width, srcCanvas.height);

    const dstCanvas = document.createElement('canvas');
    dstCanvas.width = dstWidth;
    dstCanvas.height = dstHeight;
    const dstCtx = dstCanvas.getContext('2d');
    const dstData = dstCtx.createImageData(dstWidth, dstHeight);

    // Destination corners: rectangle
    const dst = [
        [0, 0],
        [dstWidth, 0],
        [dstWidth, dstHeight],
        [0, dstHeight]
    ];

    // Compute homography: dst → src (inverse direction for inverse mapping)
    const H = computeHomography(dst, corners);
    
    // Inverse mapping: for each dest pixel, find source coordinate
    for (let y = 0; y < dstHeight; y++) {
        for (let x = 0; x < dstWidth; x++) {
            const denominator = H[6] * x + H[7] * y + H[8];
            if (Math.abs(denominator) < 1e-12) continue;
            const srcX = (H[0] * x + H[1] * y + H[2]) / denominator;
            const srcY = (H[3] * x + H[4] * y + H[5]) / denominator;

            if (srcX < 0 || srcX >= srcCanvas.width - 1 || srcY < 0 || srcY >= srcCanvas.height - 1) continue;

            // Bilinear interpolation
            const x0 = Math.floor(srcX);
            const y0 = Math.floor(srcY);
            const x1 = x0 + 1;
            const y1 = y0 + 1;
            const fx = srcX - x0;
            const fy = srcY - y0;

            const idx00 = (y0 * srcCanvas.width + x0) * 4;
            const idx10 = (y0 * srcCanvas.width + x1) * 4;
            const idx01 = (y1 * srcCanvas.width + x0) * 4;
            const idx11 = (y1 * srcCanvas.width + x1) * 4;

            const dstIdx = (y * dstWidth + x) * 4;
            for (let c = 0; c < 3; c++) {
                const top = srcData.data[idx00 + c] * (1 - fx) + srcData.data[idx10 + c] * fx;
                const bottom = srcData.data[idx01 + c] * (1 - fx) + srcData.data[idx11 + c] * fx;
                dstData.data[dstIdx + c] = top * (1 - fy) + bottom * fy;
            }
            dstData.data[dstIdx + 3] = 255;
        }
    }

    dstCtx.putImageData(dstData, 0, 0);
    return dstCanvas;
}

// ================== HIGH-LEVEL AUTO CROP ==================
export async function autoCropCanvas(inputCanvas, resizeForDetection = true) {
    // Nếu ảnh quá lớn, resize tạm thời để tìm góc
    let workingCanvas = inputCanvas;
    let scaleX = 1, scaleY = 1;
    if (resizeForDetection && (inputCanvas.width > 1200 || inputCanvas.height > 1200)) {
        const maxDim = 1000;
        let ratio = Math.min(maxDim / inputCanvas.width, maxDim / inputCanvas.height);
        const smallCanvas = document.createElement('canvas');
        smallCanvas.width = inputCanvas.width * ratio;
        smallCanvas.height = inputCanvas.height * ratio;
        const ctx = smallCanvas.getContext('2d');
        ctx.drawImage(inputCanvas, 0, 0, smallCanvas.width, smallCanvas.height);
        workingCanvas = smallCanvas;
        scaleX = inputCanvas.width / smallCanvas.width;
        scaleY = inputCanvas.height / smallCanvas.height;
    }

    const ctx = workingCanvas.getContext('2d');
    const imageData = ctx.getImageData(0, 0, workingCanvas.width, workingCanvas.height);
    const { gray, width, height } = toGrayscale(imageData);
    const blurred = gaussianBlur(gray, width, height);
    const edges = cannyEdge(blurred, width, height, 50, 150);
    let corners = findDocumentCorners(edges, width, height);

    if (corners && corners.length === 4) {
        // Scale corners back to original size if we resized
        if (scaleX !== 1 || scaleY !== 1) {
            corners = corners.map(([x, y]) => [x * scaleX, y * scaleY]);
        }
        // Calculate output dimensions
        const topW = Math.hypot(corners[1][0] - corners[0][0], corners[1][1] - corners[0][1]);
        const botW = Math.hypot(corners[2][0] - corners[3][0], corners[2][1] - corners[3][1]);
        const leftH = Math.hypot(corners[3][0] - corners[0][0], corners[3][1] - corners[0][1]);
        const rightH = Math.hypot(corners[2][0] - corners[1][0], corners[2][1] - corners[1][1]);
        const outW = Math.round(Math.max(topW, botW));
        const outH = Math.round(Math.max(leftH, rightH));
        if (outW > 0 && outH > 0) {
            return perspectiveWarp(inputCanvas, corners, outW, outH);
        }
    }
    return null; // No crop performed
}