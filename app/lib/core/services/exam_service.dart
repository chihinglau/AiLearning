import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/services/api_client.dart';

class ExamService {
  ExamService(this._api);

  final ApiClient _api;

  Future<List<ExamSummary>> list({String? type, String? status}) async {
    final query = <String>[
      if (type != null && type.isNotEmpty) 'type=$type',
      if (status != null && status.isNotEmpty) 'status=$status',
    ];
    final path = query.isEmpty ? '/api/exams' : '/api/exams?${query.join('&')}';
    final data = await _api.getList(path);
    return data
        .map((item) => ExamSummary.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<ExamAttempt> startAttempt(int examId) async {
    final data = await _api.postJson('/api/exams/$examId/attempts', const {});
    return ExamAttempt.fromJson(data);
  }

  Future<ExamSaveResult> saveAnswers(
    int attemptId,
    List<Map<String, dynamic>> answers,
  ) async {
    final data = await _api.patchJson(
      '/api/exams/attempts/$attemptId',
      {'answers': answers},
    );
    return ExamSaveResult.fromJson(data);
  }

  Future<ExamSubmitResult> submit(
    int attemptId, {
    required String submitToken,
    List<Map<String, dynamic>> answers = const [],
    int? durationMs,
  }) async {
    final data = await _api.postJson(
      '/api/exams/attempts/$attemptId/submit',
      {
        'submit_token': submitToken,
        'answers': answers,
        'duration_ms': durationMs,
      },
    );
    return ExamSubmitResult.fromJson(data);
  }

  Future<ExamReport> report(int attemptId) async {
    final data =
        await _api.getJson('/api/exams/attempts/$attemptId/report');
    return ExamReport.fromJson(data);
  }
}
