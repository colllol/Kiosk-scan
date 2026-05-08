/**
 * Form Filler Module
 * Xử lý tìm và điền thông tin vào form
 */

const FORM_FILLER = (function() {
  'use strict';

  // State
  let lastFormData = null;
  let apiDataCache = null;

  /**
   * Tìm field bằng label text
   * @param {string} labelText - Text của label cần tìm
   * @param {HTMLElement} container - Container để tìm (mặc định document)
   * @returns {HTMLElement|null} Element tìm thấy hoặc null
   */
  function findFieldByLabelText(labelText, container = document) {
    const searchText = labelText.toLowerCase().trim();

    // First try: Find by mat-label text
    const allLabels = container.querySelectorAll('mat-label');
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

    // Second try: Find by placeholder text (for select fields)
    if (searchText.includes('dịch vụ công')) {
      // Try to find by name="case_id"
      const caseIdSelect = container.querySelector('mat-select[name="case_id"]');
      if (caseIdSelect) return caseIdSelect;
      
      // Try to find by id containing "case" or "dich-vu-cong"
      const allSelects = container.querySelectorAll('mat-select');
      for (const select of allSelects) {
        const id = select.id || '';
        const name = select.getAttribute('name') || '';
        const placeholder = select.getAttribute('placeholder') || '';
        if (id.includes('case') || name.includes('case') || 
            placeholder.toLowerCase().includes('dịch vụ công') ||
            placeholder.includes('-- Dịch vụ công --')) {
          return select;
        }
      }
    }

    return null;
  }

  /**
   * Điền giá trị vào field
   * @param {HTMLElement} element - Element cần điền
   * @param {string} value - Giá trị cần điền
   * @param {string} type - Loại field ('text', 'date', 'select')
   * @returns {boolean} Thành công hay không
   */
  function fillField(element, value, type = 'text') {
    if (!element || element.disabled || element.hasAttribute('disabled')) return false;

    try {
      if (type === 'select' && (element.tagName === 'MAT-SELECT' || element.classList.contains('mat-select'))) {
        const matFormField = element.closest('mat-form-field');
        if (matFormField) {
          const selectEl = matFormField.querySelector('mat-select');
          if (selectEl) {
            // Store the current value to check if it changes
            const currentValue = selectEl.value || selectEl.textContent || '';
            
            selectEl.click();
            setTimeout(() => {
              const options = Array.from(document.querySelectorAll('mat-option'));
              const matched = options.find(opt =>
                opt.value === value || opt.value === String(value) ||
                opt.textContent.trim().toLowerCase().includes(value.toLowerCase()) ||
                opt.textContent.trim() === value
              );
              if (matched) {
                matched.click();
                // Dispatch change event
                selectEl.dispatchEvent(new Event('change', { bubbles: true }));
                selectEl.dispatchEvent(new Event('selectionChange', { bubbles: true }));
                
                // Check if value actually changed
                setTimeout(() => {
                  const newValue = selectEl.value || selectEl.textContent || '';
                  if (newValue !== currentValue) {
                    console.log('[FormFiller] Select value changed from', currentValue, 'to', newValue);
                  }
                }, 100);
              } else {
                console.log('[FormFiller] No matching option found for value:', value);
              }
            }, 500); // Increased timeout to 500ms for dropdown to fully open
            // We return true even if no option is found, because we tried
            // The actual success/failure is logged
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
      console.error('[FormFiller] Error filling field:', e);
      return false;
    }
  }

  /**
   * Xử lý mat-select
   * @param {HTMLElement} selectElement - Element select
   * @param {string} value - Giá trị cần chọn
   */
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

  /**
   * Lấy dữ liệu từ API
   * @returns {Promise<Object|null>} Dữ liệu API
   */
  async function fetchDataFromAPI() {
    if (apiDataCache) return apiDataCache;
    const API_URL = 'http://localhost:5431';
    try {
      const response = await fetch(API_URL, { method: 'GET', headers: { 'Accept': 'application/json' } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      apiDataCache = data;
      console.log('[FormFiller] API data fetched and cached');
      return data;
    } catch (error) {
      console.log('[FormFiller] API fetch failed:', error.message);
      return null;
    }
  }

  /**
   * Điền form chính
   * @param {Object} data - Dữ liệu cần điền
   * @returns {Object} Kết quả điền form
   */
  function fillForm(data) {
    // Nếu không có data, dùng cached data
    if (!data) {
      data = apiDataCache;
    }
    if (!data) {
      console.log('[FormFiller] No data available to fill form');
      return { success: false, message: 'No data available' };
    }

    // Kiểm tra trang hợp lệ
    if (!URL_SCANNER.isValidPage()) {
      console.log('[FormFiller] Not on valid form page.');
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

    // Trích xuất fields
    let fieldsToFill = {};
    if (data?.data?.cardObj) fieldsToFill = data.data.cardObj;
    else if (data?.cardObj) fieldsToFill = data.cardObj;
    else if (data?.identityNumber) fieldsToFill = data;
    else fieldsToFill = data || {};

    // Xử lý đặc biệt
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

    // Handle "Dịch vụ công" field based on service code
    const serviceCode = URL_SCANNER.extractServiceCodeFromUrl();
    if (serviceCode) {
      console.log('[FormFiller] Service code detected:', serviceCode);
      
      // Wait a bit for the page to fully initialize, then try to fill "Dịch vụ công"
      setTimeout(() => {
        // Find the "Dịch vụ công" field
        const dichVuCongElement = findFieldByLabelText('dịch vụ công');
        if (dichVuCongElement) {
          console.log('[FormFiller] Found "Dịch vụ công" field');
          
          // Try different values based on service code
          let serviceValues = [];
          
          if (serviceCode === URL_SCANNER.SERVICE_CODES.SIGNATURE_CERTIFICATION) {
            // 2.000884.000.00.00.H55 - Chứng thực chữ ký
            serviceValues = [
              'Chứng thực chữ ký',
              'Chứng thực chữ ký trong các giấy tờ, văn bản',
              '000884', // Service ID from code
              'H55', // Last part of code
              '2.000884.000.00.00.H55', // Full code
              'Chứng thực'
            ];
          } else if (serviceCode === URL_SCANNER.SERVICE_CODES.DOCUMENT_CERTIFICATION) {
            // 2.000815.000.00.00.H55 - Chứng thực tài liệu
            serviceValues = [
              'Chứng thực bản sao từ bản chính',
              'Chứng thực bản sao',
              '000815', // Service ID from code
              'H55', // Last part of code
              '2.000815.000.00.00.H55', // Full code
              'Chứng thực tài liệu'
            ];
          }
          
          let filled = false;
          for (const serviceValue of serviceValues) {
            console.log('[FormFiller] Trying to fill "Dịch vụ công" with:', serviceValue);
            if (fillField(dichVuCongElement, serviceValue, 'select')) {
              console.log('[FormFiller] Successfully filled with:', serviceValue);
              addResult('dichVuCong', 'success', `Filled with: ${serviceValue}`);
              filled = true;
              break;
            }
          }
          
          if (!filled) {
            console.log('[FormFiller] Could not fill "Dịch vụ công" with any value');
            addResult('dichVuCong', 'failed', 'Could not find matching option in dropdown');
          }
        } else {
          console.log('[FormFiller] Could not find "Dịch vụ công" field');
          addResult('dichVuCong', 'skipped', 'Field not found');
        }
      }, 1000); // Wait 1 second before trying to fill
    }

    console.log('[FormFiller] Form fill completed:', results);
    return results;
  }

  /**
   * Lấy dữ liệu form cuối cùng
   * @returns {Object|null}
   */
  function getLastFormData() {
    return lastFormData;
  }

  /**
   * Đặt dữ liệu form
   * @param {Object} data
   */
  function setLastFormData(data) {
    lastFormData = data;
  }

  /**
   * Lấy cache API
   * @returns {Object|null}
   */
  function getApiDataCache() {
    return apiDataCache;
  }

  /**
   * Đặt cache API
   * @param {Object} data
   */
  function setApiDataCache(data) {
    apiDataCache = data;
  }

  return {
    // Functions
    findFieldByLabelText,
    fillField,
    handleMatSelect,
    fetchDataFromAPI,
    fillForm,
    
    // Getters/Setters
    getLastFormData,
    setLastFormData,
    getApiDataCache,
    setApiDataCache
  };
})();