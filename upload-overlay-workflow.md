# Upload Overlay Workflow - No Dialog Flow

> **Chrome Extension - Auto Fill Form Dịch Vụ Công**  
> **Version:** 1.0.0  
> **Last Updated:** 2026-04-10

---

## 📋 Tổng quan

Tài liệu này mô tả chi tiết luồng xử lý **khi KHÔNG có dialog** "Cập nhật thông tin cá nhân" xuất hiện - trường hợp phổ biến nhất khi điền form dịch vụ công.

---

## 🔄 Complete No-Dialog Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NO-DIALOG WORKFLOW (Simplified)                   │
│                                                                       │
│  Step 1: Page Load & Validation                                      │
│         │                                                              │
│         ▼                                                              │
│  Step 2: Fetch API Data (localhost:5431)                              │
│         │                                                              │
│         ▼                                                              │
│  Step 3: Auto-fill Main Form (6 fields)                               │
│         │                                                              │
│         ▼                                                              │
│  Step 4: Check for Dialog (800ms delay)                               │
│         │                                                              │
│         │  Result: NO DIALOG DETECTED                                  │
│         │                                                              │
│         ▼                                                              │
│  Step 5: Start 3-Second Timer                                         │
│         │                                                              │
│         ▼                                                              │
│  Step 6: Re-check for Dialog (after 3s)                               │
│         │                                                              │
│         │  Result: STILL NO DIALOG                                     │
│         │                                                              │
│         ▼                                                              │
│  Step 7: Show Upload Overlay                                          │
│         │                                                              │
│         ▼                                                              │
│  Step 8: User Clicks "Tải tài liệu lên"                               │
│         │                                                              │
│         ▼                                                              │
│  Step 9: Check/Select Folder                                          │
│         │                                                              │
│         ▼                                                              │
│  Step 10: Find Latest File                                            │
│         │                                                              │
│         ▼                                                              │
│  Step 11: Upload File to Form                                         │
│         │                                                              │
│         ▼                                                              │
│  Step 12: Show Success & Remove Overlay (2s)                          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ⏱️ Timeline (No Dialog)

```
Time (ms)    Event
─────────────────────────────────────────────────────────────
0            Page loaded & validated
0-5000       Waiting for page render (max 10 attempts × 500ms)
5000         Fetch API data from localhost:5431
5100         Auto-fill main form (6 fields)
5900         Check for dialog (800ms delay)
6000         ❌ No dialog detected → Start 3s timer
9000         ❌ Still no dialog → Show upload overlay
>9000        User interaction required (click upload button)
```

**Total time to overlay:** ~9 seconds (without user interaction)

---

## 📝 1. Page Load & Validation

### **1.1 Content Script Initialization**

```javascript
// content.js - Line 801-846

function init() {
  console.log('[AutoFill] Initializing...');
  setupDialogObserver();
  setupDialogCloseObserver();

  let attempts = 0;
  const maxAttempts = 10;
  let isFetching = false;

  function waitForPageReady() {
    if (isFetching) return; // Prevent duplicate fetches

    if (isValidPage()) {
      isFetching = true;
      console.log('[AutoFill] Page is ready, fetching API data...');
      
      if (!apiDataCache) {
        fetchDataFromAPI().then((data) => {
          if (data) {
            apiDataCache = data;
            console.log('[AutoFill] Filling form with API data...');
            fillForm(data);
          }
        });
      }
      return;
    }

    attempts++;
    if (attempts < maxAttempts) {
      console.log(`[AutoFill] Waiting for page to render... (attempt ${attempts}/${maxAttempts})`);
      setTimeout(waitForPageReady, 500);
    } else {
      console.log('[AutoFill] Page render timeout. User can click button in popup to fill.');
    }
  }

  waitForPageReady();
}
```

### **1.2 Page Validation**

```javascript
const VALID_URL_PATTERNS = [
  /https:\/\/dichvucong\.thainguyen\.gov\.vn\/nop-ho-so/,
  /file:\/\/.*form-replica\.html/,
  /file:\/\/.*\.html/,
  /http:\/\/localhost.*form/,
  /http:\/\/127\.0\.0\.1.*form/
];

function isValidPage() {
  return VALID_URL_PATTERNS.some(p => p.test(window.location.href)) &&
         document.querySelector('.form-section, .content-wrapper, .page-content, mat-form-field');
}
```

**Validation Criteria:**
- ✅ URL matches one of the valid patterns
- ✅ Page contains form elements (`.form-section`, `.content-wrapper`, `.page-content`, or `mat-form-field`)

---

## 🌐 2. API Data Fetching

### **2.1 Fetch Function**

```javascript
// content.js - Line 153-163

async function fetchDataFromAPI() {
  if (apiDataCache) return apiDataCache;
  
  const API_URL = 'http://localhost:5431';
  
  try {
    const response = await fetch(API_URL, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    
    const data = await response.json();
    apiDataCache = data;
    
    console.log('[AutoFill] API data fetched and cached');
    return data;
  } catch (error) {
    console.log('[AutoFill] API fetch failed:', error.message);
    return null;
  }
}
```

**Expected API Response:**
```json
{
  "identityNumber": "0361240112234",
  "fullName": "Nguyễn Văn A",
  "dateOfBirth": "1990-01-15",
  "placeOfResidence": "Phường Láng, Thành phố Hà Nội",
  "dateOfIssue": "2020-01-16",
  "placeOfIssue": "Cục Cảnh sát QLHC"
}
```

---

## 📝 3. Main Form Filling (No Dialog)

### **3.1 Form Field Mapping**

Extension điền **6 trường** vào main form:

| Card Field | Form Label | Type | Disabled | Format |
|------------|------------|------|----------|--------|
| `identityNumber` | CMND | text | ✅ Yes | Text |
| `fullName` | Tên người nộp | text | ✅ Yes | Text |
| `dateOfBirth` | Ngày sinh | date | ❌ No | DD/MM/YYYY |
| `placeOfResidence` | Địa chỉ | text | ❌ No | Text |
| `dateOfIssue` | Ngày cấp | date | ❌ No | DD/MM/YYYY |
| `placeOfIssue` | Nơi cấp | text | ❌ No | Text |

### **3.2 Fill Form Function**

```javascript
// content.js - Line 166-228

function fillForm(data) {
  if (!data) {
    data = apiDataCache;
  }
  if (!data) {
    console.log('[AutoFill] No data available to fill form');
    return { success: false, message: 'No data available' };
  }

  if (!isValidPage()) {
    console.log('[AutoFill] Not on valid form page.');
    return { success: false, message: 'Not on valid form page.', url: window.location.href };
  }

  const results = { success: true, filled: 0, failed: 0, skipped: 0, total: 0, details: [] };

  function addResult(field, status, msg = '') {
    results.total++;
    results.details.push({ field, status, message: msg });
    if (status === 'success') results.filled++;
    else if (status === 'failed') results.failed++;
    else results.skipped++;
  }

  // Extract fields from various response formats
  let fieldsToFill = {};
  if (data?.data?.cardObj) fieldsToFill = data.data.cardObj;
  else if (data?.cardObj) fieldsToFill = data.cardObj;
  else if (data?.identityNumber) fieldsToFill = data;
  else fieldsToFill = data || {};

  // Special handling for missing fields
  if (!fieldsToFill.placeOfBirth && fieldsToFill.placeOfOrigin) {
    fieldsToFill.placeOfBirth = fieldsToFill.placeOfOrigin;
  }
  if (!fieldsToFill.placeOfIssue) {
    fieldsToFill.placeOfIssue = 'Cục Cảnh sát quản lý hành chính về trật tự xã hội';
  }
  if (!fieldsToFill.phone) fieldsToFill.phone = '';
  if (!fieldsToFill.email) fieldsToFill.email = '';

  lastFormData = fieldsToFill;

  // Main form field mapping
  const mapping = {
    'identityNumber': { label: 'cmnd', type: 'text', isDisabled: true },
    'fullName': { label: 'tên người nộp', type: 'text', isDisabled: true },
    'dateOfBirth': { label: 'ngày sinh', type: 'date' },
    'placeOfResidence': { label: 'địa chỉ', type: 'text' },
    'dateOfIssue': { label: 'ngày cấp', type: 'date' },
    'placeOfIssue': { label: 'nơi cấp', type: 'text' },
  };

  for (const [cardField, fm] of Object.entries(mapping)) {
    const value = fieldsToFill[cardField];
    
    if (!value || value === null || value === 'null' || value === '') {
      addResult(cardField, 'skipped', 'No value');
      continue;
    }

    const element = findFieldByLabelText(fm.label);
    if (!element) {
      addResult(cardField, 'failed', 'Element not found');
      continue;
    }
    
    if (fm.isDisabled || element.disabled || element.hasAttribute('disabled')) {
      addResult(cardField, 'skipped', 'Disabled');
      continue;
    }

    if (fillField(element, value, fm.type)) {
      addResult(cardField, 'success', 'Filled');
    } else {
      addResult(cardField, 'failed', 'Fill failed');
    }
  }

  console.log('[AutoFill] Form fill completed:', results);

  // ==========================================
  // NO DIALOG PATH - Start 3s timer
  // ==========================================
  console.log('[AutoFill] No citizen dialog detected, starting 3s timer');
  
  setTimeout(() => {
    const dlg = document.querySelector('#citizenInfoModal');
    const ttl = document.querySelector('#citizenInfoModalLabel, .modal-title');
    
    if (dlg || (ttl && ttl.textContent.includes('Cập nhật thông tin cá nhân'))) {
      console.log('[AutoFill] Citizen dialog appeared after delay');
    } else if (!overlayShown) {
      console.log('[AutoFill] No citizen dialog after 3s - showing overlay');
      showUploadOverlay();
    }
  }, 3000);

  return results;
}
```

---

## 🔍 4. Dialog Check (800ms + 3s)

### **4.1 Initial Dialog Check (800ms)**

```javascript
// content.js - Line 218-227

// Kiểm tra dialog "Cập nhật thông tin cá nhân của bạn"
const citizenDialog = document.querySelector('#citizenInfoModal');
const titleEl = document.querySelector('#citizenInfoModalLabel, .modal-title');
const hasCitizenTitle = titleEl && titleEl.textContent.includes('Cập nhật thông tin cá nhân');

if (citizenDialog || hasCitizenTitle) {
  console.log('[AutoFill] 🎯 Citizen info dialog detected - filling dialog');
  setTimeout(() => {
    const dialogContainer = citizenDialog || 
                            document.querySelector('mat-dialog-container') || 
                            document.querySelector('[role="dialog"]');
    if (dialogContainer) fillDialog(dialogContainer);
  }, 800);
  return results;
}
```

### **4.2 Second Dialog Check (3s Timer)**

```javascript
// content.js - Line 229-240

// Không có dialog → đợi 3s rồi hiện overlay
console.log('[AutoFill] No citizen dialog detected, starting 3s timer');

setTimeout(() => {
  const dlg = document.querySelector('#citizenInfoModal');
  const ttl = document.querySelector('#citizenInfoModalLabel, .modal-title');
  
  if (dlg || (ttl && ttl.textContent.includes('Cập nhật thông tin cá nhân'))) {
    console.log('[AutoFill] Citizen dialog appeared after delay');
    // Dialog xuất hiện muộn → fill dialog
  } else if (!overlayShown) {
    console.log('[AutoFill] No citizen dialog after 3s - showing overlay');
    showUploadOverlay();
  }
}, 3000);
```

**Why 3-second delay?**
- ⏱️ Allow time for late-rendering dialogs
- ⏱️ Ensure form is fully loaded
- ⏱️ Prevent race conditions
- ⏱️ Give Angular time to stabilize

---

## 📤 5. Upload Overlay (No Dialog Path)

### **5.1 Overlay Trigger Conditions**

Overlay is shown when **ALL** conditions are met:
1. ✅ Main form has been filled successfully
2. ✅ No dialog detected after initial 800ms check
3. ✅ No dialog detected after 3-second timer
4. ✅ Overlay hasn't been shown before (`overlayShown === false`)

### **5.2 Overlay UI Structure**

```html
<div id="autofill-lock-overlay">
  <div id="autofill-overlay-content">
    <p>📄 Form đã điền xong!</p>
    <button id="autofill-btn-upload">📤 Tải tài liệu lên</button>
    <div id="autofill-upload-status"></div>
  </div>
</div>
```

### **5.3 Overlay Creation Function**

```javascript
// content.js - Line 350-520

function showUploadOverlay() {
  if (overlayShown) {
    console.log('[AutoFill] Overlay already shown, skipping');
    return;
  }
  overlayShown = true;

  console.log('[AutoFill] Showing upload overlay on page');

  // CSS (created only once)
  if (!document.getElementById('autofill-overlay-style')) {
    const style = document.createElement('style');
    style.id = 'autofill-overlay-style';
    style.textContent = `
      #autofill-lock-overlay {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        background: rgba(0,0,0,0.7) !important;
        z-index: 9999999 !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        pointer-events: all !important;
      }
      #autofill-overlay-content {
        background: #fff !important;
        padding: 30px !important;
        border-radius: 12px !important;
        text-align: center !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3) !important;
        max-width: 350px !important;
        min-width: 280px !important;
      }
      #autofill-overlay-content p {
        margin: 0 0 20px 0 !important;
        font-size: 16px !important;
        color: #333 !important;
        font-weight: 600 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
      }
      #autofill-btn-upload {
        background: #28a745 !important;
        color: #fff !important;
        border: none !important;
        padding: 14px 28px !important;
        border-radius: 8px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        width: 100% !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        transition: background 0.2s !important;
      }
      #autofill-btn-upload:hover { background: #218838 !important; }
      #autofill-btn-upload:disabled { 
        background: #ccc !important; 
        cursor: not-allowed !important; 
      }
      #autofill-upload-status {
        margin-top: 12px !important;
        padding: 8px !important;
        border-radius: 4px !important;
        font-size: 13px !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        display: none !important;
      }
      #autofill-upload-status.success { 
        display: block !important; 
        background: #d4edda !important; 
        color: #155724 !important; 
        border: 1px solid #c3e6cb !important; 
      }
      #autofill-upload-status.error { 
        display: block !important; 
        background: #f8d7da !important; 
        color: #721c24 !important; 
        border: 1px solid #f5c6cb !important; 
      }
      #autofill-upload-status.info { 
        display: block !important; 
        background: #d1ecf1 !important; 
        color: #0c5460 !important; 
        border: 1px solid #bee5eb !important; 
      }
      #autofill-upload-status.warning { 
        display: block !important; 
        background: #fff3cd !important; 
        color: #856404 !important; 
        border: 1px solid #ffeaa7 !important; 
      }
    `;
    document.head.appendChild(style);
  }

  // HTML
  const overlay = document.createElement('div');
  overlay.id = 'autofill-lock-overlay';
  overlay.innerHTML = `
    <div id="autofill-overlay-content">
      <p>📄 Form đã điền xong!</p>
      <button id="autofill-btn-upload">📤 Tải tài liệu lên</button>
      <div id="autofill-upload-status"></div>
    </div>
  `;
  document.body.appendChild(overlay);

  // Button click handler
  const btn = document.getElementById('autofill-btn-upload');
  let processing = false;

  btn.addEventListener('click', async (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (btn.disabled) {
      console.log('[AutoFill] Already processing, ignoring click');
      return;
    }

    processing = true;
    btn.disabled = true;
    btn.textContent = '⏳ Đang xử lý...';
    showOverlayStatus('⏳ Đang kiểm tra thư mục...', 'info');

    try {
      // === STEP 1: Check folder handle ===
      let { handle, name } = await getFolderHandleFromIDB();

      if (!handle) {
        showOverlayStatus('📂 Vui lòng chọn thư mục chứa tài liệu', 'info');
        btn.textContent = '📂 Chọn thư mục';
        btn.disabled = false;

        const pickResponse = await new Promise((resolve) => {
          chrome.runtime.sendMessage(
            { action: 'pickFolderFromContent' }, 
            (resp) => resolve(resp)
          );
        });

        if (!pickResponse || !pickResponse.success) {
          showOverlayStatus(
            pickResponse?.error === 'Cancelled' ? '⏭️ Đã hủy' : '❌ Lỗi chọn thư mục', 
            pickResponse?.error === 'Cancelled' ? 'info' : 'error'
          );
          btn.textContent = '📤 Tải tài liệu lên';
          processing = false;
          return;
        }

        const fresh = await getFolderHandleFromIDB();
        handle = fresh.handle;
        name = pickResponse.folderName;

        if (!handle) {
          showOverlayStatus('❌ Không thể đọc thư mục', 'error');
          btn.textContent = '📤 Tải tài liệu lên';
          processing = false;
          return;
        }

        btn.disabled = true;
        btn.textContent = '⏳ Đang upload...';
      }

      // === STEP 2: Find latest file ===
      showOverlayStatus('⏳ Đang tìm file...', 'info');
      let latestFile = null;
      let latestDate = new Date(0);

      for await (const entry of handle.values()) {
        if (entry.kind === 'file') {
          const file = await entry.getFile();
          const ln = entry.name.toLowerCase();
          
          if (ln.endsWith('.pdf') || 
              ln.endsWith('.jpg') || 
              ln.endsWith('.jpeg') || 
              ln.endsWith('.png')) {
            
            if (file.lastModified > latestDate.getTime()) {
              latestDate = new Date(file.lastModified);
              latestFile = { 
                handle: entry, 
                file, 
                name: entry.name, 
                size: file.size 
              };
            }
          }
        }
      }

      if (!latestFile) {
        showOverlayStatus(
          '❌ Không tìm thấy file PDF/JPG/PNG trong thư mục', 
          'error'
        );
        btn.disabled = false;
        btn.textContent = '📤 Tải tài liệu lên';
        processing = false;
        return;
      }

      console.log('[AutoFill] Found file:', latestFile.name);
      showOverlayStatus('⏳ Đang upload: ' + latestFile.name, 'info');

      // === STEP 3: Upload to form ===
      const fileData = await latestFile.file;
      const arrayBuffer = await fileData.arrayBuffer();
      const byteArray = Array.from(new Uint8Array(arrayBuffer));

      uploadFileToInput(
        latestFile.name, 
        byteArray, 
        fileData.type || 'application/octet-stream', 
        (uploadSuccess) => {
          if (uploadSuccess) {
            showOverlayStatus('✅ Upload thành công!', 'success');
            chrome.runtime.sendMessage({ 
              action: 'uploadCompleted', 
              success: true 
            });
            setTimeout(() => removeUploadOverlay(), 2000);
          } else {
            showOverlayStatus('❌ Upload thất bại', 'error');
            btn.disabled = false;
            btn.textContent = '📤 Tải tài liệu lên';
          }
          processing = false;
        }
      );

    } catch (error) {
      console.error('[AutoFill] Error:', error);
      showOverlayStatus('❌ Lỗi: ' + error.message, 'error');
      btn.disabled = false;
      btn.textContent = '📤 Tải tài liệu lên';
      processing = false;
    }
  }, { once: false });

  console.log('[AutoFill] Overlay created on page');
}
```

---

## 📁 6. Folder Handle Management

### **6.1 IndexedDB Setup**

```javascript
const DB_NAME = 'AutoFillFormDB';
const DB_VERSION = 1;
const STORE_NAME = 'folderHandles';
let idb = null;

function initIDB() {
  return new Promise((resolve, reject) => {
    if (idb) { 
      resolve(idb); 
      return; 
    }
    
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => { 
      idb = req.result; 
      resolve(idb); 
    };
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
  });
}
```

### **6.2 Get Folder Handle**

```javascript
async function getFolderHandleFromIDB() {
  try {
    const db = await initIDB();
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    
    const handle = await new Promise((res, rej) => {
      const r = store.get('folderHandle');
      r.onsuccess = () => res(r.result);
      r.onerror = () => rej(r.error);
    });
    
    const name = await new Promise((res, rej) => {
      const r = store.get('folderName');
      r.onsuccess = () => res(r.result);
      r.onerror = () => rej(r.error);
    });
    
    return { handle, name };
  } catch (e) {
    console.error('[AutoFill] IDB error:', e);
    return { handle: null, name: null };
  }
}
```

### **6.3 Pick Folder (Content Script)**

```javascript
// Handler trong chrome.runtime.onMessage
if (request.action === 'pickFolderFromContent') {
  (async () => {
    try {
      if (!('showDirectoryPicker' in window)) {
        sendResponse({ success: false, error: 'Not supported' });
        return;
      }
      
      const handle = await window.showDirectoryPicker({ mode: 'read' });
      
      // Lưu handle trực tiếp (cùng origin → giữ method)
      const db = await initIDB();
      const tx = db.transaction(STORE_NAME, 'readwrite');
      
      await new Promise((res, rej) => {
        tx.objectStore(STORE_NAME).put(handle, 'folderHandle');
        tx.objectStore(STORE_NAME).put(handle.name, 'folderName');
        tx.oncomplete = () => res();
        tx.onerror = () => rej(tx.error);
      });
      
      console.log('[AutoFill] Folder picked and saved:', handle.name);
      sendResponse({ success: true, folderName: handle.name });
      
    } catch (e) {
      if (e.name === 'AbortError') {
        sendResponse({ success: false, error: 'Cancelled' });
      } else {
        console.error('[AutoFill] Error picking folder:', e);
        sendResponse({ success: false, error: e.message });
      }
    }
  })();
  return true;
}
```

---

## 📤 7. File Upload Process

### **7.1 Find Latest File**

```javascript
showOverlayStatus('⏳ Đang tìm file...', 'info');
let latestFile = null;
let latestDate = new Date(0);

for await (const entry of handle.values()) {
  if (entry.kind === 'file') {
    const file = await entry.getFile();
    const ln = entry.name.toLowerCase();
    
    if (ln.endsWith('.pdf') || 
        ln.endsWith('.jpg') || 
        ln.endsWith('.jpeg') || 
        ln.endsWith('.png')) {
      
      if (file.lastModified > latestDate.getTime()) {
        latestDate = new Date(file.lastModified);
        latestFile = { 
          handle: entry, 
          file, 
          name: entry.name, 
          size: file.size 
        };
      }
    }
  }
}
```

**Supported File Types:**
| Extension | MIME Type | Priority |
|-----------|-----------|----------|
| `.pdf` | `application/pdf` | ✅ Yes |
| `.jpg` | `image/jpeg` | ✅ Yes |
| `.jpeg` | `image/jpeg` | ✅ Yes |
| `.png` | `image/png` | ✅ Yes |

### **7.2 Upload to Form Input**

```javascript
function uploadFileToInput(fileName, fileData, fileType, callback) {
  try {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    if (fileInputs.length === 0) {
      console.log('[AutoFill] No file input found');
      if (callback) callback(false);
      return;
    }

    const fileInput = fileInputs[0];
    const uint8Array = new Uint8Array(fileData);
    const blob = new Blob([uint8Array], { type: fileType });
    const file = new File([blob], fileName, { type: fileType });

    // Use DataTransfer to set file input
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;

    // Trigger events for Angular to detect change
    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    fileInput.dispatchEvent(new Event('input', { bubbles: true }));

    console.log('[AutoFill] ✅ File uploaded to input:', fileName);
    hasUploadedFile = true;

    chrome.runtime.sendMessage({ 
      action: 'uploadCompleted', 
      success: true, 
      fileName 
    });
    
    if (callback) callback(true);

  } catch (error) {
    console.error('[AutoFill] Upload error:', error);
    if (callback) callback(false);
  }
}
```

---

## 🎨 8. Status Messages

### **8.1 Show Status Function**

```javascript
function showOverlayStatus(message, type) {
  const el = document.getElementById('autofill-upload-status');
  if (el) { 
    el.textContent = message; 
    el.className = type; 
  }
}
```

### **8.2 Status Flow (No Dialog)**

```
1. "⏳ Đang kiểm tra thư mục..." (info)
         │
         ▼
2. "📂 Vui lòng chọn thư mục chứa tài liệu" (info) [if no folder]
         │
         ▼
3. "⏳ Đang upload..." (info)
         │
         ▼
4. "⏳ Đang tìm file..." (info)
         │
         ▼
5. "⏳ Đang upload: filename.pdf" (info)
         │
         ▼
6. "✅ Upload thành công!" (success) → Auto-remove after 2s
   OR
   "❌ Upload thất bại" (error) → Allow retry
```

---

## 🧹 9. Overlay Cleanup

### **9.1 Remove Overlay**

```javascript
function removeUploadOverlay() {
  const overlay = document.getElementById('autofill-lock-overlay');
  if (overlay) overlay.remove();
  
  const style = document.getElementById('autofill-overlay-style');
  if (style) style.remove();
  
  overlayShown = false;
  console.log('[AutoFill] Overlay removed');
}
```

### **9.2 Cleanup Triggers**

| Trigger | Action |
|---------|--------|
| Upload success | Auto-remove after 2s |
| Page reload | Overlay lost (must re-trigger) |
| Manual removal | User closes browser tab |
| Error | Keep overlay visible, allow retry |

---

## 📊 10. Performance Metrics (No Dialog)

| Step | Duration | Notes |
|------|----------|-------|
| Page validation | 0-5s | Max 10 attempts × 500ms |
| API fetch | ~100ms | Depends on API response time |
| Form fill | ~200ms | 6 fields |
| Dialog check 1 | 800ms | Fixed delay |
| Dialog check 2 | 3000ms | Fixed delay |
| **Total to overlay** | **~4.1-9.1s** | Without user interaction |
| Folder pick | User-dependent | First time only |
| File search | ~100ms | Depends on folder size |
| File upload | ~50ms | DataTransfer + events |
| Success display | 2000ms | Auto-remove delay |

---

## 🔄 11. State Machine (No Dialog)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NO-DIALOG STATE MACHINE                          │
│                                                                       │
│  [START]                                                              │
│      │                                                                 │
│      ▼                                                                 │
│  ┌──────────────────────┐                                            │
│  │ Page Loaded          │                                            │
│  └────────┬─────────────┘                                            │
│           │                                                            │
│           ▼                                                            │
│  ┌──────────────────────┐                                            │
│  │ Validate Page        │ ◄─── Check URL & form elements              │
│  └────────┬─────────────┘                                            │
│           │                                                            │
│           ▼                                                            │
│  ┌──────────────────────┐                                            │
│  │ Fetch API Data       │ ◄─── localhost:5431                        │
│  └────────┬─────────────┘                                            │
│           │                                                            │
│           ▼                                                            │
│  ┌──────────────────────┐                                            │
│  │ Fill Main Form       │ ◄─── 6 fields                              │
│  └────────┬─────────────┘                                            │
│           │                                                            │
│           ▼                                                            │
│  ┌──────────────────────┐                                            │
│  │ Check Dialog (800ms) │ ◄─── No dialog found                        │
│  └────────┬─────────────┘                                            │
│           │                                                            │
│           ▼                                                            │
│  ┌──────────────────────┐                                            │
│  │ Start 3s Timer       │                                            │
│  └────────┬─────────────┘                                            │
│           │                                                            │
│           ▼                                                            │
│  ┌──────────────────────┐                                            │
│  │ Re-check Dialog      │ ◄─── Still no dialog                        │
│  └────────┬─────────────┘                                            │
│           │                                                            │
│           ▼                                                            │
│  ┌──────────────────────┐                                            │
│  │ Show Upload Overlay  │                                            │
│  └────────┬─────────────┘                                            │
│           │                                                            │
│           ▼                                                            │
│  ┌──────────────────────┐                                            │
│  │ Wait for User Click  │                                            │
│  └────────┬─────────────┘                                            │
│           │                                                            │
│           ▼                                                            │
│  ┌──────────────────────┐                                            │
│  │ Check Folder Handle  │                                            │
│  └────────┬─────────────┘                                            │
│           │                                                            │
│      ┌────┴────┐                                                      │
│      │         │                                                      │
│      ▼         ▼                                                      │
│  ┌───────┐ ┌──────────┐                                              │
│  │ No    │ │ Yes      │                                              │
│  └───┬───┘ └────┬─────┘                                              │
│      │          │                                                      │
│      ▼          │                                                      │
│  ┌───────┐      │                                                      │
│  │ Pick  │      │                                                      │
│  │ Folder│      │                                                      │
│  └───┬───┘      │                                                      │
│      │          │                                                      │
│      └────┬─────┘                                                      │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────────┐                                              │
│  │ Find Latest File     │                                              │
│  └────────┬─────────────┘                                              │
│           │                                                            │
│           ▼                                                            │
│  ┌──────────────────────┐                                              │
│  │ Upload File          │                                              │
│  └────────┬─────────────┘                                              │
│           │                                                            │
│           ▼                                                            │
│  ┌──────────────────────┐                                              │
│  │ Show Success (2s)    │                                              │
│  └────────┬─────────────┘                                              │
│           │                                                            │
│           ▼                                                            │
│  ┌──────────────────────┐                                              │
│  │ Remove Overlay       │                                              │
│  └──────────────────────┘                                              │
│                                                                         │
│  [END]                                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🐛 12. Troubleshooting (No Dialog)

### **12.1 Form Not Auto-Filling**

**Symptoms:**
- Page loads but fields remain empty
- Console shows "Page render timeout"

**Solutions:**
1. ✅ Check if page URL matches valid patterns
2. ✅ Check if page contains `mat-form-field` elements
3. ✅ Check if API at `localhost:5431` is running
4. ✅ Check console for fetch errors
5. ✅ Try manual fill from popup

---

### **12.2 Overlay Not Showing**

**Symptoms:**
- Form fills but no overlay appears
- Console shows "No citizen dialog after 3s" but no overlay

**Solutions:**
1. ✅ Check `overlayShown` flag (should be `false`)
2. ✅ Check if overlay CSS already exists (prevents duplicate)
3. ✅ Check browser console for errors
4. ✅ Check if `showUploadOverlay()` is being called

---

### **12.3 Folder Pick Fails**

**Symptoms:**
- "Not supported" error
- User cancels folder picker

**Solutions:**
1. ✅ Ensure browser supports `showDirectoryPicker()` API
2. ✅ User must grant folder access permission
3. ✅ If cancelled, user can retry by clicking button again

---

### **12.4 File Upload Fails**

**Symptoms:**
- "Không tìm thấy file PDF/JPG/PNG"
- Upload error in console

**Solutions:**
1. ✅ Ensure folder contains supported file types
2. ✅ Check file extensions (`.pdf`, `.jpg`, `.jpeg`, `.png`)
3. ✅ Check if form has `<input type="file">`
4. ✅ Check if `DataTransfer` API is supported

---

## 📊 13. Console Logs (No Dialog Flow)

Expected console output:

```
[AutoFill] Content script loaded
[AutoFill] URL: https://dichvucong.thainguyen.gov.vn/nop-ho-so/...
[AutoFill] Initializing...
[AutoFill] Page is ready, fetching API data...
[AutoFill] API data fetched and cached
[AutoFill] Filling form with API data...
[AutoFill] Form fill completed: {success: true, filled: 4, failed: 0, skipped: 2, total: 6}
[AutoFill] No citizen dialog detected, starting 3s timer
[AutoFill] No citizen dialog after 3s - showing overlay
[AutoFill] Showing upload overlay on page
[AutoFill] Overlay created on page
[AutoFill] Found file: document.pdf
[AutoFill] ✅ File uploaded to input: document.pdf
[AutoFill] Overlay removed
```

---

## 🔒 14. Security Considerations

### **14.1 IndexedDB Access**
- ✅ Only content script from same origin can access
- ✅ Handle not serialized through message passing
- ✅ User must explicitly grant folder access each time

### **14.2 File Upload**
- ✅ Only reads files from user-selected folder
- ✅ Does not send files externally
- ✅ File uploaded directly to form input

### **14.3 Overlay Security**
- ✅ Very high z-index (9999999) to stay on top
- ✅ `pointer-events: all` to block page interaction
- ✅ Single button click handler to prevent duplicate processing

---

## 📝 15. Code References

| File | Function | Line Range |
|------|----------|------------|
| `content.js` | `init()` | 801-846 |
| `content.js` | `isValidPage()` | 67-70 |
| `content.js` | `fetchDataFromAPI()` | 153-163 |
| `content.js` | `fillForm()` | 166-240 |
| `content.js` | `findFieldByLabelText()` | 76-102 |
| `content.js` | `fillField()` | 104-151 |
| `content.js` | `showUploadOverlay()` | 350-520 |
| `content.js` | `uploadFileToInput()` | 522-567 |
| `content.js` | `removeUploadOverlay()` | 524-530 |
| `content.js` | `showOverlayStatus()` | 532-536 |
| `content.js` | `getFolderHandleFromIDB()` | 33-58 |
| `content.js` | `initIDB()` | 25-32 |

---

## ✅ 16. Summary

### **No-Dialog Flow Characteristics**

| Feature | Description |
|---------|-------------|
| **Trigger** | Form fill complete + no dialog detected |
| **Delay** | 3.8 seconds (800ms + 3000ms) |
| **User Action** | Required (click upload button) |
| **Folder** | Persistent via IndexedDB |
| **File Selection** | Auto (latest by modification date) |
| **Upload** | Automatic via DataTransfer |
| **Cleanup** | Auto-remove after 2s on success |

### **Key Advantages**
- ✅ Fully automatic form filling
- ✅ One-click file upload
- ✅ Folder persistence across sessions
- ✅ No manual data entry required
- ✅ Smart file selection (latest file)

### **Limitations**
- ⚠️ Requires API running at `localhost:5431`
- ⚠️ First-time folder selection required
- ⚠️ Only supports specific file types
- ⚠️ Requires Chrome 86+ for `showDirectoryPicker()`

---

*Generated: 10/04/2026*  
*Version: 1.0*  
*Author: Auto-fill System Documentation*
