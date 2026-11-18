import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/services/api_client.dart';

class ExamService {
  ExamService(this._api);

  final ApiClient _api;

  /// 考试中心（D-09 §4.3）：所有筛选下推服务端，未传参数时与 CR-003 行为一致。
  Future<List<ExamSummary>> list({
    String? type,
    String? status,
    String? subject,
    String? windowState,
    String? query,
    int? page,
    int? pageSize,
  }) async {
    final params = <String, String>{
      if (type != null && type.isNotEmpty) 'type': type,
      if (status != null && status.isNotEmpty) 'status': status,
      if (subject != null && subject.isNotEmpty) 'subject': subject,
      if (windowState != null && windowState.isNotEmpty)
        'window_state': windowState,
      if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      if (page != null) 'page': '$page',
      if (pageSize != null) 'page_size': '$pageSize',
    };
    final uri = Uri(path: '/api/exams', queryParameters: params);
    final data = await _api.getList(uri.toString());
    return data
        .map((item) => ExamSummary.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<ExamAttempt> startAttempt(int examId) async {
    final data = await _api.postJson('/api/exams/$examId/attempts', const {});
    return ExamAttempt.fromJson(data);
  }

  /// 真题库（D-09 §5.3）：年份/学科/地区/类型/状态全部服务端过滤。
  Future<List<ExamSummary>> pastPapers({
    String? subject,
    int? year,
    String? region,
    int? grade,
    String? examType,
    String? attemptStatus,
    String? query,
    int? page,
    int? pageSize,
  }) async {
    final params = <String, String>{
      if (subject != null && subject.isNotEmpty) 'subject': subject,
      if (year != null) 'year': '$year',
      if (region != null && region.isNotEmpty) 'region': region,
      if (grade != null) 'grade': '$grade',
      if (examType != null && examType.isNotEmpty) 'exam_type': examType,
      if (attemptStatus != null && attemptStatus.isNotEmpty)
        'attempt_status': attemptStatus,
      if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      if (page != null) 'page': '$page',
      if (pageSize != null) 'page_size': '$pageSize',
    };
    final uri = Uri(path: '/api/exams/past-papers', queryParameters: params);
    final data = await _api.getList(uri.toString());
    return data
        .map((item) => ExamSummary.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 真题库筛选项：年份/学科/地区/年级/类型由服务端下发（D-09 §5.3）。
  Future<PastPaperFilters> pastPaperFilters() async {
    final data = await _api.getJson('/api/exams/past-papers/filters');
    return PastPaperFilters.fromJson(data);
  }

  /// 真题详情/预览：不含答案，含完整溯源（D-09 §5.5）。
  Future<PastPaperDetail> pastPaperDetail(int id) async {
    final data = await _api.getJson('/api/exams/past-papers/$id');
    return PastPaperDetail.fromJson(data);
  }

  /// 本人历次作答（D-09 §4.7 报告历史）。
  Future<List<ExamAttemptHistory>> attemptHistory({
    int? examId,
    int? page,
    int? pageSize,
  }) async {
    final params = <String, String>{
      if (examId != null) 'exam_id': '$examId',
      if (page != null) 'page': '$page',
      if (pageSize != null) 'page_size': '$pageSize',
    };
    final uri = Uri(path: '/api/exams/attempts', queryParameters: params);
    final data = await _api.getList(uri.toString());
    return data
        .map((item) => ExamAttemptHistory.fromJson(item as Map<String, dynamic>))
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
    int? year,
    String? region,
    String? sourceName,
    String? licenseNote,
    String? adaptedFrom,
  }) async {
    final data = await _api.postJson('/api/exams/generate', {
      'blueprint_code': blueprintCode,
      'chapter_ids': chapterIds,
      'title': ?title,
      'seed': ?seed,
      'is_past_paper': isPastPaper,
      'year': ?year,
      'region': ?region,
      'source_name': ?sourceName,
      'license_note': ?licenseNote,
      'adapted_from': ?adaptedFrom,
    });
    return ExamGenerateResult.fromJson(data);
  }

  /// EX-09：真题草稿提交复核（content:exam:write），返回新状态。
  Future<String> submitForReview(int examId, {String? note}) async {
    final data = await _api.postJson('/api/exams/$examId/submit-review', {
      if (note != null && note.trim().isNotEmpty) 'note': note.trim(),
    });
    return data['status'] as String? ?? 'pending_review';
  }

  /// EX-09：审核队列（content:review:decide），默认只列待复核真题。
  Future<List<ExamReviewItem>> listReviews({
    String status = 'pending_review',
  }) async {
    final uri = Uri(
      path: '/api/exams/reviews',
      queryParameters: {'review_status': status},
    );
    final data = await _api.getList(uri.toString());
    return data
        .map((item) => ExamReviewItem.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// EX-09：审核决策 approve / reject / offline，返回新状态。
  Future<String> reviewExam(
    int examId,
    String decision, {
    String? note,
  }) async {
    final data = await _api.postJson('/api/exams/$examId/review', {
      'decision': decision,
      if (note != null && note.trim().isNotEmpty) 'note': note.trim(),
    });
    return data['status'] as String? ?? '';
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

  /// 占用一次听力材料播放额度（CR-008）。
  ///
  /// 返回本次播放后剩余次数；超出上限时抛出，`code = LISTENING_PLAY_LIMIT`。
  /// 听力音频命中本地缓存时也必须先调本接口，否则重播不受限。
  Future<int> takeListeningPlay(int attemptId, int questionId) async {
    final data = await _api.postJson(
      '/api/exams/attempts/$attemptId/listening-plays?question_id=$questionId',
      const {},
    );
    final remaining = data['remaining'];
    return remaining is int ? remaining : 0;
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

  /// 双向细目表（PG-05）：计划 vs 实际逐节对照。
  Future<List<ExamSpecRow>> specTable(int examId) async {
    final data = await _api.getJson('/api/exams/$examId/spec-table');
    final rows = data['sections'] ?? data['rows'];
    if (rows is! List) return const [];
    return rows
        .whereType<Map>()
        .map((item) => ExamSpecRow.fromJson(Map<String, dynamic>.from(item)))
        .toList(growable: false);
  }

  /// A4 打印版答题卡（HTML，不含题干与答案）。
  Future<String> answerSheetHtml(int examId) =>
      _api.getText('/api/exams/$examId/answer-sheet');
}
