import 'package:ai_learning/core/models/content.dart';

/// 组卷预览（POST /learn/practice/preview）。
class PracticePreview {
  const PracticePreview({
    required this.count,
    required this.available,
    required this.insufficient,
    required this.estimatedMinutes,
    required this.kpCoverage,
    required this.coveredKpCount,
    required this.rangeKpCount,
    required this.qTypeMix,
    required this.dueReviewCount,
    required this.seed,
    this.mode = 'special',
    this.modeLabel = '',
    this.strategy = '',
  });

  final int count;
  final int available;
  final bool insufficient;
  final int estimatedMinutes;
  final double kpCoverage;
  final int coveredKpCount;
  final int rangeKpCount;
  final Map<String, int> qTypeMix;
  final int dueReviewCount;
  final int seed;
  final String mode;
  final String modeLabel;
  final String strategy;

  factory PracticePreview.fromJson(Map<String, dynamic> json) {
    // 兼容接口 JSON 与本地构造的 Map（字面量可能是 Map<dynamic, dynamic>）。
    final mix = <String, int>{};
    final rawMix = json['q_type_mix'];
    if (rawMix is Map) {
      rawMix.forEach((key, value) {
        mix[key.toString()] = value as int? ?? 0;
      });
    }
    return PracticePreview(
      count: json['count'] as int? ?? 0,
      available: json['available'] as int? ?? 0,
      insufficient: json['insufficient'] as bool? ?? false,
      estimatedMinutes: json['estimated_minutes'] as int? ?? 0,
      kpCoverage: (json['kp_coverage'] as num?)?.toDouble() ?? 0,
      coveredKpCount: json['covered_kp_count'] as int? ?? 0,
      rangeKpCount: json['range_kp_count'] as int? ?? 0,
      qTypeMix: mix,
      dueReviewCount: json['due_review_count'] as int? ?? 0,
      seed: json['seed'] as int? ?? 0,
      mode: json['mode'] as String? ?? 'special',
      modeLabel: json['mode_label'] as String? ?? '',
      strategy: json['strategy'] as String? ?? '',
    );
  }
}

/// 开始练习返回（POST /learn/start）。
class PracticeStartResult {
  const PracticeStartResult({
    required this.questions,
    this.seed,
    this.sessionId,
  });

  final List<Question> questions;
  final int? seed;
  final int? sessionId;

  factory PracticeStartResult.fromJson(Map<String, dynamic> json) {
    return PracticeStartResult(
      questions: (json['questions'] as List<dynamic>? ?? const [])
          .map((item) => Question.fromJson(item as Map<String, dynamic>))
          .toList(),
      seed: json['seed'] as int?,
      sessionId: json['session_id'] as int?,
    );
  }
}

/// 练习会话（GET /learn/sessions/{id}）。
class PracticeSessionData {
  const PracticeSessionData({
    required this.id,
    required this.mode,
    required this.scopeType,
    required this.scopeIds,
    required this.seed,
    required this.totalCount,
    required this.answeredCount,
    required this.correctCount,
    required this.startedAt,
    this.finishedAt,
    this.questions = const [],
    this.answers = const [],
    required this.nextIndex,
  });

  final int id;
  final String mode;
  final String scopeType;
  final List<int> scopeIds;
  final int seed;
  final int totalCount;
  final int answeredCount;
  final int correctCount;
  final DateTime startedAt;
  final DateTime? finishedAt;
  final List<Question> questions;
  final List<SessionAnswer> answers;
  final int nextIndex;

  factory PracticeSessionData.fromJson(Map<String, dynamic> json) {
    return PracticeSessionData(
      id: json['id'] as int? ?? 0,
      mode: json['mode'] as String? ?? 'special',
      scopeType: json['scope_type'] as String? ?? '',
      scopeIds: (json['scope_ids'] as List<dynamic>? ?? const [])
          .map((item) => item as int)
          .toList(),
      seed: json['seed'] as int? ?? 0,
      totalCount: json['total_count'] as int? ?? 0,
      answeredCount: json['answered_count'] as int? ?? 0,
      correctCount: json['correct_count'] as int? ?? 0,
      startedAt:
          DateTime.tryParse(json['started_at'] as String? ?? '') ?? DateTime.now(),
      finishedAt: DateTime.tryParse(json['finished_at'] as String? ?? ''),
      questions: (json['questions'] as List<dynamic>? ?? const [])
          .map((item) => Question.fromJson(item as Map<String, dynamic>))
          .toList(),
      answers: (json['answers'] as List<dynamic>? ?? const [])
          .map((item) => SessionAnswer.fromJson(item as Map<String, dynamic>))
          .toList(),
      nextIndex: json['next_index'] as int? ?? 0,
    );
  }
}

class SessionAnswer {
  const SessionAnswer({
    required this.questionId,
    this.answered = false,
    this.isCorrect,
    this.userAnswer,
  });

  final int questionId;
  final bool answered;
  final bool? isCorrect;
  final Map<String, dynamic>? userAnswer;

  factory SessionAnswer.fromJson(Map<String, dynamic> json) {
    return SessionAnswer(
      questionId: json['question_id'] as int? ?? 0,
      answered: json['answered'] as bool? ?? false,
      isCorrect: json['is_correct'] as bool?,
      userAnswer: json['user_answer'] as Map<String, dynamic>?,
    );
  }
}

/// 练习结算（POST /learn/sessions/{id}/finish）。
class PracticeFinish {
  const PracticeFinish({
    required this.session,
    required this.accuracy,
    required this.durationMs,
    required this.wrongCount,
    this.kpStats = const [],
    this.nextActions = const [],
  });

  final PracticeSessionData session;
  final double accuracy;
  final int durationMs;
  final int wrongCount;
  final List<SessionKpStat> kpStats;
  final List<String> nextActions;

  factory PracticeFinish.fromJson(Map<String, dynamic> json) {
    final session = json['session'] as Map<String, dynamic>? ?? const {};
    final actions = json['next_actions'];
    return PracticeFinish(
      session: PracticeSessionData.fromJson(session),
      accuracy: (json['accuracy'] as num?)?.toDouble() ?? 0,
      durationMs: json['duration_ms'] as int? ?? 0,
      wrongCount: json['wrong_count'] as int? ?? 0,
      kpStats: (json['kp_stats'] as List<dynamic>? ?? const [])
          .map((item) => SessionKpStat.fromJson(item as Map<String, dynamic>))
          .toList(),
      nextActions: actions is List
          ? actions.map((item) => item.toString()).toList()
          : const [],
    );
  }
}

class SessionKpStat {
  const SessionKpStat({
    required this.knowledgePointId,
    required this.name,
    required this.answered,
    required this.correct,
    required this.accuracy,
    required this.masteryScore,
  });

  final int knowledgePointId;
  final String name;
  final int answered;
  final int correct;
  final double accuracy;
  final double masteryScore;

  factory SessionKpStat.fromJson(Map<String, dynamic> json) {
    return SessionKpStat(
      knowledgePointId: json['knowledge_point_id'] as int? ?? 0,
      name: json['name'] as String? ?? '',
      answered: json['answered'] as int? ?? 0,
      correct: json['correct'] as int? ?? 0,
      accuracy: (json['accuracy'] as num?)?.toDouble() ?? 0,
      masteryScore: (json['mastery_score'] as num?)?.toDouble() ?? 0,
    );
  }
}
