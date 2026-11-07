/// 法务文档版本与展示常量（R-03）。
///
/// 版本号须与后端 `backend/app/legal/__init__.py` 保持一致；升高版本会触发 App 端重新征求同意。
const String kLegalPrivacyVersion = '2026.11.06';
const String kLegalTermsVersion = '2026.11.07';

const String kLegalPrivacyTitle = '隐私政策';
const String kLegalTermsTitle = '用户协议';
const String kLegalSupportEmail = 'support@ailearning.cn';

/// 首启同意在本地存储中的键（值为已同意的隐私政策版本）。
const String kLegalConsentStorageKey = 'legal_consent_version';
