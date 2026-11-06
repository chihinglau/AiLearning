import 'package:ai_learning/core/models/family.dart';
import 'package:ai_learning/core/services/api_client.dart';

class FamilyService {
  FamilyService(this._api);

  final ApiClient _api;

  /// 已生效绑定的孩子列表（含家长控制项）。
  Future<List<FamilyChild>> children() async {
    final data = await _api.getList('/api/family/children');
    return data
        .map((item) => FamilyChild.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 设置每日时长（分钟，0 表示不限）与青少年模式。
  Future<FamilyChild> updateControls(
    int childId, {
    int? dailyLimitMinutes,
    bool? teenMode,
  }) async {
    final data = await _api.putJson(
      '/api/family/children/$childId/controls',
      {
        'daily_limit_minutes': ?dailyLimitMinutes,
        'teen_mode': ?teenMode,
      },
    );
    return FamilyChild.fromJson(data);
  }
}
