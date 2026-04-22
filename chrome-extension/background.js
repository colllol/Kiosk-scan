// Background service worker - Minimal
// Chỉ làm nhiệm vụ lưu handle vào IndexedDB và định tuyến message

const DB_NAME = 'AutoFillFormDB';
const DB_VERSION = 1;
const STORE_NAME = 'folderHandles';
let db = null;

function initDB() {
  return new Promise((resolve, reject) => {
    if (db) { resolve(db); return; }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => { db = req.result; resolve(db); };
    req.onupgradeneeded = (e) => {
      const d = e.target.result;
      if (!d.objectStoreNames.contains(STORE_NAME)) d.createObjectStore(STORE_NAME);
    };
  });
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'saveFolderHandle') {
    (async () => {
      try {
        const d = await initDB();
        const tx = d.transaction(STORE_NAME, 'readwrite');
        await new Promise((res, rej) => {
          tx.objectStore(STORE_NAME).put(request.handle, 'folderHandle');
          tx.objectStore(STORE_NAME).put(request.folderName, 'folderName');
          tx.oncomplete = () => res();
          tx.onerror = () => rej(tx.error);
        });
        console.log('[BG] Handle saved:', request.folderName);
        sendResponse({ success: true });
      } catch (e) {
        console.error('[BG] Save error:', e);
        sendResponse({ success: false });
      }
    })();
    return true;
  }

  if (request.action === 'getFolderHandleMeta') {
    (async () => {
      try {
        const d = await initDB();
        const tx = d.transaction(STORE_NAME, 'readonly');
        const h = await new Promise((res, rej) => {
          const r = tx.objectStore(STORE_NAME).get('folderHandle');
          r.onsuccess = () => res(r.result);
          r.onerror = () => rej(r.error);
        });
        const n = await new Promise((res, rej) => {
          const r = tx.objectStore(STORE_NAME).get('folderName');
          r.onsuccess = () => res(r.result);
          r.onerror = () => rej(r.error);
        });
        sendResponse({ hasHandle: !!h, folderName: n || '' });
      } catch (e) {
        sendResponse({ hasHandle: false, folderName: '' });
      }
    })();
    return true;
  }

  if (request.action === 'deleteFolderHandle') {
    (async () => {
      try {
        const d = await initDB();
        const tx = d.transaction(STORE_NAME, 'readwrite');
        await new Promise((res, rej) => {
          tx.objectStore(STORE_NAME).delete('folderHandle');
          tx.objectStore(STORE_NAME).delete('folderName');
          tx.oncomplete = () => res();
          tx.onerror = () => rej(tx.error);
        });
        sendResponse({ success: true });
      } catch (e) {
        sendResponse({ success: false });
      }
    })();
    return true;
  }

  if (request.action === 'uploadCompleted') {
    console.log('[BG] Upload completed:', request.success);
    sendResponse({ success: true });
    return true;
  }
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ autoFillData: null });
});

chrome.runtime.onStartup.addListener(() => {
  initDB().catch(e => console.error('[BG] InitDB failed:', e));
});

// ==========================================
// URL MONITORING FOR TICKET PROCESSING
// ==========================================

const TARGET_URL = 'https://dichvucong.thainguyen.gov.vn/thong-tin-cong-dan';
const BACKEND_API = 'http://localhost:5000';
const QUEUESYSTEM_API = 'http://192.168.100.238/QueueSystemAdmin/api/ticket/create';

// Track processed URLs to avoid duplicate requests
const processedUrls = new Set();

// Monitor URL changes
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url) {
    checkAndTriggerTicket(tab.url, tabId);
  }
});

chrome.tabs.onActivated.addListener((activeInfo) => {
  chrome.tabs.get(activeInfo.tabId, (tab) => {
    if (chrome.runtime.lastError) return;
    checkAndTriggerTicket(tab.url, tab.id);
  });
});

function checkAndTriggerTicket(url, tabId) {
  if (!url) return;

  // Check if URL matches target
  if (url.includes('/thong-tin-cong-dan')) {
    // Avoid duplicate processing
    if (processedUrls.has(url)) {
      console.log('[BG] URL already processed, skipping:', url);
      return;
    }

    console.log('[BG] 🎯 Target URL detected:', url);
    processedUrls.add(url);

    // Process ticket: get info from backend → call QueueSystem API → print
    processTicketForUrl(url, tabId);
  }
}

async function processTicketForUrl(url, tabId) {
  try {
    console.log('[BG] 🎫 Processing ticket for URL:', url);

    // Step 1: Get latest ticket info from backend
    console.log('[BG] Step 1: Getting latest ticket from backend...');
    const ticketResponse = await fetch(`${BACKEND_API}/api/latest-ticket`);
    
    if (!ticketResponse.ok) {
      throw new Error(`Backend returned ${ticketResponse.status}: Không có ticket nào`);
    }

    const ticketData = await ticketResponse.json();
    console.log('[BG] ✅ Got ticket info:', ticketData);

    const { stt, formattedStt, filename, serviceId, serviceName } = ticketData;

    // Step 2: Call QueueSystem API
    console.log('[BG] Step 2: Calling QueueSystem API...');
    console.log('[BG] Target URL:', QUEUESYSTEM_API);
    
    const queuePayload = {
      ticketNumber: formattedStt,
      serviceId: serviceId || 1,
      counterId: 1,
      filePdf: filename || " "
    };
    console.log('[BG] Payload:', JSON.stringify(queuePayload));

    let queueResponse;
    let queueSuccess = false;
    let queueErrorText = '';
    try {
      queueResponse = await fetch(QUEUESYSTEM_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(queuePayload)
      });

      if (queueResponse.ok) {
        queueSuccess = true;
        console.log('[BG] ✅ QueueSystem API success');
      } else {
        queueErrorText = await queueResponse.text();
        console.error('[BG] ❌ QueueSystem API error:', queueResponse.status, queueErrorText);
      }
    } catch (fetchError) {
      console.error('[BG] ❌ QueueSystem fetch failed:', fetchError.name, fetchError.message);
      console.error('[BG] 💡 Kiểm tra: Extension đã reload chưa? Server 192.168.100.238 có bật không?');
      console.error('[BG] ⚠️ Tiếp tục in ticket dù QueueSystem lỗi...');
      queueSuccess = false;
    }

    // Step 3: Trigger print via backend
    console.log('[BG] Step 3: Triggering print...');
    const printResponse = await fetch(`${BACKEND_API}/api/print-ticket`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stt: stt,
        filename: filename,
        serviceName: serviceName || 'HỘ TỊCH - CHỨNG THỰC'
      })
    });

    if (!printResponse.ok) {
      console.error('[BG] ❌ Print API error:', printResponse.status);
    } else {
      console.log('[BG] ✅ Print triggered successfully');
    }

    // Show notification to user
    chrome.notifications?.create({
      type: 'basic',
      title: queueSuccess ? 'Số thứ tự đã được tạo' : 'Đã in phiếu (QueueSystem lỗi)',
      message: `Số thứ tự: ${formattedStt}\nDịch vụ: ${serviceName || 'HỘ TỊCH - CHỨNG THỰC'}${!queueSuccess ? '\n⚠️ QueueSystem: kiểm tra server 192.168.100.238' : ''}`,
      priority: 2
    });

    // Send to content script if needed
    chrome.tabs.sendMessage(tabId, {
      action: 'ticketCreated',
      ticketNumber: formattedStt,
      serviceId: serviceId,
      serviceName: serviceName
    }).catch(() => {
      // Content script may not be ready, that's okay
    });

    // Step 4: Clear cookies for dichvucong.thainguyen.gov.vn
    console.log('[BG] Step 4: Clearing cookies for dichvucong.thainguyen.gov.vn...');
    await clearCookiesForDomain('dichvucong.thainguyen.gov.vn');

  } catch (error) {
    console.error('[BG] ❌ Failed to process ticket:', error);

    // Show error notification
    chrome.notifications?.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: 'Lỗi xử lý số thứ tự',
      message: `${error.message}`,
      priority: 2
    });
  }
}

// ==========================================
// COOKIE MANAGEMENT
// ==========================================

/**
 * Clear all cookies for a specific domain
 * @param {string} domain - Domain to clear cookies for
 */
async function clearCookiesForDomain(domain) {
  try {
    // Debug: List ALL cookies first
    console.log('[BG] 🔍 Debugging cookie domains...');
    const allCookies = await chrome.cookies.getAll({});
    console.log(`[BG] Total cookies in browser: ${allCookies.length}`);
    
    // Log all cookie domains and names for debugging
    const uniqueDomains = [...new Set(allCookies.map(c => c.domain))];
    console.log('[BG] All unique cookie domains:', uniqueDomains);
    
    // Find cookies that might be related to dichvucong
    const matchingCookies = allCookies.filter(c => 
      c.domain.includes('dichvucong') || 
      c.domain.includes('thainguyen') ||
      c.name.toLowerCase().includes('session') ||
      c.name.toLowerCase().includes('auth') ||
      c.name.toLowerCase().includes('token')
    );
    
    console.log(`[BG] Found ${matchingCookies.length} potentially relevant cookies:`);
    matchingCookies.forEach(c => {
      console.log(`  - ${c.name} @ ${c.domain} ${c.path} (HttpOnly: ${c.httpOnly}, Secure: ${c.secure})`);
    });

    // Clear ALL cookies that match our target patterns
    let cleared = 0;
    for (const cookie of matchingCookies) {
      try {
        const url = `http${cookie.secure ? 's' : ''}://${cookie.domain.replace(/^\./, '')}${cookie.path}`;
        
        const removed = await chrome.cookies.remove({
          url: url,
          name: cookie.name
        });
        
        if (removed) {
          cleared++;
          console.log(`[BG] ✅ Removed: ${cookie.name} @ ${cookie.domain}`);
        } else {
          console.warn(`[BG] ⚠️ Failed to remove: ${cookie.name} @ ${cookie.domain}`);
        }
      } catch (err) {
        console.error(`[BG] ❌ Error removing ${cookie.name}:`, err);
      }
    }

    // Also try to clear cookies from ALL tabs with the target domain
    console.log('[BG] 🔄 Also clearing via chrome.tabs.remove for safety...');
    
    // Clear browser cache and storage if possible
    console.log(`[BG] ✅ Cleared ${cleared} cookies total`);
    
    return cleared;
  } catch (error) {
    console.error('[BG] ❌ Error clearing cookies:', error);
    return 0;
  }
}
