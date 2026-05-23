import { expect, test } from "@playwright/test";

async function waitForTestApi(page) {
  await page.goto("/?test=1");
  await page.waitForFunction(() => window.__autocutTest?.isOpenCvReady(), null, {
    timeout: 60_000,
  });
}

async function detectSyntheticA3(page, options = {}) {
  const {
    width = 1280,
    height = 720,
    margin = 8,
    docWidth = width - margin * 2,
    docHeight = height - margin * 2,
    rotateDegrees = 0,
    addDistractors = false,
  } = options;

  return page.evaluate(
    ({ width, height, docWidth, docHeight, rotateDegrees, addDistractors }) => {
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");

      ctx.fillStyle = "#11161b";
      ctx.fillRect(0, 0, width, height);

      if (addDistractors) {
        ctx.fillStyle = "#f2f0e8";
        ctx.fillRect(42, 40, 190, 54);
        ctx.fillRect(width - 260, height - 120, 210, 62);
      }

      ctx.save();
      ctx.translate(width / 2, height / 2);
      ctx.rotate((rotateDegrees * Math.PI) / 180);

      ctx.fillStyle = "#f7f5ee";
      ctx.strokeStyle = "#d2cbbb";
      ctx.lineWidth = 3;
      ctx.fillRect(-docWidth / 2, -docHeight / 2, docWidth, docHeight);
      ctx.strokeRect(-docWidth / 2, -docHeight / 2, docWidth, docHeight);

      ctx.strokeStyle = "#343434";
      ctx.lineWidth = 2;
      for (let i = 0; i < 9; i += 1) {
        const y = -docHeight / 2 + 40 + i * Math.max(22, docHeight / 12);
        ctx.beginPath();
        ctx.moveTo(-docWidth / 2 + 36, y);
        ctx.lineTo(docWidth / 2 - 42, y);
        ctx.stroke();
      }
      ctx.restore();

      window.__autocutTest.setFrame(canvas);
      const detection = window.__autocutTest.detectDocumentContour();
      return detection
        ? {
            source: detection.source,
            box: detection.box,
            corners: detection.corners,
          }
        : null;
    },
    { width, height, docWidth, docHeight, rotateDegrees, addDistractors },
  );
}

async function cropSyntheticDocument(page, options = {}) {
  const detection = await detectSyntheticA3(page, options);
  const dimensions = await page.evaluate(async (detection) => {
    const dataUrl = window.__autocutTest.cropAndDeskew(detection.box, detection.corners);
    const img = new Image();
    await new Promise((resolve, reject) => {
      img.onload = resolve;
      img.onerror = reject;
      img.src = dataUrl;
    });
    return { width: img.naturalWidth, height: img.naturalHeight };
  }, detection);

  return { detection, dimensions };
}

test("detects an A3 document that nearly fills the camera frame", async ({ page }) => {
  await waitForTestApi(page);

  const detection = await detectSyntheticA3(page, { margin: 8 });

  expect(detection).toBeTruthy();
  expect(detection.source).toBe("Contour");
  expect(detection.box.w * detection.box.h).toBeGreaterThan(1280 * 720 * 0.92);
});

test("keeps detecting a near-frame A3 document with mild skew", async ({ page }) => {
  await waitForTestApi(page);

  const detection = await detectSyntheticA3(page, { margin: 24, rotateDegrees: -1.5 });

  expect(detection).toBeTruthy();
  expect(detection.box.w).toBeGreaterThan(1150);
  expect(detection.box.h).toBeGreaterThan(650);
});

test("detects a smaller document without locking onto inner marks", async ({ page }) => {
  await waitForTestApi(page);

  const detection = await detectSyntheticA3(page, {
    docWidth: 360,
    docHeight: 510,
    rotateDegrees: 2,
    addDistractors: true,
  });

  expect(detection).toBeTruthy();
  expect(detection.corners).toHaveLength(4);
  expect(detection.box.w).toBeGreaterThan(330);
  expect(detection.box.w).toBeLessThan(420);
  expect(detection.box.h).toBeGreaterThan(480);
  expect(detection.box.h).toBeLessThan(560);
});

test("crops from the same contour corners shown on overlay", async ({ page }) => {
  await waitForTestApi(page);

  const { dimensions } = await cropSyntheticDocument(page, {
    docWidth: 360,
    docHeight: 510,
    rotateDegrees: 2,
    addDistractors: true,
  });

  expect(dimensions.width).toBeGreaterThan(330);
  expect(dimensions.width).toBeLessThan(390);
  expect(dimensions.height).toBeGreaterThan(480);
  expect(dimensions.height).toBeLessThan(540);
});

test("crops a smaller rotated document without swapping corners", async ({ page }) => {
  await waitForTestApi(page);

  const { detection, dimensions } = await cropSyntheticDocument(page, {
    docWidth: 360,
    docHeight: 510,
    rotateDegrees: 12,
    addDistractors: true,
  });

  expect(detection).toBeTruthy();
  expect(detection.corners).toHaveLength(4);
  expect(dimensions.width).toBeGreaterThan(330);
  expect(dimensions.width).toBeLessThan(395);
  expect(dimensions.height).toBeGreaterThan(480);
  expect(dimensions.height).toBeLessThan(545);
});

test("crops a very small document when it is still large enough to scan", async ({ page }) => {
  await waitForTestApi(page);

  const { detection, dimensions } = await cropSyntheticDocument(page, {
    docWidth: 160,
    docHeight: 226,
    rotateDegrees: 18,
    addDistractors: true,
  });

  expect(detection).toBeTruthy();
  expect(detection.corners).toHaveLength(4);
  expect(dimensions.width).toBeGreaterThan(130);
  expect(dimensions.width).toBeLessThan(195);
  expect(dimensions.height).toBeGreaterThan(190);
  expect(dimensions.height).toBeLessThan(265);
});

test("ignores tiny bright rectangles that are too small to be documents", async ({ page }) => {
  await waitForTestApi(page);

  const detection = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 1280;
    canvas.height = 720;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#11161b";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#f7f5ee";
    ctx.fillRect(540, 300, 72, 42);
    ctx.fillRect(700, 360, 90, 38);
    window.__autocutTest.setFrame(canvas);
    return window.__autocutTest.detectDocumentContour();
  });

  expect(detection).toBeNull();
});
