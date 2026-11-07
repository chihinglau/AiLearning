import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:ai_learning/core/constants/legal_constants.dart';

/// R-06：关于页展示的应用信息与备案号。
class AppInfo {
  const AppInfo({
    required this.name,
    required this.version,
    required this.icpRecordNo,
    required this.appRecordNo,
    required this.softwareCopyrightNo,
    required this.privacyUrl,
    required this.termsUrl,
    required this.supportEmail,
  });

  final String name;
  final String version;
  final String icpRecordNo;
  final String appRecordNo;
  final String softwareCopyrightNo;
  final String privacyUrl;
  final String termsUrl;
  final String supportEmail;

  /// 无网络或后端未配置时使用本地常量。
  factory AppInfo.fallback() {
    return const AppInfo(
      name: AppConfig.displayName,
      version: AppConfig.versionLabel,
      icpRecordNo: AppConfig.icpRecordNo,
      appRecordNo: AppConfig.appRecordNo,
      softwareCopyrightNo: AppConfig.softwareCopyrightNo,
      privacyUrl: '',
      termsUrl: '',
      supportEmail: kLegalSupportEmail,
    );
  }

  factory AppInfo.fromJson(Map<String, dynamic> json) {
    return AppInfo(
      name: json['name'] as String? ?? AppConfig.displayName,
      version: json['version'] as String? ?? AppConfig.versionLabel,
      icpRecordNo: json['icp_record_no'] as String? ?? '',
      appRecordNo: json['app_record_no'] as String? ?? '',
      softwareCopyrightNo: json['software_copyright_no'] as String? ?? '',
      privacyUrl: json['privacy_url'] as String? ?? '',
      termsUrl: json['terms_url'] as String? ?? '',
      supportEmail: json['support_email'] as String? ?? kLegalSupportEmail,
    );
  }
}
