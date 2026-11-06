import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/models/practice_session.dart';
import 'package:ai_learning/core/services/api_client.dart';

class LearnService {
  LearnService(this._api);

  final ApiClient _api;

  /// 章 → 知识点树（带个人掌握度）。
  Future<List<ChapterTree>> knowledgeTree(int textbookId) async {
    final data = await _api.getList(
      '/api/learn/knowledge-tree',
      query: {'textbook_id': textbookId},
    );
    return data
        .map((item) => ChapterTree.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 自适应组卷：可按知识点 / 章节 / 学科限定范围，自动插入到期错题。
  Future<List<Question>> start({
    int? chapterId,
    int? knowledgePointId,
    String? subject,
    int count = 10,
  }) async {
    final data = await _api.postJson('/api/learn/start', {
      'chapter_id': chapterId,
      'knowledge_point_id': knowledgePointId,
      'subject': subject,
      'count': count,
    });
    final questions = data['questions'] as List<dynamic>? ?? const [];
    return questions
        .map((item) => Question.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 提交作答：判题 + 掌握度回写 + 错题本调度。
  Future<LearnSubmitResult> submit({
    required int questionId,
    required Map<String, dynamic> userAnswer,
    int durationMs = 0,
    int? sessionId,
    String source = 'practice',
  }) async {
    final data = await _api.postJson('/api/learn/submit', {
      'question_id': questionId,
      'user_answer': userAnswer,
      'duration_ms': durationMs,
      'session_id': sessionId,
      'source': source,
    });
    return LearnSubmitResult.fromJson(data);
  }

  /// 智能练习组卷预览（P0-21）。
  Future<PracticePreview> practicePreview({
    required String scopeType,
    List<int> scopeIds = const [],
    int count = 10,
    List<String> qTypes = const [],
    String mode = 'special',
    int? seed,
  }) async {
    final data = await _api.postJson('/api/learn/practice/preview', {
      'scope_type': scopeType,
      'scope_ids': scopeIds,
      'count': count,
      'q_types': qTypes,
      'mode': mode,
      'seed': seed,
    });
    return PracticePreview.fromJson(data);
  }

  /// 按预览参数开始练习（同一 seed 保证预览=实际），返回会话 ID。
  Future<PracticeStartResult> startPractice({
    required String scopeType,
    List<int> scopeIds = const [],
    int count = 10,
    List<String> qTypes = const [],
    String mode = 'special',
    int? seed,
    bool confirmMismatch = false,
  }) async {
    final data = await _api.postJson('/api/learn/start', {
      'scope_type': scopeType,
      'scope_ids': scopeIds,
      'count': count,
      'q_types': qTypes,
      'mode': mode,
      'seed': seed,
      'confirm_mismatch': confirmMismatch,
    });
    return PracticeStartResult.fromJson(data);
  }

  /// 断点续答：会话题目、已答状态与下一题下标。
  Future<PracticeSessionData> sessionDetail(int sessionId) async {
    final data = await _api.getJson('/api/learn/sessions/$sessionId');
    return PracticeSessionData.fromJson(data);
  }

  /// 结算：正确率、用时、知识点表现与错题数（幂等）。
  Future<PracticeFinish> finishSession(int sessionId) async {
    final data = await _api.postJson(
      '/api/learn/sessions/$sessionId/finish',
      const {},
    );
    return PracticeFinish.fromJson(data);
  }

  /// 错题本列表（active 待消灭 / mastered 已消灭）。
  Future<List<WrongQuestionItem>> wrongQuestions({
    String status = 'active',
    String? subject,
  }) async {
    final data = await _api.getList(
      '/api/learn/wrong-questions',
      query: {
        'status': status,
        'subject': ?subject,
      },
    );
    return data
        .map((item) => WrongQuestionItem.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 标注错因。
  Future<WrongQuestionItem> tagReason(int wrongId, String reason) async {
    final data = await _api.postJson(
      '/api/learn/wrong-questions/$wrongId/reason',
      {'wrong_reason': reason},
    );
    return WrongQuestionItem.fromJson(data);
  }

  /// 今日到期的复习题（SM-2 调度）。
  Future<List<Question>> reviewToday() async {
    final data = await _api.getJson('/api/learn/review/today');
    final questions = data['questions'] as List<dynamic>? ?? const [];
    return questions
        .map((item) => Question.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 学习首页聚合（仅学生；非学生返回 403 NOT_STUDENT）。
  Future<HomeData> home() async {
    final data = await _api.getJson('/api/learn/home');
    return HomeData.fromJson(data);
  }

  /// 学情总览。
  Future<LearnStats> stats() async {
    final data = await _api.getJson('/api/learn/stats');
    return LearnStats.fromJson(data);
  }

  /// 教材单元目录（D-04 §6.2）。
  Future<List<UnitSummary>> units(int textbookId) async {
    final data = await _api.getList('/api/learn/textbook/$textbookId/units');
    return data
        .map((item) => UnitSummary.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 单元详情：节与知识点。
  Future<UnitDetail> unitDetail(int chapterId) async {
    final data = await _api.getJson('/api/learn/unit/$chapterId');
    return UnitDetail.fromJson(data);
  }

  /// 知识点详情：讲解、前置、掌握度与状态。
  Future<KpDetail> kpDetail(int kpId) async {
    final data = await _api.getJson('/api/learn/kp/$kpId');
    return KpDetail.fromJson(data);
  }

  /// 知识点例题（最多 2 道，带解析）。
  Future<List<KpExample>> kpExamples(int kpId) async {
    final data = await _api.getList('/api/learn/kp/$kpId/examples');
    return data
        .map((item) => KpExample.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 阅读讲解：未学习 → 学习中。
  Future<String> markKpRead(int kpId) async {
    final data = await _api.postJson('/api/learn/kp/$kpId/read', const {});
    return data['state'] as String? ?? '学习中';
  }
}
