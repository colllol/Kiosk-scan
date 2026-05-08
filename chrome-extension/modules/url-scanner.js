/**
 * URL Scanner Module
 * Xử lý quét URL và nhận diện mã dịch vụ
 */

const URL_SCANNER = (function() {
  'use strict';

  // Các pattern URL hợp lệ
  const VALID_URL_PATTERNS = [
    /https:\/\/dichvucong\.thainguyen\.gov\.vn\/nop-ho-so/,
    /file:\/\/.*form-replica\.html/,
    /file:\/\/.*\.html/,
    /http:\/\/localhost.*form/,
    /http:\/\/127\.0\.0\.1.*form/
  ];

  // Các mã dịch vụ cần xử lý
  const SERVICE_CODES = {
    DOCUMENT_CERTIFICATION: '2.000815.000.00.00.H55',  // Chứng thực tài liệu
    SIGNATURE_CERTIFICATION: '2.000884.000.00.00.H55'  // Chứng thực chữ ký
  };

  // Nội dung cho từng loại dịch vụ
  const SERVICE_CONTENT = {
    [SERVICE_CODES.DOCUMENT_CERTIFICATION]: {
      componentText: 'Chứng thực bản sao từ bản chính giấy tờ, văn bản do cơ quan, tổ chức có thẩm quyền của Việt Nam; cơ quan, tổ chức có thẩm quyền của nước ngoài; cơ quan, tổ chức có thẩm quyền của Việt Nam liên kết với cơ quan, tổ chức có thẩm quyền của nước ngoài cấp hoặc chứng nhận',
      description: 'Dịch vụ chứng thực tài liệu'
    },
    [SERVICE_CODES.SIGNATURE_CERTIFICATION]: {
      componentText: 'Thủ tục chứng thực chữ ký trong các giấy tờ, văn bản (áp dụng cho cả trường hợp chứng thực điểm chỉ và trường hợp người yêu cầu chứng thực không thể ký, không thể điểm chỉ được)',
      secondComponentText: 'Giấy tờ, văn bản mà mình sẽ yêu cầu chứng thực chữ ký. Trường hợp chứng thực chữ ký trong giấy tờ, văn bản bằng tiếng nước ngoài, nếu người thực hiện chứng thực không hiểu rõ nội dung của giấy tờ, văn bản thì có quyền yêu cầu người yêu cầu chứng thực nộp kèm theo bản dịch ra tiếng Việt nội dung của giấy tờ, văn bản đó (bản dịch không cần công chứng hoặc chứng thực chữ ký người dịch, người yêu cầu chứng thực phải chịu trách nhiệm về nội dung của bản dịch).',
      description: 'Dịch vụ chứng thực chữ ký'
    }
  };

  /**
   * Kiểm tra URL hiện tại có hợp lệ không
   * @returns {boolean}
   */
  function isValidPage() {
    const currentUrl = window.location.href;
    const hasValidUrl = VALID_URL_PATTERNS.some(p => p.test(currentUrl));
    const hasFormElements = document.querySelector('.form-section, .content-wrapper, .page-content, mat-form-field');
    
    return hasValidUrl && hasFormElements;
  }

  /**
   * Trích xuất mã dịch vụ từ URL
   * @returns {string|null} Mã dịch vụ hoặc null nếu không tìm thấy
   */
  function extractServiceCodeFromUrl() {
    const url = window.location.href;
    const urlParams = new URLSearchParams(window.location.search);
    
    // Kiểm tra tham số MaTTHCDP
    const maTTHCDP = urlParams.get('MaTTHCDP');
    if (maTTHCDP && Object.values(SERVICE_CODES).includes(maTTHCDP)) {
      return maTTHCDP;
    }
    
    // Kiểm tra trong URL string
    for (const code of Object.values(SERVICE_CODES)) {
      if (url.includes(code)) {
        return code;
      }
    }
    
    return null;
  }

  /**
   * Lấy thông tin dịch vụ dựa trên mã
   * @param {string} serviceCode - Mã dịch vụ
   * @returns {Object|null} Thông tin dịch vụ
   */
  function getServiceInfo(serviceCode) {
    if (!serviceCode || !SERVICE_CONTENT[serviceCode]) {
      return null;
    }
    
    return {
      code: serviceCode,
      ...SERVICE_CONTENT[serviceCode],
      isSignatureCertification: serviceCode === SERVICE_CODES.SIGNATURE_CERTIFICATION,
      isDocumentCertification: serviceCode === SERVICE_CODES.DOCUMENT_CERTIFICATION
    };
  }

  /**
   * Lấy thông tin dịch vụ cho URL hiện tại
   * @returns {Object|null}
   */
  function getCurrentServiceInfo() {
    const serviceCode = extractServiceCodeFromUrl();
    return getServiceInfo(serviceCode);
  }

  /**
   * Kiểm tra xem có phải trang chứng thực chữ ký không
   * @returns {boolean}
   */
  function isSignatureCertificationPage() {
    const serviceInfo = getCurrentServiceInfo();
    return serviceInfo && serviceInfo.isSignatureCertification;
  }

  /**
   * Kiểm tra xem có phải trang chứng thực tài liệu không
   * @returns {boolean}
   */
  function isDocumentCertificationPage() {
    const serviceInfo = getCurrentServiceInfo();
    return serviceInfo && serviceInfo.isDocumentCertification;
  }

  /**
   * Lấy nội dung cần điền cho dịch vụ hiện tại
   * @returns {Object} Nội dung cho component
   */
  function getComponentContentForCurrentService() {
    const serviceInfo = getCurrentServiceInfo();
    
    if (!serviceInfo) {
      // Mặc định cho chứng thực tài liệu
      return {
        firstComponent: SERVICE_CONTENT[SERVICE_CODES.DOCUMENT_CERTIFICATION].componentText,
        secondComponent: null,
        isSignatureCertification: false
      };
    }
    
    return {
      firstComponent: serviceInfo.componentText,
      secondComponent: serviceInfo.secondComponentText || null,
      isSignatureCertification: serviceInfo.isSignatureCertification
    };
  }

  return {
    // Constants
    SERVICE_CODES,
    SERVICE_CONTENT,
    
    // Functions
    isValidPage,
    extractServiceCodeFromUrl,
    getServiceInfo,
    getCurrentServiceInfo,
    isSignatureCertificationPage,
    isDocumentCertificationPage,
    getComponentContentForCurrentService
  };
})();