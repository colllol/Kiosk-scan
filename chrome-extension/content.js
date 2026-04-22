// Content script - Auto Fill + Dialog Detection + Overlay Upload
(function() {
  'use strict';

  console.log('[AutoFill] Content script loaded');
  console.log('[AutoFill] URL:', window.location.href);

  const VALID_URL_PATTERNS = [
    /https:\/\/dichvucong\.thainguyen\.gov\.vn\/nop-ho-so/,
    /file:\/\/.*form-replica\.html/,
    /file:\/\/.*\.html/,
    /http:\/\/localhost.*form/,
    /http:\/\/127\.0\.0\.1.*form/
  ];

  // State
  let hasUploadedFile = false;
  let lastFormData = null;
  let apiDataCache = null;
  let overlayShown = false; // Prevent duplicate overlay

  // Tối ưu: Cache folder và latest PDF
  let folderCache = { handle: null, name: null, lastScan: 0, latestPdf: null };
  const CACHE_TTL = 30000; // 30 giây cache

  // IndexedDB for folder handle (accessed directly from content script)
  const DB_NAME = 'AutoFillFormDB';
  const DB_VERSION = 1;
  const STORE_NAME = 'folderHandles';
  let idb = null;

  function initIDB() {
    return new Promise((resolve, reject) => {
      if (idb) { resolve(idb); return; }
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onerror = () => reject(req.error);
      req.onsuccess = () => { idb = req.result; resolve(idb); };
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) db.createObjectStore(STORE_NAME);
      };
    });
  }

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

  // ==========================================
  // VALID PAGE CHECK
  // ==========================================

  function isValidPage() {
    return VALID_URL_PATTERNS.some(p => p.test(window.location.href)) &&
           document.querySelector('.form-section, .content-wrapper, .page-content, mat-form-field');
  }

  // ==========================================
  // FIELD FINDING & FILLING
  // ==========================================

  function findFieldByLabelText(labelText, container = document) {
    const allLabels = container.querySelectorAll('mat-label');
    const searchText = labelText.toLowerCase().trim();

    for (const matLabel of allLabels) {
      const labelContent = matLabel.textContent.trim().toLowerCase();
      if (labelContent.includes(searchText)) {
        const matFormField = matLabel.closest('mat-form-field');
        if (matFormField) {
          const input = matFormField.querySelector('input.mat-mdc-input-element, input.mat-input-element, input[matinput]');
          if (input) return input;
          const matSelect = matFormField.querySelector('mat-select');
          if (matSelect) return matSelect;
          const textarea = matFormField.querySelector('textarea');
          if (textarea) return textarea;
          const textInput = matFormField.querySelector('input[type="text"], input[type="email"], input:not([type])');
          if (textInput) return textInput;
        }
      }
    }
    return null;
  }

  function fillField(element, value, type = 'text') {
    if (!element || element.disabled || element.hasAttribute('disabled')) return false;

    try {
      if (type === 'select' && (element.tagName === 'MAT-SELECT' || element.classList.contains('mat-select'))) {
        const matFormField = element.closest('mat-form-field');
        if (matFormField) {
          const selectEl = matFormField.querySelector('mat-select');
          if (selectEl) {
            selectEl.click();
            setTimeout(() => {
              const options = Array.from(document.querySelectorAll('mat-option'));
              const matched = options.find(opt =>
                opt.value === value || opt.value === String(value) ||
                opt.textContent.trim().toLowerCase().includes(value.toLowerCase()) ||
                opt.textContent.trim() === value
              );
              if (matched) matched.click();
            }, 200);
            return true;
          }
        }
        element.value = value;
      } else if (type === 'date') {
        let formatted = value;
        if (!/^\d{2}\/\d{2}\/\d{4}$/.test(value)) {
          const date = new Date(value);
          if (!isNaN(date.getTime())) {
            formatted = `${String(date.getDate()).padStart(2,'0')}/${String(date.getMonth()+1).padStart(2,'0')}/${date.getFullYear()}`;
          }
        }
        element.value = formatted;
      } else {
        element.value = value;
      }

      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
      element.dispatchEvent(new Event('blur', { bubbles: true }));
      element.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true }));
      element.focus();
      setTimeout(() => element.blur(), 100);
      return true;
    } catch (e) {
      console.error('[AutoFill] Error filling field:', e);
      return false;
    }
  }

  // Auto-fetch data from API
  async function fetchDataFromAPI() {
    if (apiDataCache) return apiDataCache;
    const API_URL = 'http://localhost:5431';
    try {
      const response = await fetch(API_URL, { method: 'GET', headers: { 'Accept': 'application/json' } });
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

  // Main form filling (SYNCHRONOUS - required for chrome.runtime.onMessage)
  function fillForm(data) {
    // If no data provided, use cached data
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

    // Extract fields
    let fieldsToFill = {};
    if (data?.data?.cardObj) fieldsToFill = data.data.cardObj;
    else if (data?.cardObj) fieldsToFill = data.cardObj;
    else if (data?.identityNumber) fieldsToFill = data;
    else fieldsToFill = data || {};

    // Special handling
    if (!fieldsToFill.placeOfBirth && fieldsToFill.placeOfOrigin) fieldsToFill.placeOfBirth = fieldsToFill.placeOfOrigin;
    if (!fieldsToFill.placeOfIssue) fieldsToFill.placeOfIssue = 'Cục Cảnh sát quản lý hành chính về trật tự xã hội';
    if (!fieldsToFill.phone) fieldsToFill.phone = '';
    if (!fieldsToFill.email) fieldsToFill.email = '';

    lastFormData = fieldsToFill;

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
      if (!value || value === null || value === 'null' || value === '') { addResult(cardField, 'skipped', 'No value'); continue; }

      const element = findFieldByLabelText(fm.label);
      if (!element) { addResult(cardField, 'failed', 'Element not found'); continue; }
      if (fm.isDisabled || element.disabled || element.hasAttribute('disabled')) { addResult(cardField, 'skipped', 'Disabled'); continue; }

      if (fillField(element, value, fm.type)) addResult(cardField, 'success', 'Filled');
      else addResult(cardField, 'failed', 'Fill failed');
    }

    console.log('[AutoFill] Form fill completed:', results);

    // Kiểm tra dialog "Cập nhật thông tin cá nhân của bạn"
    const citizenDialog = document.querySelector('#citizenInfoModal');
    const titleEl = document.querySelector('#citizenInfoModalLabel, .modal-title');
    const hasCitizenTitle = titleEl && titleEl.textContent.includes('Cập nhật thông tin cá nhân');

    if (citizenDialog || hasCitizenTitle) {
      console.log('[AutoFill] 🎯 Citizen info dialog detected - filling dialog');
      setTimeout(() => {
        const dialogContainer = citizenDialog || document.querySelector('mat-dialog-container') || document.querySelector('[role="dialog"]');
        if (dialogContainer) fillDialog(dialogContainer);
      }, 800);
      return results;
    }

    // Không có dialog → Workflow mới: Thêm thành phần → Điền nội dung → Upload overlay
    console.log('[AutoFill] No citizen dialog detected, starting new component workflow...');
    setTimeout(async () => {
      const dlg = document.querySelector('#citizenInfoModal');
      const ttl = document.querySelector('#citizenInfoModalLabel, .modal-title');
      if (dlg || (ttl && ttl.textContent.includes('Cập nhật thông tin cá nhân'))) {
        console.log('[AutoFill] Citizen dialog appeared after delay');
      } else if (!overlayShown) {
        console.log('[AutoFill] No citizen dialog after 3s - starting component workflow');
        await addAndFillComponent();
      }
    }, 3000);

    return results;
  }

  // ==========================================
  // ADD COMPONENT WORKFLOW
  // ==========================================

  const COMPONENT_TEXT = 'Chứng thực bản sao từ bản chính giấy tờ, văn bản do cơ quan, tổ chức có thẩm quyền của Việt Nam; cơ quan, tổ chức có thẩm quyền của nước ngoài; cơ quan, tổ chức có thẩm quyền của Việt Nam liên kết với cơ quan, tổ chức có thẩm quyền của nước ngoài cấp hoặc chứng nhận';

  async function addAndFillComponent() {
    try {
      // Step 1: Find and click "Thêm 1 thành phần" button
      console.log('[AutoFill] Step 1: Looking for "Thêm 1 thành phần" button...');
      const addButton = Array.from(document.querySelectorAll('button')).find(btn =>
        btn.textContent.trim().includes('Thêm 1 thành phần')
      );

      if (!addButton) {
        console.warn('[AutoFill] ⚠️ "Thêm 1 thành phần" button not found, showing overlay directly');
        showUploadOverlay();
        return;
      }

      console.log('[AutoFill] Found "Thêm 1 thành phần" button, clicking...');
      addButton.click();

      // Wait longer for Angular to render the new row
      console.log('[AutoFill] Waiting for new row to render...');
      await sleep(1500);

      // Step 2: Fill the content
      console.log('[AutoFill] Step 2: Finding target input in new row...');

      // Try multiple selectors for the table row
      let lastRow = document.querySelector('table tbody tr:last-child') ||
                    document.querySelector('mat-table tr:last-child') ||
                    document.querySelector('.mat-mdc-table tbody tr:last-child') ||
                    document.querySelector('.mat-table tbody tr:last-child');

      if (!lastRow) {
        console.warn('[AutoFill] ⚠️ No table row found. Dumping table structure for debug:');
        console.log(document.querySelector('table')?.innerHTML?.substring(0, 500));
        showUploadOverlay();
        return;
      }

      console.log('[AutoFill] Found last row. Searching for input...');
      
      // Strategy A: Look for input in 2nd column (Thành phần hồ sơ)
      let targetInput = lastRow.querySelector('td:nth-child(2) input.mat-mdc-input-element, td:nth-child(2) input.mat-input-element, td:nth-child(2) input');
      
      // Strategy B: Look for ANY mat-form-field input in the last row
      if (!targetInput) {
        const formFields = lastRow.querySelectorAll('mat-form-field, .mat-mdc-form-field');
        if (formFields.length > 0) {
          // Usually the first form-field is the name, or we can look for the one without a label matching "số trang" etc.
          // Let's try the first one that has an input
          for (const field of formFields) {
            const input = field.querySelector('input');
            if (input && input.type !== 'hidden') {
              targetInput = input;
              break;
            }
          }
        }
      }

      // Strategy C: Fallback to any input in the row
      if (!targetInput) {
        const allInputs = lastRow.querySelectorAll('input');
        for (const input of allInputs) {
          if (input.type !== 'hidden' && input.type !== 'checkbox') {
            targetInput = input;
            break;
          }
        }
      }

      if (!targetInput) {
        console.warn('[AutoFill] ⚠️ Target input not found in last row. Row HTML:');
        console.log(lastRow.innerHTML.substring(0, 500));
        showUploadOverlay();
        return;
      }

      console.log('[AutoFill] ✅ Found target input:', targetInput);
      fillField(targetInput, COMPONENT_TEXT, 'text');

      // Step 3: Wait 1.5s then show upload overlay
      console.log('[AutoFill] Step 3: Waiting 1.5s before showing upload overlay...');
      await sleep(1500);

      console.log('[AutoFill] Showing upload overlay...');
      showUploadOverlay();

    } catch (error) {
      console.error('[AutoFill] ❌ Error in addAndFillComponent:', error);
      showUploadOverlay();
    }
  }

  function waitForElement(selector, timeout = 5000) {
    return new Promise((resolve) => {
      const startTime = Date.now();
      const check = () => {
        if (document.querySelector(selector)) {
          resolve(true);
        } else if (Date.now() - startTime > timeout) {
          resolve(false);
        } else {
          setTimeout(check, 100);
        }
      };
      check();
    });
  }

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ==========================================
  // DIALOG FILLING
  // ==========================================

  function fillDialog(dialogContainer = document) {
    if (!dialogContainer || dialogContainer === document) {
      dialogContainer = document.querySelector('mat-dialog-container, .mat-mdc-dialog-container') ||
                        document.querySelector('[role="dialog"]');
    }
    if (!dialogContainer || !lastFormData) return { success: false, message: 'No dialog or data' };

    const results = { success: true, filled: 0, failed: 0, skipped: 0, total: 0, details: [] };

    function addResult(field, status, msg = '') {
      results.total++;
      results.details.push({ field, status, message: msg });
      if (status === 'success') results.filled++;
      else if (status === 'failed') results.failed++;
      else results.skipped++;
    }

    const dialogMapping = [
      { cardField: 'fullName', dialogField: 'full_name', type: 'text', disabled: true, label: 'Họ tên' },
      { cardField: 'dateOfBirth', dialogField: 'birth_of_day', type: 'date', label: 'Ngày sinh' },
      { cardField: 'previousNumber', dialogField: 'cmt', type: 'text', label: 'Số CMT cũ' },
      { cardField: 'identityNumber', dialogField: 'applicant_id_card', type: 'text', disabled: true, label: 'Số định danh' },
      { cardField: 'dateOfIssue', dialogField: 'applicant_id_card_date', type: 'date', label: 'Ngày cấp' },
      { cardField: 'placeOfIssue', dialogField: 'applicant_id_card_places', type: 'text', label: 'Nơi cấp' },
      { cardField: 'phone', dialogField: 'phone_number', type: 'text', label: 'Số điện thoại' },
      { cardField: 'sex', dialogField: 'gender', type: 'select', label: 'Giới tính' },
      { cardField: 'email', dialogField: 'email', type: 'text', label: 'Email' },
      { cardField: 'placeOfBirth', dialogField: 'place_of_birth', type: 'text', label: 'Nơi sinh' },
      { cardField: 'placeOfResidence', dialogField: 'address', type: 'text', label: 'Địa chỉ' },
      { cardField: 'administrativeUnit', dialogField: 'citizen_info_commune_id', type: 'select', label: 'Đơn vị hành chính' },
    ];

    for (const m of dialogMapping) {
      const value = lastFormData[m.cardField];
      if (!value || value === null || value === 'null' || value === '') { addResult(m.dialogField, 'skipped', 'No value'); continue; }

      let element = dialogContainer.querySelector(`input[name="${m.dialogField}"], mat-select[name="${m.dialogField}"]`);
      if (!element) {
        for (const field of dialogContainer.querySelectorAll('mat-form-field')) {
          const label = field.querySelector('mat-label');
          if (label && label.textContent.trim().toLowerCase().includes(m.label.toLowerCase())) {
            element = field.querySelector('input, mat-select, textarea');
            if (element) break;
          }
        }
      }

      if (!element) { addResult(m.dialogField, 'failed', 'Not found'); continue; }
      if (m.disabled || element.disabled || element.hasAttribute('disabled')) { addResult(m.dialogField, 'skipped', 'Disabled'); continue; }

      if (m.type === 'select' && (element.tagName === 'MAT-SELECT' || element.classList.contains('mat-select'))) {
        handleMatSelect(element, value, m.dialogField);
        addResult(m.dialogField, 'success', `Selecting: ${value}`);
      } else if (fillField(element, value, m.type)) {
        addResult(m.dialogField, 'success', `Filled: ${value}`);
      } else {
        addResult(m.dialogField, 'failed', 'Fill failed');
      }
    }

    console.log('[AutoFill] Dialog fill completed:', results);
    return results;
  }

  function handleMatSelect(selectElement, value) {
    selectElement.click();
    setTimeout(() => {
      const options = Array.from(document.querySelectorAll('mat-option'));
      const normalized = value.toString().toLowerCase().trim();
      const matched = options.find(opt => {
        const ov = opt.value?.toString().toLowerCase().trim();
        const ot = opt.textContent.trim().toLowerCase();
        return ov === normalized || ov?.includes(normalized) || ot === normalized || ot?.includes(normalized);
      });
      if (matched) {
        matched.click();
        selectElement.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }, 300);
  }

  // ==========================================
  // OVERLAY ON PAGE
  // ==========================================

  function showUploadOverlay() {
    if (overlayShown) {
      console.log('[AutoFill] Overlay already shown, skipping');
      return;
    }
    overlayShown = true;

    console.log('[AutoFill] Showing upload overlay on page');

    // CSS (chỉ tạo 1 lần)
    if (!document.getElementById('autofill-overlay-style')) {
      const style = document.createElement('style');
      style.id = 'autofill-overlay-style';
      style.textContent = `
        #autofill-lock-overlay {
          position: fixed !important; top: 0 !important; left: 0 !important;
          width: 100vw !important; height: 100vh !important;
          background: rgba(0,0,0,0.7) !important; z-index: 9999999 !important;
          display: flex !important; justify-content: center !important; align-items: center !important;
          pointer-events: all !important;
        }
        #autofill-overlay-content {
          background: #fff !important; padding: 30px !important; border-radius: 12px !important;
          text-align: center !important; box-shadow: 0 8px 32px rgba(0,0,0,0.3) !important;
          max-width: 350px !important; min-width: 280px !important;
        }
        #autofill-overlay-content p {
          margin: 0 0 20px 0 !important; font-size: 16px !important; color: #333 !important;
          font-weight: 600 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        }
        #autofill-btn-upload {
          background: #28a745 !important; color: #fff !important; border: none !important;
          padding: 14px 28px !important; border-radius: 8px !important; font-size: 16px !important;
          font-weight: 600 !important; cursor: pointer !important; width: 100% !important;
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important; transition: background 0.2s !important;
        }
        #autofill-btn-upload:hover { background: #218838 !important; }
        #autofill-btn-upload:disabled { background: #ccc !important; cursor: not-allowed !important; }
        #autofill-upload-status {
          margin-top: 12px !important; padding: 8px !important; border-radius: 4px !important;
          font-size: 13px !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
          display: none !important;
        }
        #autofill-upload-status.success { display:block!important; background:#d4edda!important; color:#155724!important; border:1px solid #c3e6cb!important; }
        #autofill-upload-status.error { display:block!important; background:#f8d7da!important; color:#721c24!important; border:1px solid #f5c6cb!important; }
        #autofill-upload-status.info { display:block!important; background:#d1ecf1!important; color:#0c5460!important; border:1px solid #bee5eb!important; }
        #autofill-upload-status.warning { display:block!important; background:#fff3cd!important; color:#856404!important; border:1px solid #ffeaa7!important; }
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

    // Button click handler - dùng biến cục bộ để tránh duplicate
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
        // === BƯỚC 1: Kiểm tra thư mục ===
        let { handle, name } = await getFolderHandleFromIDB();

        if (!handle) {
          showOverlayStatus('📂 Vui lòng chọn thư mục chứa tài liệu', 'info');
          btn.textContent = '📂 Chọn thư mục';
          btn.disabled = false;

          const pickResponse = await new Promise((resolve) => {
            chrome.runtime.sendMessage({ action: 'pickFolderFromContent' }, (resp) => resolve(resp));
          });

          if (!pickResponse || !pickResponse.success) {
            showOverlayStatus(pickResponse?.error === 'Cancelled' ? '⏭️ Đã hủy' : '❌ Lỗi chọn thư mục', pickResponse?.error === 'Cancelled' ? 'info' : 'error');
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

          // Cập nhật cache folder
          folderCache.handle = handle;
          folderCache.name = name;

          btn.disabled = true;
          btn.textContent = '⏳ Đang upload...';
        }

        // === TỐI ƯU: Kiểm tra cache trước ===
        const now = Date.now();
        let latestFile = null;
        let latestDate = new Date(0);
        
        if (folderCache.handle && folderCache.name === name && 
            folderCache.latestPdf && (now - folderCache.lastScan) < CACHE_TTL) {
          // Sử dụng cache nếu còn hiệu lực
          console.log('[AutoFill] Using cached PDF:', folderCache.latestPdf.name);
          latestFile = folderCache.latestPdf;
        } else {
          // === BƯỚC 2: Tìm file PDF mới nhất (TỐI ƯU) ===
          showOverlayStatus('⏳ Đang tìm file PDF...', 'info');
          let foundFiles = 0;

          // Tối ưu: Sử dụng Promise.all để parallel resolve handles
          const entries = [];
          for await (const entry of handle.values()) {
            if (entry.kind === 'file') {
              const ln = entry.name.toLowerCase();
              if (ln.endsWith('.pdf')) {
                foundFiles++;
                entries.push(entry);
                if (foundFiles > 50) break; // Giới hạn scanning để tránh chậm
              }
            }
          }

          // Parallel lấy metadata cho các file PDF tìm thấy
          if (entries.length > 0) {
            const fileMetas = await Promise.all(
              entries.slice(0, 20).map(async (entry) => {
                try {
                  const file = await entry.getFile();
                  return { handle: entry, file, name: entry.name, lastModified: file.lastModified };
                } catch {
                  return null;
                }
              })
            );

            // Tìm file mới nhất
            for (const fm of fileMetas) {
              if (fm && fm.lastModified > latestDate.getTime()) {
                latestDate = new Date(fm.lastModified);
                latestFile = fm;
              }
            }
          }

          // Cập nhật cache nếu tìm thấy file
          if (latestFile) {
            folderCache.handle = handle;
            folderCache.name = name;
            folderCache.lastScan = Date.now();
            folderCache.latestPdf = latestFile;
            console.log('[AutoFill] PDF cached:', latestFile.name);
          }
        }

        // === Kiểm tra kết quả ===
        if (!latestFile) {
          showOverlayStatus('❌ Không tìm thấy file PDF trong thư mục', 'error');
          btn.disabled = false;
          btn.textContent = '📤 Tải tài liệu lên';
          processing = false;
          return;
        }

        console.log('[AutoFill] Found PDF:', latestFile.name, '(modified:', new Date(latestFile.lastModified).toLocaleString(), ')');
        showOverlayStatus('⏳ Upload: ' + latestFile.name, 'info');

        // === BƯỚC 3: Upload vào form (TỐI ƯU) ===
        // Tối ưu: Đọc file trực tiếp, không qua ArrayBuffer trung gian
        const file = latestFile.file;
        const fileName = latestFile.name;
        
        // Sử dụng FileReaderSync hoặc async để đọc nhanh hơn
        const arrayBuffer = await file.arrayBuffer();
        
        // Tối ưu: Truyền trực tiếp ArrayBuffer thay vì Uint8Array để giảm bước chuyển đổi
        uploadFileToInput(fileName, arrayBuffer, file.type || 'application/pdf', (uploadSuccess) => {
          if (uploadSuccess) {
            showOverlayStatus('✅ Upload thành công!', 'success');
            chrome.runtime.sendMessage({ action: 'uploadCompleted', success: true });
            setTimeout(() => removeUploadOverlay(), 1500);
          } else {
            showOverlayStatus('❌ Upload thất bại', 'error');
            btn.disabled = false;
            btn.textContent = '📤 Tải tài liệu lên';
          }
          processing = false;
        });

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

  function removeUploadOverlay() {
    const overlay = document.getElementById('autofill-lock-overlay');
    if (overlay) overlay.remove();
    const style = document.getElementById('autofill-overlay-style');
    if (style) style.remove();
    overlayShown = false;
    console.log('[AutoFill] Overlay removed');
  }

  function showOverlayStatus(message, type) {
    const el = document.getElementById('autofill-upload-status');
    if (el) { el.textContent = message; el.className = type; }
  }

  // ==========================================
  // UPLOAD FILE TO INPUT
  // ==========================================

  function uploadFileToInput(fileName, fileData, fileType, callback) {
    try {
      const fileInputs = document.querySelectorAll('input[type="file"]');
      if (fileInputs.length === 0) {
        console.log('[AutoFill] No file input found');
        if (callback) callback(false);
        return;
      }

      const fileInput = fileInputs[0];
      // Tối ưu: Blob có thể nhận trực tiếp ArrayBuffer mà không cần chuyển Uint8Array
      const blob = new Blob([fileData], { type: fileType });
      const file = new File([blob], fileName, { type: fileType });

      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      fileInput.files = dataTransfer.files;

      // Dispatch events
      fileInput.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
      fileInput.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));

      console.log('[AutoFill] ✅ File uploaded:', fileName, 'type:', fileType);
      hasUploadedFile = true;

      chrome.runtime.sendMessage({ action: 'uploadCompleted', success: true, fileName });
      if (callback) callback(true);

    } catch (error) {
      console.error('[AutoFill] Upload error:', error);
      if (callback) callback(false);
    }
  }

  // ==========================================
  // DIALOG OBSERVERS
  // ==========================================

  function setupDialogObserver() {
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Citizen info dialog: #citizenInfoModal hoặc trong mat-dialog-container
            const isCitizenDialog = node.id === 'citizenInfoModal' ||
              (node.querySelector && node.querySelector('#citizenInfoModal'));
            const isMatDialog = node.matches && (node.matches('mat-dialog-container') || node.matches('.mat-mdc-dialog-container'));

            if (isCitizenDialog || isMatDialog) {
              console.log('[AutoFill] 🎯 Dialog detected!', isCitizenDialog ? 'Citizen modal' : 'Angular Material');
              if (lastFormData) {
                setTimeout(() => {
                  const container = node.id === 'citizenInfoModal' ? node :
                    (node.querySelector('#citizenInfoModal') || node);
                  fillDialog(container);
                }, 800);
              } else {
                const wait = setInterval(() => {
                  if (lastFormData) {
                    clearInterval(wait);
                    const container = node.id === 'citizenInfoModal' ? node :
                      (node.querySelector('#citizenInfoModal') || node);
                    fillDialog(container);
                  }
                }, 500);
                setTimeout(() => clearInterval(wait), 30000);
              }
            }
            if (node.querySelectorAll) {
              const dialogs = node.querySelectorAll('mat-dialog-container, .mat-mdc-dialog-container, #citizenInfoModal');
              dialogs.forEach(d => {
                if (lastFormData) {
                  setTimeout(() => fillDialog(d), 800);
                } else {
                  const wait = setInterval(() => {
                    if (lastFormData) { clearInterval(wait); fillDialog(d); }
                  }, 500);
                  setTimeout(() => clearInterval(wait), 30000);
                }
              });
            }
          }
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return observer;
  }

  function setupDialogCloseObserver() {
    const observer = new MutationObserver((mutations) => {
      let closed = false;
      for (const mutation of mutations) {
        for (const node of mutation.removedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE && node.matches) {
            if (node.matches('mat-dialog-container') || node.matches('.mat-mdc-dialog-container') || node.id === 'citizenInfoModal') {
              closed = true;
            }
          }
        }
        // Also check for removed element with citizenInfoModal ID
        for (const node of mutation.removedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE && node.querySelector) {
            if (node.querySelector('#citizenInfoModal')) {
              closed = true;
            }
          }
        }
      }
      if (closed) {
        console.log('[AutoFill] ✅ Citizen dialog closed - refilling main form');
        setTimeout(() => {
          if (lastFormData) {
            fillForm(lastFormData);
            // Sau khi điền lại, nếu không có dialog → timer 3s → hiện overlay
            setTimeout(() => {
              const dlg = document.querySelector('#citizenInfoModal');
              const ttl = document.querySelector('#citizenInfoModalLabel, .modal-title');
              if (!dlg && !(ttl && ttl.textContent.includes('Cập nhật thông tin cá nhân')) && !overlayShown) {
                showUploadOverlay();
              }
            }, 1500);
          }
        }, 1000);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return observer;
  }

  // Message handlers
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('[AutoFill] Message:', request.action);

    // Popup gửi handle để lưu vào IndexedDB của trang
    // NOTE: handle bị serialize qua message passing → mất method
    // Thay vào đó, content script sẽ tự mở directory picker
    if (request.action === 'saveFolderHandleFromPopup') {
      // Không lưu handle từ popup (bị mất method), chỉ lưu tên
      (async () => {
        try {
          const db = await initIDB();
          const tx = db.transaction(STORE_NAME, 'readwrite');
          // Chỉ lưu tên, không lưu handle
          tx.objectStore(STORE_NAME).put(request.folderName, 'folderName');
          await new Promise((res, rej) => {
            tx.oncomplete = () => res();
            tx.onerror = () => rej(tx.error);
          });
          console.log('[AutoFill] Folder name saved:', request.folderName, '(handle not saved - use picker directly)');
          sendResponse({ success: true });
        } catch (e) {
          console.error('[AutoFill] Error saving name:', e);
          sendResponse({ success: false });
        }
      })();
      return true;
    }

    // Content script mở directory picker để chọn thư mục
    if (request.action === 'pickFolderFromContent') {
      (async () => {
        try {
          if (!('showDirectoryPicker' in window)) {
            sendResponse({ success: false, error: 'Not supported' });
            return;
          }
          const handle = await window.showDirectoryPicker({ mode: 'read' });
          // Lưu handle trực tiếp (cùng origin → giữ nguyên method)
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

    // Reset folder handle trong IndexedDB của trang
    if (request.action === 'resetFolderHandle') {
      (async () => {
        try {
          const db = await initIDB();
          const tx = db.transaction(STORE_NAME, 'readwrite');
          await new Promise((res, rej) => {
            tx.objectStore(STORE_NAME).delete('folderHandle');
            tx.objectStore(STORE_NAME).delete('folderName');
            tx.oncomplete = () => res();
            tx.onerror = () => rej(tx.error);
          });
          console.log('[AutoFill] Handle deleted from page IndexedDB');
          sendResponse({ success: true });
        } catch (e) {
          console.error('[AutoFill] Error deleting handle:', e);
          sendResponse({ success: false });
        }
      })();
      return true;
    }

    if (request.action === 'fillForm') {
      // First try to fetch from API and cache, then fill
      (async () => {
        let data = request.data;
        if (!data || (!data.data && !data.cardObj && !data.identityNumber)) {
          data = await fetchDataFromAPI();
        }
        if (data) {
          apiDataCache = data; // Cache it
        }
        sendResponse(fillForm(data));
      })();
      return true;
    } else if (request.action === 'checkPage') {
      sendResponse({ isValid: isValidPage(), url: window.location.href, hasUploadedFile, overlayShown });
    } else if (request.action === 'uploadFile') {
      uploadFileToInput(request.fileName, request.fileData, request.fileType, (ok) => {
        sendResponse({ success: ok });
      });
      return true;
    } else if (request.action === 'fillDialog') {
      const dialog = document.querySelector('mat-dialog-container, .mat-mdc-dialog-container');
      sendResponse(dialog ? fillDialog(dialog) : { success: false, message: 'No dialog' });
    } else if (request.action === 'showUploadOverlay') {
      showUploadOverlay();
      sendResponse({ success: true });
    } else if (request.action === 'hideUploadOverlay') {
      removeUploadOverlay();
      sendResponse({ success: true });
    } else if (request.action === 'overlayUploadResult') {
      showOverlayStatus(request.success ? '✅ ' + (request.message || 'Thành công') : '❌ ' + (request.message || 'Thất bại'),
                        request.success ? 'success' : 'error');
      if (request.success) setTimeout(() => removeUploadOverlay(), 2000);
      else {
        const btn = document.getElementById('autofill-btn-upload');
        if (btn) { btn.disabled = false; btn.textContent = '📤 Tải tài liệu lên'; }
      }
      sendResponse({ success: true });
    }

    return true;
  });

  // ==========================================
  // INIT
  // ==========================================

  function init() {
    console.log('[AutoFill] Initializing...');
    setupDialogObserver();
    setupDialogCloseObserver();

    // Retry waitForPageReady nếu trang chưa render xong
    let attempts = 0;
    const maxAttempts = 10;
    let isFetching = false;

    function waitForPageReady() {
      if (isFetching) return; // Đã bắt đầu fetch, không retry nữa

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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  console.log('[AutoFill] Content script ready');
})();
