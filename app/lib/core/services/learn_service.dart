import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/learn.dart';
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
  }) async {
    final data = await _api.postJson('/api/learn/submit', {
      'question_id': questionId,
      'user_answer': userAnswer,
      'duration_ms': durationMs,
    });
    return LearnSubmitResult.fromJson(data);
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

  /// 学情总览。
  Future<LearnStats> stats() async {
    final data = await _api.getJson('/api/learn/stats');
    return LearnStats.fromJson(data);
  }
}
