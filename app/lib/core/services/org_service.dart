import 'package:ai_learning/core/models/org.dart';
import 'package:ai_learning/core/services/api_client.dart';

class OrgService {
  OrgService(this._api);

  final ApiClient _api;

  /// 教师可查看的班级（班主任全班 + 授课班；校管为本校班级）。
  Future<List<ClassSummary>> classes() async {
    final data = await _api.getList('/api/org/classes');
    return data
        .map((item) => ClassSummary.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 班级学情聚合值，可按学科收窄。
  Future<ClassStats> classStats(int classId, {String? subject}) async {
    final data = await _api.getJson(
      '/api/org/classes/$classId/stats',
      query: {'subject': ?subject},
    );
    return ClassStats.fromJson(data);
  }
}
