import 'package:ai_learning/core/models/usage.dart';
import 'package:ai_learning/core/services/api_client.dart';

/// 合规自助能力（R-04）：今日时长、数据导出、账号注销。
class ComplianceService {
  ComplianceService(this._api);

  final ApiClient _api;

  Future<DailyUsage> usage() async {
    return DailyUsage.fromJson(await _api.getJson('/api/users/me/usage'));
  }

  /// 导出当前账号数据（最小可用版，返回脱敏后的完整 JSON）。
  Future<Map<String, dynamic>> exportMyData() async {
    return _api.getJson('/api/data/export');
  }

  /// 注销账号：立即停用并匿名化，15 个工作日内完成删除或匿名化。
  Future<Map<String, dynamic>> requestDeletion({String? reason}) async {
    final body = <String, dynamic>{'confirm': true};
    if (reason != null && reason.trim().isNotEmpty) {
      body['reason'] = reason.trim();
    }
    return _api.deleteJson('/api/users/me', body: body);
  }
}
