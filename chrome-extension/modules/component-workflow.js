/**
 * Component Workflow Module
 * Xử lý thêm thành phần và điền nội dung theo dịch vụ
 */

const COMPONENT_WORKFLOW = (function() {
  'use strict';

  let overlayShown = false;

  /**
   * Sleep helper
   * @param {number} ms - Milliseconds
   * @returns {Promise}
   */
  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Thêm và điền thành phần theo dịch vụ
   * @returns {Promise}
   */
  async function addAndFillComponent() {
    try {
      // Lấy thông tin dịch vụ hiện tại
      const serviceInfo = URL_SCANNER.getCurrentServiceInfo();
      const componentContent = URL_SCANNER.getComponentContentForCurrentService();
      
      console.log('[ComponentWorkflow] Service info:', serviceInfo);
      console.log('[ComponentWorkflow] Component content:', componentContent);

      // Step 1: Tìm và click "Thêm 1 thành phần" button
      console.log('[ComponentWorkflow] Step 1: Looking for "Thêm 1 thành phần" button...');
      const addButton = Array.from(document.querySelectorAll('button')).find(btn =>
        btn.textContent.trim().includes('Thêm 1 thành phần')
      );

      if (!addButton) {
        console.warn('[ComponentWorkflow] ⚠️ "Thêm 1 thành phần" button not found, showing overlay directly');
        OVERLAY_HANDLER.showUploadOverlay();
        return;
      }

      console.log('[ComponentWorkflow] Found "Thêm 1 thành phần" button, clicking...');
      addButton.click();

      // Chờ Angular render row mới
      console.log('[ComponentWorkflow] Waiting for new row to render...');
      await sleep(1500);

      // Step 2: Điền nội dung cho thành phần đầu tiên
      console.log('[ComponentWorkflow] Step 2: Finding target input in new row...');

      // Tìm row cuối cùng
      let lastRow = document.querySelector('table tbody tr:last-child') ||
                    document.querySelector('mat-table tr:last-child') ||
                    document.querySelector('.mat-mdc-table tbody tr:last-child') ||
                    document.querySelector('.mat-table tbody tr:last-child');

      if (!lastRow) {
        console.warn('[ComponentWorkflow] ⚠️ No table row found.');
        OVERLAY_HANDLER.showUploadOverlay();
        return;
      }

      console.log('[ComponentWorkflow] Found last row. Searching for input...');

      // Strategy A: Tìm input trong cột thứ 2 (Thành phần hồ sơ)
      let targetInput = lastRow.querySelector('td:nth-child(2) input.mat-mdc-input-element, td:nth-child(2) input.mat-input-element, td:nth-child(2) input');

      // Strategy B: Tìm ANY mat-form-field input trong row cuối
      if (!targetInput) {
        const formFields = lastRow.querySelectorAll('mat-form-field, .mat-mdc-form-field');
        if (formFields.length > 0) {
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
        console.warn('[ComponentWorkflow] ⚠️ Target input not found in last row.');
        OVERLAY_HANDLER.showUploadOverlay();
        return;
      }

      console.log('[ComponentWorkflow] ✅ Found target input:', targetInput);
      FORM_FILLER.fillField(targetInput, componentContent.firstComponent, 'text');

      // Step 3: Nếu là chứng thực chữ ký, thêm thành phần thứ 2
      // if (componentContent.isSignatureCertification && componentContent.secondComponent) {
      //   console.log('[ComponentWorkflow] Signature certification detected, adding second component...');
        
      //   // Chờ 1 giây rồi thêm thành phần thứ 2
      //   await sleep(1000);
        
      //   // Click thêm thành phần lần nữa
      //   addButton.click();
      //   await sleep(1500);
        
      //   // Tìm row mới nhất
      //   lastRow = document.querySelector('table tbody tr:last-child') ||
      //             document.querySelector('mat-table tr:last-child') ||
      //             document.querySelector('.mat-mdc-table tbody tr:last-child') ||
      //             document.querySelector('.mat-table tbody tr:last-child');
        
      //   if (lastRow) {
      //     // Tìm input trong row mới
      //     let secondInput = lastRow.querySelector('td:nth-child(2) input.mat-mdc-input-element, td:nth-child(2) input.mat-input-element, td:nth-child(2) input');
          
      //     if (!secondInput) {
      //       const formFields = lastRow.querySelectorAll('mat-form-field, .mat-mdc-form-field');
      //       for (const field of formFields) {
      //         const input = field.querySelector('input');
      //         if (input && input.type !== 'hidden') {
      //           secondInput = input;
      //           break;
      //         }
      //       }
      //     }
          
      //     if (secondInput) {
      //       console.log('[ComponentWorkflow] ✅ Found second target input:', secondInput);
      //       FORM_FILLER.fillField(secondInput, componentContent.secondComponent, 'text');
      //     }
      //   }
      // }

      // Step 4: Chờ 1.5s rồi hiển thị overlay upload
      console.log('[ComponentWorkflow] Step 4: Waiting 1.5s before showing upload overlay...');
      await sleep(1500);

      console.log('[ComponentWorkflow] Showing upload overlay...');
      OVERLAY_HANDLER.showUploadOverlay();

    } catch (error) {
      console.error('[ComponentWorkflow] ❌ Error in addAndFillComponent:', error);
      OVERLAY_HANDLER.showUploadOverlay();
    }
  }

  /**
   * Kiểm tra và xử lý workflow sau khi dialog đóng
   */
  function handlePostDialogWorkflow() {
    // Kiểm tra xem có dialog citizen không
    const dlg = document.querySelector('#citizenInfoModal');
    const ttl = document.querySelector('#citizenInfoModalLabel, .modal-title');
    const hasCitizenDialog = dlg || (ttl && ttl.textContent.includes('Cập nhật thông tin cá nhân'));
    
    if (!hasCitizenDialog && !overlayShown) {
      console.log('[ComponentWorkflow] No citizen dialog after dialog close - starting component workflow');
      setTimeout(() => {
        addAndFillComponent();
      }, 500);
    }
  }

  /**
   * Kiểm tra và xử lý workflow chính
   */
  async function checkAndStartWorkflow() {
    // Kiểm tra dialog citizen
    const citizenDialog = document.querySelector('#citizenInfoModal');
    const titleEl = document.querySelector('#citizenInfoModalLabel, .modal-title');
    const hasCitizenTitle = titleEl && titleEl.textContent.includes('Cập nhật thông tin cá nhân');

    if (citizenDialog || hasCitizenTitle) {
      console.log('[ComponentWorkflow] 🎯 Citizen info dialog detected - filling dialog');
      setTimeout(() => {
        const dialogContainer = citizenDialog || document.querySelector('mat-dialog-container') || document.querySelector('[role="dialog"]');
        if (dialogContainer) DIALOG_HANDLER.fillDialog(dialogContainer);
      }, 800);
      return;
    }

    // Không có dialog → Workflow mới: Thêm thành phần → Điền nội dung → Upload overlay
    console.log('[ComponentWorkflow] No citizen dialog detected, starting new component workflow...');
    setTimeout(async () => {
      const dlg = document.querySelector('#citizenInfoModal');
      const ttl = document.querySelector('#citizenInfoModalLabel, .modal-title');
      if (dlg || (ttl && ttl.textContent.includes('Cập nhật thông tin cá nhân'))) {
        console.log('[ComponentWorkflow] Citizen dialog appeared after delay');
      } else if (!overlayShown) {
        console.log('[ComponentWorkflow] No citizen dialog after 3s - starting component workflow');
        await addAndFillComponent();
      }
    }, 3000);
  }

  /**
   * Đặt trạng thái overlay
   * @param {boolean} shown
   */
  function setOverlayShown(shown) {
    overlayShown = shown;
  }

  /**
   * Lấy trạng thái overlay
   * @returns {boolean}
   */
  function getOverlayShown() {
    return overlayShown;
  }

  return {
    // Functions
    addAndFillComponent,
    handlePostDialogWorkflow,
    checkAndStartWorkflow,
    
    // Getters/Setters
    setOverlayShown,
    getOverlayShown
  };
})();