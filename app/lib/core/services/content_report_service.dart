import 'package:ai_learning/core/services/api_client.dart';

/// R-07：内容举报提交（题目/教材/其他）。
class ContentReportService {
  ContentReportService(this._client);

  final ApiClient _client;

  Future<void> submit({
    required String targetType,
    int? targetId,
    required String reason,
    String? description,
  }) async {
    final body = <String, dynamic>{
      'target_type': targetType,
      'reason': reason,
    };
    if (targetId != null) body['target_id'] = targetId;
    final detail = description?.trim() ?? '';
    if (detail.isNotEmpty) body['description'] = detail;
    await _client.postJson('/api/content/reports', body);
  }
}
