import 'package:ai_learning/core/constants/legal_constants.dart';
import 'package:ai_learning/core/models/legal.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/services.dart';

/// 法务文档读取与同意提交（R-03）。
///
/// 优先读取后端已发布内容，失败（如离线/首启）回退到 App 内置 Markdown。
class LegalService {
  LegalService(this._api);

  final ApiClient _api;

  Future<LegalDocument> fetch(String docType) async {
    try {
      final data = await _api.getJson('/api/legal/$docType');
      return LegalDocument.fromJson(data);
    } on ApiException {
      return loadBundled(docType);
    }
  }

  /// 读取 App 内置版本（首启同意阶段使用，不发起任何网络请求）。
  static Future<LegalDocument> loadBundled(String docType) async {
    final isPrivacy = docType == 'privacy';
    return LegalDocument(
      docType: docType,
      title: isPrivacy ? kLegalPrivacyTitle : kLegalTermsTitle,
      version: isPrivacy ? kLegalPrivacyVersion : kLegalTermsVersion,
      content: await rootBundle.loadString('assets/legal/$docType.md'),
    );
  }

  Future<void> accept({
    required String privacyVersion,
    required String termsVersion,
    bool guardianConfirmed = false,
  }) async {
    await _api.postJson('/api/legal/consent', {
      'privacy_version': privacyVersion,
      'terms_version': termsVersion,
      'guardian_confirmed': guardianConfirmed,
    });
  }
}
