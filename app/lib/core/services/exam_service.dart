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

  /// 真题库：按学科/年份/地区筛选已发布的历年真题。
  Future<List<ExamSummary>> pastPapers({
    String? subject,
    int? year,
    String? region,
  }) async {
    final query = <String>[
      if (subject != null && subject.isNotEmpty) 'subject=$subject',
      if (year != null) 'year=$year',
      if (region != null && region.isNotEmpty)
        'region=${Uri.encodeQueryComponent(region)}',
    ];
    final path = query.isEmpty
        ? '/api/exams/past-papers'
        : '/api/exams/past-papers?${query.join('&')}';
    final data = await _api.getList(path);
    return data
        .map((item) => ExamSummary.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 考试入库：可选组卷蓝图（需 content:exam:write）。
  Future<List<ExamBlueprint>> blueprints() async {
    final data = await _api.getList('/api/exams/blueprints');
    return data
        .map((item) => ExamBlueprint.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 考试入库：按蓝图在指定章节范围内组卷并发布。
  Future<ExamGenerateResult> generateExam({
    required String blueprintCode,
    required List<int> chapterIds,
    String? title,
    int? seed,
    bool isPastPaper = false,
  }) async {
    final data = await _api.postJson('/api/exams/generate', {
      'blueprint_code': blueprintCode,
      'chapter_ids': chapterIds,
      'title': ?title,
      'seed': ?seed,
      'is_past_paper': isPastPaper,
    });
    return ExamGenerateResult.fromJson(data);
  }

  /// 教师把一张真题/模考模板派发为班级同卷模考。
  Future<MockExamAssignment> assignClassMock({
    required int classId,
    required int examId,
    String? title,
    DateTime? windowStart,
    DateTime? windowEnd,
  }) async {
    final data = await _api.postJson('/api/exams/mock', {
      'class_id': classId,
      'exam_id': examId,
      'title': ?title,
      'window_start': ?windowStart?.toIso8601String(),
      'window_end': ?windowEnd?.toIso8601String(),
    });
    return MockExamAssignment.fromJson(data);
  }

  /// 开始/续答并返回原始 JSON，供离线整卷快照使用。
  Future<(ExamAttempt, Map<String, dynamic>)> startAttemptRaw(int examId) async {
    final data = await _api.postJson('/api/exams/$examId/attempts', const {});
    return (ExamAttempt.fromJson(data), data);
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

  /// 主观题自评：按题号提交 0~满分。
  Future<void> selfAssess(int attemptId, Map<int, double> scores) async {
    await _api.postJson('/api/exams/attempts/$attemptId/self-assess', {
      'items': [
        for (final entry in scores.entries)
          {'question_id': entry.key, 'score': entry.value},
      ],
    });
  }
}
