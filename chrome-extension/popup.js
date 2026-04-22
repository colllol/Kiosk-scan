// Popup script - IndexedDB folder handle + Auto-upload trigger
(function() {
  'use strict';

  const VALID_URL_PATTERNS = [
    /https:\/\/dichvucong\.thainguyen\.gov\.vn\/nop-ho-so/,
    /file:\/\/.*\.html/,
    /http:\/\/localhost/,
    /http:\/\/127\.0\.0\.1/
  ];

  // DOM elements
  let apiUrlInput, jsonDataTextarea, btnFetch, btnFill, btnCheckPage, btnClear;
  let btnSelectFolder, btnResetFolder, pageStatus, fetchStatus, fillStatus, uploadStatus;
  let folderPathDisplay;

  // State
  let folderName = '';

  // Initialize DOM elements
  function initDOMElements() {
    apiUrlInput = document.getElementById('api-url');
    jsonDataTextarea = document.getElementById('json-data');
    btnFetch = document.getElementById('btn-fetch');
    btnFill = document.getElementById('btn-fill');
    btnCheckPage = document.getElementById('btn-check-page');
    btnClear = document.getElementById('btn-clear');
    btnSelectFolder = document.getElementById('btn-select-folder');
    btnResetFolder = document.getElementById('btn-reset-folder');
    pageStatus = document.getElementById('page-status');
    fetchStatus = document.getElementById('fetch-status');
    fillStatus = document.getElementById('fill-status');
    uploadStatus = document.getElementById('upload-status');
    folderPathDisplay = document.getElementById('folder-path');
  }

  // Show status message
  function showStatus(element, message, type) {
    if (!element) return;
    element.textContent = message;
    element.className = `status ${type}`;
    setTimeout(() => {
      element.className = 'status';
    }, 5000);
  }

  // Check if current tab is on valid page
  function checkCurrentPage() {
    if (!pageStatus) return;

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || !tabs[0]) {
        pageStatus.textContent = '⚠️ Không xác định được trang';
        pageStatus.className = 'page-status invalid';
        return;
      }

      const url = tabs[0].url;
      const isValid = VALID_URL_PATTERNS.some(pattern => pattern.test(url));

      if (isValid) {
        pageStatus.textContent = '✅ Trang hợp lệ';
        pageStatus.className = 'page-status valid';
      } else {
        pageStatus.textContent = '❌ Không phải trang form';
        pageStatus.className = 'page-status invalid';
      }
    });
  }

  // Setup all event listeners
  function setupEventListeners() {
    // Select folder button - ủy quyền cho content script mở picker
    if (btnSelectFolder) {
      btnSelectFolder.addEventListener('click', async () => {
        try {
          // Gửi message cho content script để mở directory picker
          const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
          if (!tab) {
            showStatus(uploadStatus, '❌ Không tìm thấy tab form', 'error');
            return;
          }

          btnSelectFolder.disabled = true;
          btnSelectFolder.textContent = '⏳ Đang chờ...';
          showStatus(uploadStatus, '⏳ Vui lòng chọn thư mục trên trang form', 'info');

          const response = await new Promise((resolve) => {
            chrome.tabs.sendMessage(tab.id, { action: 'pickFolderFromContent' }, (resp) => {
              if (chrome.runtime.lastError) {
                resolve({ success: false, error: chrome.runtime.lastError.message });
              } else {
                resolve(resp);
              }
            });
          });

          btnSelectFolder.disabled = false;
          btnSelectFolder.textContent = '📂 Chọn thư mục';

          if (response && response.success) {
            folderName = response.folderName;
            folderPathDisplay.textContent = `📁 ${folderName}`;
            folderPathDisplay.style.display = 'block';
            showStatus(uploadStatus, `✅ Đã chọn thư mục: ${folderName}`, 'success');

            // Lưu tên vào storage để hiển thị
            await chrome.storage.local.set({ folderSet: true, folderName: folderName });

            if (btnResetFolder) {
              btnResetFolder.style.display = 'block';
            }
          } else if (response?.error === 'Cancelled') {
            showStatus(uploadStatus, '⏭️ Đã hủy chọn thư mục', 'info');
          } else {
            showStatus(uploadStatus, '❌ Lỗi: ' + (response?.error || 'Không xác định'), 'error');
          }

        } catch (error) {
          console.error('[Popup] Error selecting folder:', error);
          btnSelectFolder.disabled = false;
          btnSelectFolder.textContent = '📂 Chọn thư mục';
          showStatus(uploadStatus, '❌ Lỗi: ' + error.message, 'error');
        }
      });
    }

    // Reset folder button
    if (btnResetFolder) {
      btnResetFolder.addEventListener('click', async () => {
        try {
          // 1. Xóa handle khỏi IndexedDB của extension
          await chrome.runtime.sendMessage({ action: 'deleteFolderHandle' });
          await chrome.storage.local.remove(['folderSet', 'folderName']);

          // 2. Xóa handle khỏi IndexedDB của trang (content script)
          try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            if (tab) {
              chrome.tabs.sendMessage(tab.id, { action: 'resetFolderHandle' });
            }
          } catch (e) { /* ignore */ }

          folderName = '';
          folderPathDisplay.textContent = '';
          folderPathDisplay.style.display = 'none';

          if (btnResetFolder) {
            btnResetFolder.style.display = 'none';
          }

          showStatus(uploadStatus, '🗑️ Đã xóa thư mục đã chọn', 'info');
          console.log('[Popup] Folder handle reset');

        } catch (error) {
          console.error('[Popup] Error resetting folder:', error);
          showStatus(uploadStatus, '❌ Lỗi reset: ' + error.message, 'error');
        }
      });
    }

    // Fetch data from API and fill form
    if (btnFetch) {
      btnFetch.addEventListener('click', async () => {
        const apiUrl = 'http://localhost:5431';

        btnFetch.disabled = true;
        btnFetch.textContent = '⏳ Đang lấy dữ liệu từ API...';
        showStatus(fetchStatus, '', '');

        try {
          const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
          const isValid = VALID_URL_PATTERNS.some(pattern => pattern.test(tab.url));

          if (!isValid) {
            showStatus(fetchStatus, '❌ Vui lòng mở trang form trước', 'error');
            btnFetch.disabled = false;
            btnFetch.textContent = '🚀 Lấy dữ liệu và điền form';
            return;
          }

          const apiResponse = await fetch(apiUrl, {
            method: 'GET',
            headers: { 'Accept': 'application/json' }
          });

          if (!apiResponse.ok) {
            throw new Error(`HTTP ${apiResponse.status}: ${apiResponse.statusText}`);
          }

          const responseData = await apiResponse.json();
          console.log('[Popup] API Response:', responseData);

          btnFetch.disabled = false;
          btnFetch.textContent = '🚀 Lấy dữ liệu và điền form';

          chrome.tabs.sendMessage(tab.id, {
            action: 'fillForm',
            data: responseData
          }, (fillResponse) => {
            if (chrome.runtime.lastError) {
              showStatus(fetchStatus, '❌ Lỗi: ' + chrome.runtime.lastError.message, 'error');
              return;
            }

            if (fillResponse?.success) {
              showStatus(fetchStatus, `✅ Đã điền ${fillResponse.filled}/${fillResponse.total} trường!`, 'success');
            } else {
              showStatus(fetchStatus, '❌ Lỗi: ' + (fillResponse?.error || fillResponse?.message || 'Không xác định'), 'error');
            }
          });
        } catch (error) {
          showStatus(fetchStatus, '❌ Lỗi: ' + error.message, 'error');
          btnFetch.disabled = false;
          btnFetch.textContent = '🚀 Lấy dữ liệu và điền form';
        }
      });
    }

    // Fill form with manual JSON
    if (btnFill) {
      btnFill.addEventListener('click', async () => {
        const jsonText = jsonDataTextarea.value.trim();
        if (!jsonText) {
          showStatus(fillStatus, '⚠️ Vui lòng dán dữ liệu JSON', 'error');
          return;
        }

        try {
          const data = JSON.parse(jsonText);
          const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
          const isValid = VALID_URL_PATTERNS.some(pattern => pattern.test(tab.url));

          if (!isValid) {
            showStatus(fillStatus, '❌ Vui lòng mở trang form trước', 'error');
            return;
          }

          chrome.tabs.sendMessage(tab.id, { action: 'fillForm', data }, (response) => {
            if (chrome.runtime.lastError) {
              showStatus(fillStatus, '❌ Lỗi: ' + chrome.runtime.lastError.message, 'error');
              return;
            }

            if (response?.success) {
              showStatus(fillStatus, `✅ Đã điền ${response.filled}/${response.total} trường!`, 'success');
              chrome.storage.local.set({ autoFillData: data });
            } else {
              showStatus(fillStatus, '❌ Lỗi: ' + (response?.message || 'Không thể điền form'), 'error');
            }
          });
        } catch (error) {
          showStatus(fillStatus, '❌ JSON không hợp lệ: ' + error.message, 'error');
        }
      });
    }

    // Check page button
    if (btnCheckPage) {
      btnCheckPage.addEventListener('click', checkCurrentPage);
    }

    // Clear button
    if (btnClear) {
      btnClear.addEventListener('click', async () => {
        apiUrlInput.value = '';
        jsonDataTextarea.value = '';
        chrome.storage.local.remove(['autoFillData', 'folderSet', 'folderName']);
        fetchStatus.className = 'status';
        fillStatus.className = 'status';
        uploadStatus.className = 'status';
        showStatus(fillStatus, '🗑️ Đã xóa dữ liệu', 'info');
      });
    }
  }

  // Initialize
  async function init() {
    initDOMElements();
    setupEventListeners();
    checkCurrentPage();

    // Kiểm tra trạng thái folder từ background
    try {
      const response = await chrome.runtime.sendMessage({ action: 'getFolderHandleMeta' });
      if (response && response.hasHandle) {
        folderName = response.folderName || '';
        folderPathDisplay.textContent = `📁 ${folderName}`;
        folderPathDisplay.style.display = 'block';

        if (btnResetFolder) {
          btnResetFolder.style.display = 'block';
        }
      }
    } catch (error) {
      console.error('[Popup] Error checking folder status:', error);
    }
  }

  init();
})();
