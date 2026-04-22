// Script injection for iframe - tự động điền form khi nhận dữ liệu từ API
(function() {
  'use strict';

  console.log('[AutoFill-Iframe] Script injected');

  // Valid URL patterns for the form
  const VALID_URL_PATTERNS = [
    /https:\/\/dichvucong\.thainguyen\.gov\.vn\/nop-ho-so/,
    /file:\/\/.*form-replica\.html/,
    /file:\/\/.*\.html/,
    /http:\/\/localhost.*form/,
    /http:\/\/127\.0\.0\.1.*form/
  ];

  // Check if current page is a valid form page
  function isValidPage() {
    const url = window.location.href;
    return VALID_URL_PATTERNS.some(pattern => pattern.test(url)) &&
           document.querySelector('.form-section, .content-wrapper, .page-content, mat-form-field');
  }

  // Tìm input/select/textarea dựa trên label text (Hỗ trợ Angular Material)
  function findFieldByLabelText(labelText) {
    const allLabels = document.querySelectorAll('mat-label');
    const searchText = labelText.toLowerCase().trim();

    console.log(`[AutoFill-Iframe] Searching for label: "${labelText}"`);

    for (const matLabel of allLabels) {
      const labelContent = matLabel.textContent.trim().toLowerCase();

      if (labelContent.includes(searchText)) {
        console.log('[AutoFill-Iframe] Found label:', matLabel.textContent.trim());

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

    console.log('[AutoFill-Iframe] No element found for label:', labelText);
    return null;
  }

  // Điền giá trị vào trường
  function fillField(element, value, type = 'text') {
    if (!element || element.disabled || element.hasAttribute('disabled')) {
      return false;
    }

    console.log('[AutoFill-Iframe] Filling field:', element, 'with value:', value);

    try {
      switch (type) {
        case 'text':
        case 'input':
          element.value = value;
          break;

        case 'select':
          if (element.tagName === 'MAT-SELECT' || element.classList.contains('mat-select')) {
            const matFormField = element.closest('mat-form-field');
            if (matFormField) {
              const selectEl = matFormField.querySelector('mat-select');
              if (selectEl) {
                const options = Array.from(selectEl.querySelectorAll('mat-option'));
                const matchedOption = options.find(opt =>
                  opt.value === value ||
                  opt.value === String(value) ||
                  opt.textContent.trim().toLowerCase().includes(value.toLowerCase())
                );

                if (matchedOption) {
                  matchedOption.click();
                  return true;
                }
              }
            }
            element.value = value;
          } else {
            const options = Array.from(element.options || []);
            const matchedOption = options.find(opt =>
              opt.value === value ||
              opt.value.includes(value) ||
              opt.text.toLowerCase().includes(value.toLowerCase())
            );
            if (matchedOption) {
              element.value = matchedOption.value;
            } else {
              element.value = value;
            }
          }
          break;

        case 'date':
          let formattedDate = value;
          if (/^\d{2}\/\d{2}\/\d{4}$/.test(value)) {
            formattedDate = value;
          } else {
            const date = new Date(value);
            if (!isNaN(date.getTime())) {
              const day = String(date.getDate()).padStart(2, '0');
              const month = String(date.getMonth() + 1).padStart(2, '0');
              const year = date.getFullYear();
              formattedDate = `${day}/${month}/${year}`;
            }
          }
          element.value = formattedDate;
          break;

        case 'textarea':
          element.value = value;
          break;
      }

      // Trigger events để Angular nhận biết thay đổi
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
      element.dispatchEvent(new Event('blur', { bubbles: true }));
      element.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true }));
      element.focus();
      setTimeout(() => element.blur(), 100);

      return true;
    } catch (e) {
      console.error('[AutoFill-Iframe] Error filling field:', e);
      return false;
    }
  }

  // Main function to fill form with JSON data
  function fillForm(data) {
    const isValid = isValidPage();

    if (!isValid) {
      console.log('[AutoFill-Iframe] Not on valid form page');
      return { success: false, message: 'Not on valid form page' };
    }

    const results = {
      success: true,
      filled: 0,
      failed: 0,
      skipped: 0,
      total: 0,
      details: []
    };

    console.log('[AutoFill-Iframe] Starting form fill with data:', data);

    function addResult(field, status, message = '') {
      results.total++;
      results.details.push({ field, status, message });
      if (status === 'success') results.filled++;
      else if (status === 'failed') results.failed++;
      else if (status === 'skipped') results.skipped++;
    }

    // Extract fieldsToFill from data
    let fieldsToFill = {};
    if (data && data.data && data.data.cardObj) {
      fieldsToFill = data.data.cardObj;
    } else if (data && data.cardObj) {
      fieldsToFill = data.cardObj;
    } else if (data && data.identityNumber) {
      fieldsToFill = data;
    } else {
      fieldsToFill = data || {};
    }

    console.log('[AutoFill-Iframe] Fields to fill:', fieldsToFill);

    // Mapping từ cardObj sang form
    const cardObjToFormMapping = {
      'identityNumber': { label: 'cmnd', type: 'text', isDisabled: true },
      'fullName': { label: 'tên người nộp', type: 'text', isDisabled: true },
      'dateOfBirth': { label: 'ngày sinh', type: 'date' },
      'placeOfResidence': { label: 'địa chỉ', type: 'text' },
      'dateOfIssue': { label: 'ngày cấp', type: 'date' },
    };

    // Điền từng field
    for (const [cardField, formMapping] of Object.entries(cardObjToFormMapping)) {
      if (!formMapping) continue;

      const value = fieldsToFill[cardField];
      if (!value || value === null || value === 'null' || value === '') continue;

      const element = findFieldByLabelText(formMapping.label);

      if (!element) {
        console.warn('[AutoFill-Iframe] ❌ Could not find element for:', cardField);
        addResult(cardField, 'failed', 'Element not found');
        continue;
      }

      if (formMapping.isDisabled || element.disabled || element.hasAttribute('disabled')) {
        addResult(cardField, 'skipped', 'Disabled field');
        continue;
      }

      const success = fillField(element, value, formMapping.type);
      if (success) {
        console.log('[AutoFill-Iframe] ✅ Filled:', cardField, '=', value);
        addResult(cardField, 'success', 'Filled');
      } else {
        addResult(cardField, 'failed', 'Fill failed');
      }
    }

    console.log('[AutoFill-Iframe] Form fill completed:', results);
    return results;
  }

  // Lắng nghe postMessage từ trang cha (DVCIfamre.html)
  window.addEventListener('message', (event) => {
    console.log('[AutoFill-Iframe] Received postMessage:', event.data);
    
    if (event.data && event.data.action === 'fillForm') {
      console.log('[AutoFill-Iframe] Auto-filling form');
      const result = fillForm(event.data.data);
      
      // Gửi kết quả về trang cha
      if (window.parent) {
        window.parent.postMessage({
          action: 'formFilled',
          filled: result.filled,
          total: result.total,
          success: result.success
        }, '*');
      }
    }
  });

  console.log('[AutoFill-Iframe] Script loaded successfully');
})();
