/**
 * Dialog Handler Module
 * Xử lý dialog "Cập nhật thông tin cá nhân"
 */

const DIALOG_HANDLER = (function() {
  'use strict';

  /**
   * Điền thông tin vào dialog
   * @param {HTMLElement} dialogContainer - Container của dialog
   * @returns {Object} Kết quả điền dialog
   */
  function fillDialog(dialogContainer = document) {
    if (!dialogContainer || dialogContainer === document) {
      dialogContainer = document.querySelector('mat-dialog-container, .mat-mdc-dialog-container') ||
                        document.querySelector('[role="dialog"]');
    }
    
    const lastFormData = FORM_FILLER.getLastFormData();
    if (!dialogContainer || !lastFormData) {
      return { success: false, message: 'No dialog or data' };
    }

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
      if (!value || value === null || value === 'null' || value === '') {
        addResult(m.dialogField, 'skipped', 'No value');
        continue;
      }

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

      if (!element) {
        addResult(m.dialogField, 'failed', 'Not found');
        continue;
      }
      if (m.disabled || element.disabled || element.hasAttribute('disabled')) {
        addResult(m.dialogField, 'skipped', 'Disabled');
        continue;
      }

      if (m.type === 'select' && (element.tagName === 'MAT-SELECT' || element.classList.contains('mat-select'))) {
        FORM_FILLER.handleMatSelect(element, value, m.dialogField);
        addResult(m.dialogField, 'success', `Selecting: ${value}`);
      } else if (FORM_FILLER.fillField(element, value, m.type)) {
        addResult(m.dialogField, 'success', `Filled: ${value}`);
      } else {
        addResult(m.dialogField, 'failed', 'Fill failed');
      }
    }

    console.log('[DialogHandler] Dialog fill completed:', results);
    return results;
  }

  /**
   * Thiết lập observer để phát hiện dialog
   * @returns {MutationObserver}
   */
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
              console.log('[DialogHandler] 🎯 Dialog detected!', isCitizenDialog ? 'Citizen modal' : 'Angular Material');
              const lastFormData = FORM_FILLER.getLastFormData();
              if (lastFormData) {
                setTimeout(() => {
                  const container = node.id === 'citizenInfoModal' ? node :
                    (node.querySelector('#citizenInfoModal') || node);
                  fillDialog(container);
                }, 800);
              } else {
                const wait = setInterval(() => {
                  const data = FORM_FILLER.getLastFormData();
                  if (data) {
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
                const lastFormData = FORM_FILLER.getLastFormData();
                if (lastFormData) {
                  setTimeout(() => fillDialog(d), 800);
                } else {
                  const wait = setInterval(() => {
                    const data = FORM_FILLER.getLastFormData();
                    if (data) {
                      clearInterval(wait);
                      fillDialog(d);
                    }
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

  /**
   * Thiết lập observer để phát hiện dialog đóng
   * @returns {MutationObserver}
   */
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
        console.log('[DialogHandler] ✅ Citizen dialog closed - refilling main form');
        setTimeout(() => {
          const lastFormData = FORM_FILLER.getLastFormData();
          if (lastFormData) {
            FORM_FILLER.fillForm(lastFormData);
          }
        }, 1000);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return observer;
  }

  return {
    // Functions
    fillDialog,
    setupDialogObserver,
    setupDialogCloseObserver
  };
})();