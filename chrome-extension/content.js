/**
 * Content Script - Auto Fill + Dialog Detection + Overlay Upload
 * Modular version with separated concerns
 */

(function() {
  'use strict';

  console.log('[AutoFill] Content script loaded (modular version)');
  console.log('[AutoFill] URL:', window.location.href);

  // Load modules (they are loaded before this script)
  // Modules available: URL_SCANNER, FORM_FILLER, DIALOG_HANDLER, COMPONENT_WORKFLOW, OVERLAY_HANDLER

  // State
  let hasUploadedFile = false;

  // ==========================================
  // MESSAGE HANDLERS
  // ==========================================

  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('[AutoFill] Message:', request.action);

    // Popup gửi handle để lưu vào IndexedDB của trang
    if (request.action === 'saveFolderHandleFromPopup') {
      // Không lưu handle từ popup (bị mất method), chỉ lưu tên
      (async () => {
        try {
          const db = await OVERLAY_HANDLER.initIDB();
          const tx = db.transaction('folderHandles', 'readwrite');
          // Chỉ lưu tên, không lưu handle
          tx.objectStore('folderHandles').put(request.folderName, 'folderName');
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
          const db = await OVERLAY_HANDLER.initIDB();
          const tx = db.transaction('folderHandles', 'readwrite');
          await new Promise((res, rej) => {
            tx.objectStore('folderHandles').put(handle, 'folderHandle');
            tx.objectStore('folderHandles').put(handle.name, 'folderName');
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
          const db = await OVERLAY_HANDLER.initIDB();
          const tx = db.transaction('folderHandles', 'readwrite');
          await new Promise((res, rej) => {
            tx.objectStore('folderHandles').delete('folderHandle');
            tx.objectStore('folderHandles').delete('folderName');
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
          data = await FORM_FILLER.fetchDataFromAPI();
        }
        if (data) {
          FORM_FILLER.setApiDataCache(data); // Cache it
        }
        sendResponse(FORM_FILLER.fillForm(data));
      })();
      return true;
    } else if (request.action === 'checkPage') {
      sendResponse({
        isValid: URL_SCANNER.isValidPage(),
        url: window.location.href,
        hasUploadedFile,
        overlayShown: COMPONENT_WORKFLOW.getOverlayShown(),
        serviceCode: URL_SCANNER.extractServiceCodeFromUrl(),
        serviceInfo: URL_SCANNER.getCurrentServiceInfo()
      });
    } else if (request.action === 'uploadFile') {
      OVERLAY_HANDLER.uploadFileToInput(request.fileName, request.fileData, request.fileType, (ok) => {
        sendResponse({ success: ok });
      });
      return true;
    } else if (request.action === 'fillDialog') {
      const dialog = document.querySelector('mat-dialog-container, .mat-mdc-dialog-container');
      sendResponse(dialog ? DIALOG_HANDLER.fillDialog(dialog) : { success: false, message: 'No dialog' });
    } else if (request.action === 'showUploadOverlay') {
      OVERLAY_HANDLER.showUploadOverlay();
      sendResponse({ success: true });
    } else if (request.action === 'hideUploadOverlay') {
      OVERLAY_HANDLER.removeUploadOverlay();
      sendResponse({ success: true });
    } else if (request.action === 'overlayUploadResult') {
      OVERLAY_HANDLER.showOverlayStatus(request.success ? '✅ ' + (request.message || 'Thành công') : '❌ ' + (request.message || 'Thất bại'),
                        request.success ? 'success' : 'error');
      if (request.success) setTimeout(() => OVERLAY_HANDLER.removeUploadOverlay(), 2000);
      else {
        const btn = document.getElementById('autofill-btn-upload');
        if (btn) { btn.disabled = false; btn.textContent = '📤 Tải tài liệu lên'; }
      }
      sendResponse({ success: true });
    }

    return true;
  });

  // ==========================================
  // INITIALIZATION
  // ==========================================

  function init() {
    console.log('[AutoFill] Initializing modular version...');
    
    // Setup dialog observers
    DIALOG_HANDLER.setupDialogObserver();
    DIALOG_HANDLER.setupDialogCloseObserver();

    // Retry waitForPageReady nếu trang chưa render xong
    let attempts = 0;
    const maxAttempts = 10;
    let isFetching = false;

    function waitForPageReady() {
      if (isFetching) return; // Đã bắt đầu fetch, không retry nữa

      if (URL_SCANNER.isValidPage()) {
        isFetching = true;
        console.log('[AutoFill] Page is ready, fetching API data...');
        if (!FORM_FILLER.getApiDataCache()) {
          FORM_FILLER.fetchDataFromAPI().then((data) => {
            if (data) {
              FORM_FILLER.setApiDataCache(data);
              console.log('[AutoFill] Filling form with API data...');
              const fillResult = FORM_FILLER.fillForm(data);
              
              // Sau khi điền form, kiểm tra và xử lý workflow
              if (fillResult.success) {
                COMPONENT_WORKFLOW.checkAndStartWorkflow();
              }
            }
          });
        } else {
          // Đã có cache, điền form ngay
          const fillResult = FORM_FILLER.fillForm(FORM_FILLER.getApiDataCache());
          if (fillResult.success) {
            COMPONENT_WORKFLOW.checkAndStartWorkflow();
          }
        }
        return;
      }

      attempts++;
      if (attempts < maxAttempts) {
        console.log(`[AutoFill] Page not ready (attempt ${attempts}/${maxAttempts}), retrying...`);
        setTimeout(waitForPageReady, 1000);
      } else {
        console.log('[AutoFill] Max attempts reached, page may not be a valid form');
      }
    }

    // Bắt đầu kiểm tra trang
    waitForPageReady();
  }

  // Khởi động khi DOM sẵn sàng
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();