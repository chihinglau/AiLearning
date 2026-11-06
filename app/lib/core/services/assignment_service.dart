import 'package:ai_learning/core/models/assignment.dart';
import 'package:ai_learning/core/services/api_client.dart';

class AssignmentService {
  AssignmentService(this._api);

  final ApiClient _api;

  Future<List<AssignmentInfo>> list() async {
    final data = await _api.getList('/api/assignments');
    return data
        .map((item) => AssignmentInfo.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<AssignmentInfo> detail(int assignmentId) async {
    final data = await _api.getJson('/api/assignments/$assignmentId');
    return AssignmentInfo.fromJson(data);
  }

  Future<AssignmentInfo> create({
    required int classId,
    required String title,
    required String subject,
    required List<int> chapterIds,
    required int count,
    required List<String> qTypes,
    required int timeLimitMin,
    String? dueAt,
  }) async {
    final data = await _api.postJson('/api/assignments', {
      'class_id': classId,
      'title': title,
      'subject': subject,
      'chapter_ids': chapterIds,
      'count': count,
      'q_types': qTypes,
      'time_limit_min': timeLimitMin,
      'due_at': ?dueAt,
    });
    return AssignmentInfo.fromJson(data);
  }

  Future<GradingList> grading(int assignmentId) async {
    final data = await _api.getJson('/api/assignments/$assignmentId/grading');
    return GradingList.fromJson(data);
  }

  Future<GradeBatchResult> grade(
    int assignmentId,
    List<Map<String, dynamic>> items,
  ) async {
    final data = await _api.postJson(
      '/api/assignments/$assignmentId/grade',
      {'items': items},
    );
    return GradeBatchResult.fromJson(data);
  }
}
