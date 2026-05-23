const video = document.querySelector("#camera");
const overlay = document.querySelector("#overlay");
const statusEl = document.querySelector("#status");
const startBtn = document.querySelector("#startBtn");
const snapBtn = document.querySelector("#snapBtn");
const pdfBtn = document.querySelector("#pdfBtn");
const clearBtn = document.querySelector("#clearBtn");
const capturesEl = document.querySelector("#captures");
const modelInput = document.querySelector("#modelInput");
const scoreInput = document.querySelector("#scoreInput");
const stableInput = document.querySelector("#stableInput");
const autoInput = document.querySelector("#autoInput");

const MODEL_PATH = "/best.onnx";
const INPUT_SIZE = 640;
const IOU_THRESHOLD = 0.45;
const AUTO_CAPTURE_COOLDOWN = 5000;
const MIN_DOCUMENT_AREA_RATIO = 0.01;
const MAX_DOCUMENT_AREA_RATIO = 0.985;
const MIN_BOX_ONLY_AREA_RATIO = 0.06;
const MIN_DOCUMENT_SHORT_SIDE_RATIO = 0.07;

let cvReady = false;
let session = null;
let stream = null;
let running = false;
let lastBox = null;
let stableSince = 0;
let lastCaptureAt = -AUTO_CAPTURE_COOLDOWN;
let captures = [];

const frameCanvas = document.createElement("canvas");
const frameCtx = frameCanvas.getContext("2d", { willReadFrequently: true });
const prepCanvas = document.createElement("canvas");
prepCanvas.width = INPUT_SIZE;
prepCanvas.height = INPUT_SIZE;
const prepCtx = prepCanvas.getContext("2d", { willReadFrequently: true });

function setStatus(message) {
  statusEl.textContent = message;
}

function waitForOpenCv() {
  if (window.cv?.Mat && window.cv?.imread) {
    cvReady = true;
    setStatus("OpenCV đã sẵn sàng. Nạp model hoặc mở camera để dùng contour fallback.");
    return;
  }

  const timer = window.setInterval(() => {
    if (window.cv?.Mat && window.cv?.imread) {
      window.clearInterval(timer);
      cvReady = true;
      setStatus("OpenCV đã sẵn sàng. Nạp model hoặc mở camera để dùng contour fallback.");
    }
  }, 100);
}

async function loadDefaultModel() {
  try {
    configureOrt();
    session = await ort.InferenceSession.create(MODEL_PATH, {
      executionProviders: ["wasm"],
      graphOptimizationLevel: "all",
    });
    setStatus("Đã nạp model /best.onnx.");
  } catch (error) {
    console.warn("Không nạp được model ONNX, dùng contour fallback.", error);
    session = null;
    setStatus("Chưa có model ONNX. Bạn có thể upload model hoặc dùng contour fallback.");
  }
}

async function loadUploadedModel(file) {
  const buffer = await file.arrayBuffer();
  configureOrt();
  session = await ort.InferenceSession.create(buffer, {
    executionProviders: ["wasm"],
    graphOptimizationLevel: "all",
  });
  setStatus(`Đã nạp model: ${file.name}`);
}

function configureOrt() {
  if (!window.ort?.env?.wasm) return;
  window.ort.env.wasm.numThreads = 1;
}

async function startCamera() {
  if (!cvReady) {
    setStatus("OpenCV chưa tải xong.");
    return;
  }

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 1920 },
        height: { ideal: 1080 },
      },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();

    frameCanvas.width = video.videoWidth;
    frameCanvas.height = video.videoHeight;
    overlay.width = video.videoWidth;
    overlay.height = video.videoHeight;
    snapBtn.disabled = false;
    running = true;
    requestAnimationFrame(loop);
  } catch (error) {
    console.error("Không mở được camera.", error);
    setStatus("Không mở được camera. Kiểm tra quyền truy cập camera rồi thử lại.");
  }
}

async function loop(now) {
  if (!running || video.readyState < 2) {
    requestAnimationFrame(loop);
    return;
  }

  frameCtx.drawImage(video, 0, 0, frameCanvas.width, frameCanvas.height);
  const detection = await detectDocument();
  drawOverlay(detection);

  if (detection && autoInput.checked) {
    const stable = isStable(detection.box, now);
    const enoughDelay = now - lastCaptureAt >= AUTO_CAPTURE_COOLDOWN;
    if (stable && enoughDelay) {
      await captureDocument(detection);
      lastCaptureAt = now;
      stableSince = 0;
    }
  } else {
    lastBox = null;
    stableSince = 0;
  }

  requestAnimationFrame(loop);
}

async function detectDocument() {
  if (session) {
    try {
      const detection = await detectWithYolo();
      if (detection) return detection;
    } catch (error) {
      console.warn("YOLO detect lỗi, chuyển sang contour fallback.", error);
      session = null;
    }
  }

  return cvReady ? detectDocumentContour() : null;
}

async function detectWithYolo() {
  prepCtx.fillStyle = "#000";
  prepCtx.fillRect(0, 0, INPUT_SIZE, INPUT_SIZE);

  const scale = Math.min(INPUT_SIZE / frameCanvas.width, INPUT_SIZE / frameCanvas.height);
  const dw = frameCanvas.width * scale;
  const dh = frameCanvas.height * scale;
  const dx = (INPUT_SIZE - dw) / 2;
  const dy = (INPUT_SIZE - dh) / 2;
  prepCtx.drawImage(frameCanvas, dx, dy, dw, dh);

  const image = prepCtx.getImageData(0, 0, INPUT_SIZE, INPUT_SIZE).data;
  const input = new Float32Array(3 * INPUT_SIZE * INPUT_SIZE);
  for (let i = 0; i < INPUT_SIZE * INPUT_SIZE; i += 1) {
    input[i] = image[i * 4] / 255;
    input[i + INPUT_SIZE * INPUT_SIZE] = image[i * 4 + 1] / 255;
    input[i + 2 * INPUT_SIZE * INPUT_SIZE] = image[i * 4 + 2] / 255;
  }

  const tensor = new ort.Tensor("float32", input, [1, 3, INPUT_SIZE, INPUT_SIZE]);
  const output = await session.run({ [session.inputNames[0]]: tensor });
  const result = output[session.outputNames[0]];
  const boxes = parseYoloOutput(result, scale, dx, dy);
  return boxes[0] ? { box: boxes[0], source: "YOLO" } : null;
}

function parseYoloOutput(result, scale, padX, padY) {
  const data = result.data;
  const dims = result.dims;
  const scoreThreshold = Number(scoreInput.value);
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
    if (score < scoreThreshold) continue;

    const x = (cx - w / 2 - padX) / scale;
    const y = (cy - h / 2 - padY) / scale;
    candidates.push({
      x: clamp(x, 0, frameCanvas.width),
      y: clamp(y, 0, frameCanvas.height),
      w: clamp(w / scale, 0, frameCanvas.width),
      h: clamp(h / scale, 0, frameCanvas.height),
      score,
    });
  }

  return nms(candidates).slice(0, 1);
}

function detectDocumentContour() {
  const src = cv.imread(frameCanvas);
  const gray = new cv.Mat();
  const blur = new cv.Mat();
  const edges = new cv.Mat();
  const binary = new cv.Mat();
  const kernel = cv.Mat.ones(7, 7, cv.CV_8U);
  const contours = new cv.MatVector();
  const hierarchy = new cv.Mat();
  let best = null;

  cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
  cv.GaussianBlur(gray, blur, new cv.Size(5, 5), 0);
  cv.Canny(blur, edges, 60, 160);
  cv.findContours(edges, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);
  best = findBestContourBox(contours, best);

  contours.delete();
  hierarchy.delete();

  const brightContours = new cv.MatVector();
  const brightHierarchy = new cv.Mat();
  cv.threshold(blur, binary, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU);
  cv.morphologyEx(binary, binary, cv.MORPH_CLOSE, kernel);
  cv.findContours(binary, brightContours, brightHierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);
  best = findBestContourBox(brightContours, best);

  src.delete();
  gray.delete();
  blur.delete();
  edges.delete();
  binary.delete();
  kernel.delete();
  brightContours.delete();
  brightHierarchy.delete();

  return best ? { box: best.box, corners: best.corners, source: "Contour" } : null;
}

function findBestContourBox(contours, currentBest) {
  let best = currentBest;
  const frameArea = frameCanvas.width * frameCanvas.height;
  const minShortSide = Math.min(frameCanvas.width, frameCanvas.height) * MIN_DOCUMENT_SHORT_SIDE_RATIO;
  const minArea = frameArea * MIN_DOCUMENT_AREA_RATIO;
  const maxArea = frameArea * MAX_DOCUMENT_AREA_RATIO;

  for (let i = 0; i < contours.size(); i += 1) {
    const contour = contours.get(i);
    const area = cv.contourArea(contour);
    if (area < minArea || area > maxArea) {
      contour.delete();
      continue;
    }

    const rect = normalizeCvRect(cv.boundingRect(contour));
    const areaRatio = area / frameArea;
    const rectArea = rect.w * rect.h;
    const fillRatio = area / rectArea;
    const aspect = rect.w / rect.h;
    const shortSide = Math.min(rect.w, rect.h);
    const plausibleAspect = aspect >= 0.45 && aspect <= 2.25;
    const plausibleFill = fillRatio >= 0.35;
    const plausibleSize = shortSide >= minShortSide;
    if (!plausibleAspect || !plausibleFill || !plausibleSize) {
      contour.delete();
      continue;
    }

    const peri = cv.arcLength(contour, true);
    const approx = new cv.Mat();
    cv.approxPolyDP(contour, approx, 0.035 * peri, true);
    const corners = approx.rows === 4 ? pointsFromMat(approx) : null;
    if (!corners && areaRatio < MIN_BOX_ONLY_AREA_RATIO) {
      approx.delete();
      contour.delete();
      continue;
    }
    const cornerWeight = corners ? 4 : 1;
    const portraitAspect = Math.min(aspect, 1 / aspect);
    const documentAspectScore = 1 - Math.min(1, Math.abs(portraitAspect - 0.707) / 0.35);
    const score = area * fillRatio * cornerWeight * (0.7 + documentAspectScore * 0.3);
    if (!best || score > best.score) best = { area, score, box: rect, corners };
    approx.delete();
    contour.delete();
  }

  return best;
}

function normalizeCvRect(rect) {
  return {
    x: rect.x,
    y: rect.y,
    w: rect.w ?? rect.width,
    h: rect.h ?? rect.height,
  };
}

async function captureDocument(detection) {
  let dataUrl = null;
  try {
    dataUrl = cropAndDeskew(detection.box, detection.corners);
  } catch (error) {
    console.warn("Crop tài liệu lỗi, lưu nguyên khung camera.", error);
  }

  if (!dataUrl) {
    await captureFrame();
    return;
  }

  captures.push(dataUrl);
  renderCaptures();
  setStatus(`Đã crop ${captures.length} ảnh tài liệu.`);
}

async function captureFrame() {
  const canvas = document.createElement("canvas");
  canvas.width = frameCanvas.width;
  canvas.height = frameCanvas.height;
  canvas.getContext("2d").drawImage(frameCanvas, 0, 0);
  captures.push(canvas.toDataURL("image/jpeg", 0.94));
  renderCaptures();
  setStatus(`Không phát hiện được tài liệu. Đã lưu nguyên khung camera (${captures.length} ảnh).`);
}

function cropAndDeskew(box, corners = null) {
  const src = cv.imread(frameCanvas);
  let roi = null;
  let output;

  if (corners?.length === 4) {
    output = warpDocument(src, corners);
  } else {
    const roiRect = expandRect(box, 0.06, src.cols, src.rows);
    roi = src.roi(roiRect);
    const points = findDocumentCorners(roi);

    if (points) {
      const shifted = points.map((p) => ({ x: p.x + roiRect.x, y: p.y + roiRect.y }));
      output = warpDocument(src, shifted);
    } else {
      output = roi.clone();
    }
  }

  const normalized = normalizeOrientation(output);
  const canvas = document.createElement("canvas");
  cv.imshow(canvas, normalized);
  const dataUrl = canvas.toDataURL("image/jpeg", 0.94);

  src.delete();
  if (roi) roi.delete();
  output.delete();
  normalized.delete();
  return dataUrl;
}

function findDocumentCorners(mat) {
  const gray = new cv.Mat();
  const blur = new cv.Mat();
  const edges = new cv.Mat();
  const contours = new cv.MatVector();
  const hierarchy = new cv.Mat();
  let best = null;
  let bestArea = 0;
  const matArea = mat.cols * mat.rows;

  cv.cvtColor(mat, gray, cv.COLOR_RGBA2GRAY);
  cv.GaussianBlur(gray, blur, new cv.Size(5, 5), 0);
  cv.Canny(blur, edges, 45, 140);
  cv.findContours(edges, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);

  for (let i = 0; i < contours.size(); i += 1) {
    const contour = contours.get(i);
    const peri = cv.arcLength(contour, true);
    const approx = new cv.Mat();
    cv.approxPolyDP(contour, approx, 0.03 * peri, true);
    const area = cv.contourArea(approx);
    const rect = normalizeCvRect(cv.boundingRect(approx));
    const rectArea = rect.w * rect.h;
    const aspect = rect.w / rect.h;
    const fillRatio = rectArea > 0 ? area / rectArea : 0;
    const plausibleSize = area >= matArea * 0.18 && area <= matArea * 0.98;
    const plausibleAspect = aspect >= 0.45 && aspect <= 2.25;
    const plausibleFill = fillRatio >= 0.35;
    if (approx.rows === 4 && plausibleSize && plausibleAspect && plausibleFill && area > bestArea) {
      bestArea = area;
      best = [];
      for (let r = 0; r < 4; r += 1) {
        best.push({ x: approx.intPtr(r, 0)[0], y: approx.intPtr(r, 0)[1] });
      }
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
  const dst = new cv.Mat();
  const srcTri = cv.matFromArray(4, 1, cv.CV_32FC2, [
    tl.x,
    tl.y,
    tr.x,
    tr.y,
    br.x,
    br.y,
    bl.x,
    bl.y,
  ]);
  const dstTri = cv.matFromArray(4, 1, cv.CV_32FC2, [
    0,
    0,
    width - 1,
    0,
    width - 1,
    height - 1,
    0,
    height - 1,
  ]);
  const matrix = cv.getPerspectiveTransform(srcTri, dstTri);
  cv.warpPerspective(src, dst, matrix, new cv.Size(width, height), cv.INTER_LINEAR, cv.BORDER_CONSTANT);
  srcTri.delete();
  dstTri.delete();
  matrix.delete();
  return dst;
}

function normalizeOrientation(mat) {
  if (mat.cols <= mat.rows) return mat.clone();
  const rotated = new cv.Mat();
  cv.rotate(mat, rotated, cv.ROTATE_90_CLOCKWISE);
  return rotated;
}

async function createPdf() {
  const { jsPDF } = window.jspdf;
  const pdf = new jsPDF({ unit: "mm", format: "a4", orientation: "portrait" });

  for (let i = 0; i < captures.length; i += 1) {
    if (i > 0) pdf.addPage();
    const img = await loadImage(captures[i]);
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const margin = 8;
    const ratio = Math.min((pageW - margin * 2) / img.width, (pageH - margin * 2) / img.height);
    const w = img.width * ratio;
    const h = img.height * ratio;
    pdf.addImage(captures[i], "JPEG", (pageW - w) / 2, (pageH - h) / 2, w, h);
  }

  pdf.save(`autocut-${new Date().toISOString().slice(0, 10)}.pdf`);
}

function renderCaptures() {
  capturesEl.innerHTML = "";
  for (const src of captures) {
    const img = new Image();
    img.src = src;
    capturesEl.append(img);
  }
  pdfBtn.disabled = captures.length === 0;
  clearBtn.disabled = captures.length === 0;
}

function drawOverlay(detection) {
  const ctx = overlay.getContext("2d");
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  if (!detection) {
    setStatus(session ? "Đưa tài liệu vào khung camera." : "Fallback contour: đưa tài liệu lên nền tương phản.");
    return;
  }

  const { x, y, score } = detection.box;
  const corners = detection.corners ? orderPoints(detection.corners) : boxToPoints(detection.box);

  ctx.save();
  ctx.lineJoin = "round";
  ctx.shadowColor = "rgba(0, 0, 0, 0.55)";
  ctx.shadowBlur = 8;
  ctx.strokeStyle = "#07110e";
  ctx.lineWidth = 9;
  drawPointPath(ctx, corners);
  ctx.stroke();
  ctx.shadowBlur = 0;
  ctx.strokeStyle = "#47d7ac";
  ctx.lineWidth = 5;
  drawPointPath(ctx, corners);
  ctx.stroke();
  ctx.fillStyle = "rgba(71, 215, 172, 0.16)";
  drawPointPath(ctx, corners);
  ctx.fill();
  drawCornerHandles(ctx, corners);
  ctx.fillStyle = "#47d7ac";
  ctx.font = "24px sans-serif";
  const label = `${detection.source}${score ? ` ${(score * 100).toFixed(0)}%` : ""}`;
  ctx.fillText(label, x + 10, Math.max(28, y - 10));
  ctx.restore();
  setStatus(`${label}. Giữ tài liệu ổn định để tự chụp.`);
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

function drawPointPath(ctx, points) {
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i += 1) ctx.lineTo(points[i].x, points[i].y);
  ctx.closePath();
}

function drawCornerHandles(ctx, points) {
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 3;
  for (const point of points) {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 8, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function isStable(box, now) {
  if (!lastBox || boxDelta(lastBox, box) > 0.035) {
    lastBox = { ...box };
    stableSince = now;
    return false;
  }
  return now - stableSince >= Number(stableInput.value);
}

function boxDelta(a, b) {
  const dw = frameCanvas.width;
  const dh = frameCanvas.height;
  return (
    Math.abs(a.x - b.x) / dw +
    Math.abs(a.y - b.y) / dh +
    Math.abs(a.w - b.w) / dw +
    Math.abs(a.h - b.h) / dh
  );
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

function expandRect(box, amount, maxW, maxH) {
  const padX = box.w * amount;
  const padY = box.h * amount;
  const x = Math.max(0, Math.floor(box.x - padX));
  const y = Math.max(0, Math.floor(box.y - padY));
  const w = Math.min(maxW - x, Math.floor(box.w + padX * 2));
  const h = Math.min(maxH - y, Math.floor(box.h + padY * 2));
  return new cv.Rect(x, y, w, h);
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

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function loadImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.src = src;
  });
}

modelInput.addEventListener("change", async (event) => {
  const [file] = event.target.files;
  if (file) await loadUploadedModel(file);
});

startBtn.addEventListener("click", startCamera);
snapBtn.addEventListener("click", async () => {
  frameCtx.drawImage(video, 0, 0, frameCanvas.width, frameCanvas.height);
  const detection = await detectDocument();
  if (detection) {
    drawOverlay(detection);
    await captureDocument(detection);
  } else {
    await captureFrame();
  }
});
pdfBtn.addEventListener("click", createPdf);
clearBtn.addEventListener("click", () => {
  captures = [];
  renderCaptures();
});

if (new URLSearchParams(window.location.search).has("test")) {
  window.__autocutTest = {
    setFrame(sourceCanvas) {
      frameCanvas.width = sourceCanvas.width;
      frameCanvas.height = sourceCanvas.height;
      overlay.width = sourceCanvas.width;
      overlay.height = sourceCanvas.height;
      frameCtx.drawImage(sourceCanvas, 0, 0);
    },
    detectDocumentContour,
    cropAndDeskew,
    getCaptures: () => [...captures],
    isOpenCvReady: () => cvReady,
  };
}

waitForOpenCv();
loadDefaultModel();
