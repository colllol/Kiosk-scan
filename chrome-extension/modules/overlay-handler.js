/**
 * Overlay Handler Module
 * Xử lý overlay upload và quản lý file
 */

const OVERLAY_HANDLER = (function() {
  'use strict';

  // Tối ưu: Cache folder và latest PDF
  let folderCache = { handle: null, name: null, lastScan: 0, latestPdf: null };
  const CACHE_TTL = 30000; // 30 giây cache

  // IndexedDB for folder handle
  const DB_NAME = 'AutoFillFormDB';
  const DB_VERSION = 1;
  const STORE_NAME = 'folderHandles';
  let idb = null;

  /**
   * Khởi tạo IndexedDB
   * @returns {Promise<IDBDatabase>}
   */
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

  /**
   * Lấy folder handle từ IndexedDB
   * @returns {Promise<Object>}
   */
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
      console.error('[OverlayHandler] IDB error:', e);
      return { handle: null, name: null };
    }
  }

  /**
   * Hiển thị overlay upload
   */
  function showUploadOverlay() {
    if (COMPONENT_WORKFLOW.getOverlayShown()) {
      console.log('[OverlayHandler] Overlay already shown, skipping');
      return;
    }
    COMPONENT_WORKFLOW.setOverlayShown(true);

    console.log('[OverlayHandler] Showing upload overlay on page');

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

    // Button click handler
    const btn = document.getElementById('autofill-btn-upload');
    let processing = false;

    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      if (btn.disabled) {
        console.log('[OverlayHandler] Already processing, ignoring click');
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
          console.log('[OverlayHandler] Using cached PDF:', folderCache.latestPdf.name);
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
            console.log('[OverlayHandler] PDF cached:', latestFile.name);
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

        console.log('[OverlayHandler] Found PDF:', latestFile.name, '(modified:', new Date(latestFile.lastModified).toLocaleString(), ')');
        showOverlayStatus('⏳ Upload: ' + latestFile.name, 'info');

        // === BƯỚC 3: Upload vào form (TỐI ƯU) ===
        const file = latestFile.file;
        const fileName = latestFile.name;
        const arrayBuffer = await file.arrayBuffer();

        // Upload file
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
        console.error('[OverlayHandler] Error:', error);
        showOverlayStatus('❌ Lỗi: ' + error.message, 'error');
        btn.disabled = false;
        btn.textContent = '📤 Tải tài liệu lên';
        processing = false;
      }
    }, { once: false });

    console.log('[OverlayHandler] Overlay created on page');
  }

  /**
   * Xóa overlay upload
   */
  function removeUploadOverlay() {
    const overlay = document.getElementById('autofill-lock-overlay');
    if (overlay) overlay.remove();
    const style = document.getElementById('autofill-overlay-style');
    if (style) style.remove();
    COMPONENT_WORKFLOW.setOverlayShown(false);
    console.log('[OverlayHandler] Overlay removed');
  }

  /**
   * Hiển thị trạng thái trên overlay
   * @param {string} message - Thông điệp
   * @param {string} type - Loại thông điệp ('success', 'error', 'info', 'warning')
   */
  function showOverlayStatus(message, type) {
    const el = document.getElementById('autofill-upload-status');
    if (el) { el.textContent = message; el.className = type; }
  }

  /**
   * Upload file vào input
   * @param {string} fileName - Tên file
   * @param {ArrayBuffer} fileData - Dữ liệu file
   * @param {string} fileType - Loại file
   * @param {Function} callback - Callback khi hoàn thành
   */
  function uploadFileToInput(fileName, fileData, fileType, callback) {
    try {
      const fileInputs = document.querySelectorAll('input[type="file"]');
      if (fileInputs.length === 0) {
        console.log('[OverlayHandler] No file input found');
        if (callback) callback(false);
        return;
      }

      const fileInput = fileInputs[0];
      const blob = new Blob([fileData], { type: fileType });
      const file = new File([blob], fileName, { type: fileType });

      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      fileInput.files = dataTransfer.files;

      // Dispatch events
      fileInput.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
      fileInput.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));

      console.log('[OverlayHandler] ✅ File uploaded:', fileName, 'type:', fileType);

      chrome.runtime.sendMessage({ action: 'uploadCompleted', success: true, fileName });
      if (callback) callback(true);

    } catch (error) {
      console.error('[OverlayHandler] Upload error:', error);
      if (callback) callback(false);
    }
  }

  return {
    // Functions
    showUploadOverlay,
    removeUploadOverlay,
    showOverlayStatus,
    uploadFileToInput,
    
    // IndexedDB functions
    initIDB,
    getFolderHandleFromIDB
  };
})();