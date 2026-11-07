import 'package:ai_learning/core/models/app_info.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('fromJson 解析备案信息', () {
    final info = AppInfo.fromJson({
      'name': '深爱学',
      'version': '1.0.0',
      'icp_record_no': '粤ICP备2026000000号-1',
      'app_record_no': '粤ICP备2026000000号-2A',
      'software_copyright_no': '2026SR0000000',
      'privacy_url': 'https://example.com/legal/privacy',
      'terms_url': 'https://example.com/legal/terms',
      'support_email': 'support@ailearning.cn',
    });
    expect(info.name, '深爱学');
    expect(info.icpRecordNo, '粤ICP备2026000000号-1');
    expect(info.appRecordNo, '粤ICP备2026000000号-2A');
    expect(info.softwareCopyrightNo, '2026SR0000000');
    expect(info.privacyUrl, endsWith('/legal/privacy'));
    expect(info.supportEmail, 'support@ailearning.cn');
  });

  test('字段缺失时回退默认值', () {
    final info = AppInfo.fromJson({});
    expect(info.name, '深爱学');
    expect(info.version, '1.0.0');
    expect(info.icpRecordNo, '');
    expect(info.appRecordNo, '');
    expect(info.supportEmail, 'support@ailearning.cn');
  });
}
