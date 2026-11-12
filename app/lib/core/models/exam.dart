import 'package:ai_learning/core/models/content.dart';

/// 考试列表摘要（GET /exams）。
class ExamSummary {
  const ExamSummary({
    required this.id,
    required this.title,
    required this.subject,
    required this.grade,
    this.year,
    required this.examType,
    required this.totalScore,
    required this.timeLimitMin,
    required this.questionCount,
    required this.category,
    this.windowStart,
    this.windowEnd,
    this.windowState = 'unscheduled',
    this.region,
    this.isPastPaper = false,
    this.classId,
    this.attempt,
  });

  final int id;
  final String title;
  final String subject;
  final int grade;
  final int? year;
  final String examType;
  final int totalScore;
  final int timeLimitMin;
  final int questionCount;

  /// available | in_progress | completed
  final String category;
  final DateTime? windowStart;
  final DateTime? windowEnd;

  /// open | scheduled | closed | unscheduled
  final String windowState;

  /// P2-07 真题库与班级同卷模考
  final String? region;
  final bool isPastPaper;
  final int? classId;
  final ExamAttemptBrief? attempt;

  bool get windowOpen => windowState != 'scheduled' && windowState != 'closed';

  String get windowLabel {
    switch (windowState) {
      case 'scheduled':
        return '未到开放时间';
      case 'closed':
        return '已结束';
      case 'open':
        return '开放中';
      default:
        return '';
    }
  }

  String? get windowRange {
    if (windowStart == null && windowEnd == null) return null;
    final start = _formatTime(windowStart);
    final end = _formatTime(windowEnd);
    if (start != null && end != null) return '$start ~ $end';
    if (start != null) return '$start 起';
    return '截止 $end';
  }

  String get typeLabel {
    switch (examType) {
      case 'unit':
        return '单元测';
      case 'midterm':
        return '期中';
      case 'final':
        return '期末';
      case 'mock':
        return '模考';
      default:
        return '考试';
    }
  }

  factory ExamSummary.fromJson(Map<String, dynamic> json) {
    return ExamSummary(
      id: json['id'] as int? ?? 0,
      title: json['title'] as String? ?? '',
      subject: json['subject'] as String? ?? '',
      grade: json['grade'] as int? ?? 1,
      year: json['year'] as int?,
      examType: json['exam_type'] as String? ?? '',
      totalScore: json['total_score'] as int? ?? 0,
      timeLimitMin: json['time_limit_min'] as int? ?? 0,
      questionCount: json['question_count'] as int? ?? 0,
      category: json['category'] as String? ?? 'available',
      windowStart: DateTime.tryParse(json['window_start'] as String? ?? ''),
      windowEnd: DateTime.tryParse(json['window_end'] as String? ?? ''),
      windowState: json['window_state'] as String? ?? 'unscheduled',
      region: json['region'] as String?,
      isPastPaper: json['is_past_paper'] as bool? ?? false,
      classId: json['class_id'] as int?,
      attempt: json['attempt'] == null
          ? null
          : ExamAttemptBrief.fromJson(json['attempt'] as Map<String, dynamic>),
    );
  }

  static String? _formatTime(DateTime? value) {
    if (value == null) return null;
    final local = value.toLocal();
    String two(int number) => number.toString().padLeft(2, '0');
    return '${two(local.month)}-${two(local.day)} ${two(local.hour)}:${two(local.minute)}';
  }
}

class ExamAttemptBrief {
  const ExamAttemptBrief({
    required this.id,
    required this.status,
    required this.seed,
    required this.startedAt,
    this.submittedAt,
    this.durationMs = 0,
    this.objectiveScore = 0,
    this.subjectiveScore,
    this.totalScore,
    this.remainingSeconds = 0,
  });

  final int id;
  final String status;
  final int seed;
  final DateTime startedAt;
  final DateTime? submittedAt;
  final int durationMs;
  final double objectiveScore;
  final double? subjectiveScore;
  final double? totalScore;
  final int remainingSeconds;

  factory ExamAttemptBrief.fromJson(Map<String, dynamic> json) {
    return ExamAttemptBrief(
      id: json['id'] as int? ?? 0,
      status: json['status'] as String? ?? '',
      seed: json['seed'] as int? ?? 0,
      startedAt: DateTime.tryParse(json['started_at'] as String? ?? '') ??
          DateTime.now(),
      submittedAt: DateTime.tryParse(json['submitted_at'] as String? ?? ''),
      durationMs: json['duration_ms'] as int? ?? 0,
      objectiveScore: (json['objective_score'] as num?)?.toDouble() ?? 0,
      subjectiveScore: (json['subjective_score'] as num?)?.toDouble(),
      totalScore: (json['total_score'] as num?)?.toDouble(),
      remainingSeconds: json['remaining_seconds'] as int? ?? 0,
    );
  }
}

class ExamQuestion {
  const ExamQuestion({
    required this.question,
    this.score = 0,
    this.sectionIndex = 0,
    this.sectionName,
    this.orderIndex = 0,
  });

  final Question question;
  final double score;
  final int sectionIndex;
  final String? sectionName;
  final int orderIndex;

  factory ExamQuestion.fromJson(Map<String, dynamic> json) {
    return ExamQuestion(
      question: Question.fromJson(json),
      score: (json['score'] as num?)?.toDouble() ?? 0,
      sectionIndex: json['section_index'] as int? ?? 0,
      sectionName: json['section_name'] as String?,
      orderIndex: json['order_index'] as int? ?? 0,
    );
  }
}

class ExamDetail {
  const ExamDetail({
    required this.id,
    required this.title,
    required this.subject,
    required this.grade,
    this.year,
    required this.source,
    required this.examType,
    required this.totalScore,
    required this.timeLimitMin,
    required this.status,
    required this.questionCount,
    this.questions = const [],
  });

  final int id;
  final String title;
  final String subject;
  final int grade;
  final int? year;
  final String source;
  final String examType;
  final int totalScore;
  final int timeLimitMin;
  final String status;
  final int questionCount;
  final List<ExamQuestion> questions;

  factory ExamDetail.fromJson(Map<String, dynamic> json) {
    return ExamDetail(
      id: json['id'] as int? ?? 0,
      title: json['title'] as String? ?? '',
      subject: json['subject'] as String? ?? '',
      grade: json['grade'] as int? ?? 1,
      year: json['year'] as int?,
      source: json['source'] as String? ?? '',
      examType: json['exam_type'] as String? ?? '',
      totalScore: json['total_score'] as int? ?? 0,
      timeLimitMin: json['time_limit_min'] as int? ?? 0,
      status: json['status'] as String? ?? '',
      questionCount: json['question_count'] as int? ?? 0,
      questions: (json['questions'] as List<dynamic>? ?? const [])
          .map((item) => ExamQuestion.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class ExamAnswer {
  const ExamAnswer({
    required this.questionId,
    this.userAnswer,
    this.isCorrect,
    this.score,
    this.updatedAt,
  });

  final int questionId;
  final Map<String, dynamic>? userAnswer;
  final bool? isCorrect;
  final double? score;
  final DateTime? updatedAt;

  factory ExamAnswer.fromJson(Map<String, dynamic> json) {
    return ExamAnswer(
      questionId: json['question_id'] as int? ?? 0,
      userAnswer: json['user_answer'] as Map<String, dynamic>?,
      isCorrect: json['is_correct'] as bool?,
      score: (json['score'] as num?)?.toDouble(),
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? ''),
    );
  }
}

class ExamAttempt {
  const ExamAttempt({
    required this.id,
    required this.examId,
    required this.status,
    required this.seed,
    required this.startedAt,
    this.submittedAt,
    this.durationMs = 0,
    this.objectiveScore = 0,
    this.subjectiveScore,
    this.totalScore,
    this.submitToken,
    required this.remainingSeconds,
    required this.serverNow,
    required this.exam,
    this.answers = const [],
    this.nextIndex = 0,
  });

  final int id;
  final int examId;
  final String status;
  final int seed;
  final DateTime startedAt;
  final DateTime? submittedAt;
  final int durationMs;
  final double objectiveScore;
  final double? subjectiveScore;
  final double? totalScore;
  final String? submitToken;
  final int remainingSeconds;
  final DateTime serverNow;
  final ExamDetail exam;
  final List<ExamAnswer> answers;
  final int nextIndex;

  factory ExamAttempt.fromJson(Map<String, dynamic> json) {
    return ExamAttempt(
      id: json['id'] as int? ?? 0,
      examId: json['exam_id'] as int? ?? 0,
      status: json['status'] as String? ?? '',
      seed: json['seed'] as int? ?? 0,
      startedAt: DateTime.tryParse(json['started_at'] as String? ?? '') ??
          DateTime.now(),
      submittedAt: DateTime.tryParse(json['submitted_at'] as String? ?? ''),
      durationMs: json['duration_ms'] as int? ?? 0,
      objectiveScore: (json['objective_score'] as num?)?.toDouble() ?? 0,
      subjectiveScore: (json['subjective_score'] as num?)?.toDouble(),
      totalScore: (json['total_score'] as num?)?.toDouble(),
      submitToken: json['submit_token'] as String?,
      remainingSeconds: json['remaining_seconds'] as int? ?? 0,
      serverNow: DateTime.tryParse(json['server_now'] as String? ?? '') ??
          DateTime.now(),
      exam: ExamDetail.fromJson(json['exam'] as Map<String, dynamic>? ?? const {}),
      answers: (json['answers'] as List<dynamic>? ?? const [])
          .map((item) => ExamAnswer.fromJson(item as Map<String, dynamic>))
          .toList(),
      nextIndex: json['next_index'] as int? ?? 0,
    );
  }
}

class ExamSaveResult {
  const ExamSaveResult({
    required this.attemptId,
    required this.saved,
    required this.status,
    required this.remainingSeconds,
    this.answers = const [],
  });

  final int attemptId;
  final int saved;
  final String status;
  final int remainingSeconds;
  final List<ExamAnswer> answers;

  factory ExamSaveResult.fromJson(Map<String, dynamic> json) {
    return ExamSaveResult(
      attemptId: json['attempt_id'] as int? ?? 0,
      saved: json['saved'] as int? ?? 0,
      status: json['status'] as String? ?? '',
      remainingSeconds: json['remaining_seconds'] as int? ?? 0,
      answers: (json['answers'] as List<dynamic>? ?? const [])
          .map((item) => ExamAnswer.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class ExamSubmitResult {
  const ExamSubmitResult({
    required this.attemptId,
    required this.status,
    this.duplicate = false,
    this.objectiveScore = 0,
    this.subjectiveScore,
    this.totalScore,
    this.correctCount = 0,
    this.questionCount = 0,
    this.pendingGrading = false,
    this.submittedAt,
  });

  final int attemptId;
  final String status;
  final bool duplicate;
  final double objectiveScore;
  final double? subjectiveScore;
  final double? totalScore;
  final int correctCount;
  final int questionCount;
  final bool pendingGrading;
  final DateTime? submittedAt;

  factory ExamSubmitResult.fromJson(Map<String, dynamic> json) {
    return ExamSubmitResult(
      attemptId: json['attempt_id'] as int? ?? 0,
      status: json['status'] as String? ?? '',
      duplicate: json['duplicate'] as bool? ?? false,
      objectiveScore: (json['objective_score'] as num?)?.toDouble() ?? 0,
      subjectiveScore: (json['subjective_score'] as num?)?.toDouble(),
      totalScore: (json['total_score'] as num?)?.toDouble(),
      correctCount: json['correct_count'] as int? ?? 0,
      questionCount: json['question_count'] as int? ?? 0,
      pendingGrading: json['pending_grading'] as bool? ?? false,
      submittedAt: DateTime.tryParse(json['submitted_at'] as String? ?? ''),
    );
  }
}

/// 考试报告（GET /exams/attempts/{id}/report）。
class ExamReport {
  const ExamReport({
    required this.attemptId,
    required this.examId,
    required this.examTitle,
    required this.examType,
    required this.status,
    this.totalScore,
    required this.fullScore,
    this.objectiveScore = 0,
    this.subjectiveScore,
    this.correctCount = 0,
    this.questionCount = 0,
    this.answeredCount = 0,
    this.accuracy = 0,
    this.durationMs = 0,
    this.submittedAt,
    this.typeStats = const [],
    this.kpStats = const [],
    this.abilityStats = const [],
    this.classAverage = const ExamClassAverage(),
    this.trend = const ExamTrend(),
    this.wrongQuestions = const [],
    this.pendingSubjective = const [],
    this.nextActions = const [],
  });

  final int attemptId;
  final int examId;
  final String examTitle;
  final String examType;
  final String status;
  final double? totalScore;
  final double fullScore;
  final double objectiveScore;
  final double? subjectiveScore;
  final int correctCount;
  final int questionCount;
  final int answeredCount;
  final double accuracy;
  final int durationMs;
  final DateTime? submittedAt;
  final List<ExamTypeStat> typeStats;
  final List<ExamKpStat> kpStats;
  final List<ExamAbilityStat> abilityStats;
  final ExamClassAverage classAverage;
  final ExamTrend trend;
  final List<ExamWrongItem> wrongQuestions;
  final List<ExamSubjectiveQuestion> pendingSubjective;
  final List<ExamNextAction> nextActions;

  factory ExamReport.fromJson(Map<String, dynamic> json) {
    return ExamReport(
      attemptId: json['attempt_id'] as int? ?? 0,
      examId: json['exam_id'] as int? ?? 0,
      examTitle: json['exam_title'] as String? ?? '',
      examType: json['exam_type'] as String? ?? '',
      status: json['status'] as String? ?? '',
      totalScore: (json['total_score'] as num?)?.toDouble(),
      fullScore: (json['full_score'] as num?)?.toDouble() ?? 0,
      objectiveScore: (json['objective_score'] as num?)?.toDouble() ?? 0,
      subjectiveScore: (json['subjective_score'] as num?)?.toDouble(),
      correctCount: json['correct_count'] as int? ?? 0,
      questionCount: json['question_count'] as int? ?? 0,
      answeredCount: json['answered_count'] as int? ?? 0,
      accuracy: (json['accuracy'] as num?)?.toDouble() ?? 0,
      durationMs: json['duration_ms'] as int? ?? 0,
      submittedAt: DateTime.tryParse(json['submitted_at'] as String? ?? ''),
      typeStats: (json['type_stats'] as List<dynamic>? ?? const [])
          .map((item) => ExamTypeStat.fromJson(item as Map<String, dynamic>))
          .toList(),
      kpStats: (json['kp_stats'] as List<dynamic>? ?? const [])
          .map((item) => ExamKpStat.fromJson(item as Map<String, dynamic>))
          .toList(),
      abilityStats: (json['ability_stats'] as List<dynamic>? ?? const [])
          .map((item) => ExamAbilityStat.fromJson(item as Map<String, dynamic>))
          .toList(),
      classAverage: ExamClassAverage.fromJson(
        json['class_average'] as Map<String, dynamic>? ?? const {},
      ),
      trend: ExamTrend.fromJson(
        json['trend'] as Map<String, dynamic>? ?? const {},
      ),
      wrongQuestions: (json['wrong_questions'] as List<dynamic>? ?? const [])
          .map((item) => ExamWrongItem.fromJson(item as Map<String, dynamic>))
          .toList(),
      pendingSubjective:
          (json['pending_subjective'] as List<dynamic>? ?? const [])
              .map(
                (item) => ExamSubjectiveQuestion.fromJson(
                  item as Map<String, dynamic>,
                ),
              )
              .toList(),
      nextActions: (json['next_actions'] as List<dynamic>? ?? const [])
          .map((item) => ExamNextAction.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class ExamTypeStat {
  const ExamTypeStat({
    required this.qType,
    required this.questionCount,
    required this.answered,
    required this.correct,
    required this.score,
    required this.fullScore,
    required this.scoreRate,
  });

  final String qType;
  final int questionCount;
  final int answered;
  final int correct;
  final double score;
  final double fullScore;
  final double scoreRate;

  factory ExamTypeStat.fromJson(Map<String, dynamic> json) {
    return ExamTypeStat(
      qType: json['q_type'] as String? ?? '',
      questionCount: json['question_count'] as int? ?? 0,
      answered: json['answered'] as int? ?? 0,
      correct: json['correct'] as int? ?? 0,
      score: (json['score'] as num?)?.toDouble() ?? 0,
      fullScore: (json['full_score'] as num?)?.toDouble() ?? 0,
      scoreRate: (json['score_rate'] as num?)?.toDouble() ?? 0,
    );
  }
}

class ExamKpStat {
  const ExamKpStat({
    this.knowledgePointId,
    required this.name,
    required this.questionCount,
    required this.correct,
    required this.score,
    required this.fullScore,
    required this.scoreRate,
  });

  final int? knowledgePointId;
  final String name;
  final int questionCount;
  final int correct;
  final double score;
  final double fullScore;
  final double scoreRate;

  factory ExamKpStat.fromJson(Map<String, dynamic> json) {
    return ExamKpStat(
      knowledgePointId: json['knowledge_point_id'] as int?,
      name: json['name'] as String? ?? '',
      questionCount: json['question_count'] as int? ?? 0,
      correct: json['correct'] as int? ?? 0,
      score: (json['score'] as num?)?.toDouble() ?? 0,
      fullScore: (json['full_score'] as num?)?.toDouble() ?? 0,
      scoreRate: (json['score_rate'] as num?)?.toDouble() ?? 0,
    );
  }
}

class ExamAbilityStat {
  const ExamAbilityStat({
    required this.ability,
    required this.label,
    required this.questionCount,
    required this.score,
    required this.fullScore,
    required this.scoreRate,
  });

  final String ability;
  final String label;
  final int questionCount;
  final double score;
  final double fullScore;
  final double scoreRate;

  factory ExamAbilityStat.fromJson(Map<String, dynamic> json) {
    return ExamAbilityStat(
      ability: json['ability'] as String? ?? '',
      label: json['label'] as String? ?? '',
      questionCount: json['question_count'] as int? ?? 0,
      score: (json['score'] as num?)?.toDouble() ?? 0,
      fullScore: (json['full_score'] as num?)?.toDouble() ?? 0,
      scoreRate: (json['score_rate'] as num?)?.toDouble() ?? 0,
    );
  }
}

/// 班级平均（仅聚合值，无班级或无人参加时不可用）。
class ExamClassAverage {
  const ExamClassAverage({
    this.available = false,
    this.className,
    this.studentCount = 0,
    this.averageScore,
    this.averageRate,
  });

  final bool available;
  final String? className;
  final int studentCount;
  final double? averageScore;
  final double? averageRate;

  factory ExamClassAverage.fromJson(Map<String, dynamic> json) {
    return ExamClassAverage(
      available: json['available'] as bool? ?? false,
      className: json['class_name'] as String?,
      studentCount: json['student_count'] as int? ?? 0,
      averageScore: (json['average_score'] as num?)?.toDouble(),
      averageRate: (json['average_rate'] as num?)?.toDouble(),
    );
  }
}

class ExamTrendPoint {
  const ExamTrendPoint({
    required this.attemptId,
    required this.examId,
    required this.examTitle,
    required this.examType,
    required this.scoreRate,
    this.totalScore,
    this.submittedAt,
  });

  final int attemptId;
  final int examId;
  final String examTitle;
  final String examType;
  final double scoreRate;
  final double? totalScore;
  final DateTime? submittedAt;

  factory ExamTrendPoint.fromJson(Map<String, dynamic> json) {
    return ExamTrendPoint(
      attemptId: json['attempt_id'] as int? ?? 0,
      examId: json['exam_id'] as int? ?? 0,
      examTitle: json['exam_title'] as String? ?? '',
      examType: json['exam_type'] as String? ?? '',
      scoreRate: (json['score_rate'] as num?)?.toDouble() ?? 0,
      totalScore: (json['total_score'] as num?)?.toDouble(),
      submittedAt: DateTime.tryParse(json['submitted_at'] as String? ?? ''),
    );
  }
}

class ExamTrend {
  const ExamTrend({this.points = const [], this.deltaRate});

  final List<ExamTrendPoint> points;
  final double? deltaRate;

  factory ExamTrend.fromJson(Map<String, dynamic> json) {
    return ExamTrend(
      points: (json['points'] as List<dynamic>? ?? const [])
          .map((item) => ExamTrendPoint.fromJson(item as Map<String, dynamic>))
          .toList(),
      deltaRate: (json['delta_rate'] as num?)?.toDouble(),
    );
  }
}

class ExamSubjectiveQuestion {
  const ExamSubjectiveQuestion({
    required this.questionId,
    required this.qType,
    required this.stem,
    required this.fullScore,
    this.userAnswer,
    this.referenceAnswer,
    this.scoringPoints = const [],
    this.analysis,
    this.selfScore,
  });

  final int questionId;
  final String qType;
  final String stem;
  final double fullScore;
  final Map<String, dynamic>? userAnswer;
  final Map<String, dynamic>? referenceAnswer;
  final List<String> scoringPoints;
  final String? analysis;
  final double? selfScore;

  String get referenceAnswerText =>
      referenceAnswer?['value']?.toString() ?? '暂无参考答案';
  String get userAnswerText => userAnswer?['value']?.toString() ?? '未作答';

  factory ExamSubjectiveQuestion.fromJson(Map<String, dynamic> json) {
    return ExamSubjectiveQuestion(
      questionId: json['question_id'] as int? ?? 0,
      qType: json['q_type'] as String? ?? '',
      stem: json['stem'] as String? ?? '',
      fullScore: (json['full_score'] as num?)?.toDouble() ?? 0,
      userAnswer: json['user_answer'] as Map<String, dynamic>?,
      referenceAnswer: json['reference_answer'] as Map<String, dynamic>?,
      scoringPoints: (json['scoring_points'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
      analysis: json['analysis'] as String?,
      selfScore: (json['self_score'] as num?)?.toDouble(),
    );
  }
}

class ExamWrongItem {
  const ExamWrongItem({
    required this.questionId,
    required this.qType,
    required this.stem,
    this.userAnswer,
    required this.correctAnswer,
    this.analysis,
    required this.score,
    required this.fullScore,
  });

  final int questionId;
  final String qType;
  final String stem;
  final Map<String, dynamic>? userAnswer;
  final Map<String, dynamic> correctAnswer;
  final String? analysis;
  final double score;
  final double fullScore;

  String get correctAnswerText => correctAnswer['value']?.toString() ?? '';
  String get userAnswerText => userAnswer?['value']?.toString() ?? '未作答';

  factory ExamWrongItem.fromJson(Map<String, dynamic> json) {
    return ExamWrongItem(
      questionId: json['question_id'] as int? ?? 0,
      qType: json['q_type'] as String? ?? '',
      stem: json['stem'] as String? ?? '',
      userAnswer: json['user_answer'] as Map<String, dynamic>?,
      correctAnswer:
          json['correct_answer'] as Map<String, dynamic>? ?? const {},
      analysis: json['analysis'] as String?,
      score: (json['score'] as num?)?.toDouble() ?? 0,
      fullScore: (json['full_score'] as num?)?.toDouble() ?? 0,
    );
  }
}

class ExamNextAction {
  const ExamNextAction({
    required this.action,
    required this.label,
    this.knowledgePointIds = const [],
    this.count = 0,
  });

  final String action;
  final String label;
  final List<int> knowledgePointIds;
  final int count;

  factory ExamNextAction.fromJson(Map<String, dynamic> json) {
    return ExamNextAction(
      action: json['action'] as String? ?? '',
      label: json['label'] as String? ?? '',
      knowledgePointIds: (json['knowledge_point_ids'] as List<dynamic>? ?? const [])
          .map((item) => item as int)
          .toList(),
      count: json['count'] as int? ?? 0,
    );
  }
}

/// P2-07 班级同卷模考派发结果（POST /exams/mock）。
class MockExamAssignment {
  const MockExamAssignment({
    required this.examId,
    required this.classId,
    required this.title,
    required this.questionCount,
    required this.studentCount,
    this.windowStart,
    this.windowEnd,
  });

  final int examId;
  final int classId;
  final String title;
  final int questionCount;
  final int studentCount;
  final DateTime? windowStart;
  final DateTime? windowEnd;

  factory MockExamAssignment.fromJson(Map<String, dynamic> json) {
    return MockExamAssignment(
      examId: json['exam_id'] as int? ?? 0,
      classId: json['class_id'] as int? ?? 0,
      title: json['title'] as String? ?? '',
      questionCount: json['question_count'] as int? ?? 0,
      studentCount: json['student_count'] as int? ?? 0,
      windowStart: DateTime.tryParse(json['window_start'] as String? ?? ''),
      windowEnd: DateTime.tryParse(json['window_end'] as String? ?? ''),
    );
  }
}

/// 组卷蓝图（GET /api/exams/blueprints）。
class ExamBlueprint {
  const ExamBlueprint({
    required this.code,
    required this.name,
    required this.subject,
    required this.examType,
    required this.totalScore,
    required this.timeLimitMin,
    this.grade,
  });

  final String code;
  final String name;
  final String subject;
  final int? grade;
  final String examType;
  final int totalScore;
  final int timeLimitMin;

  factory ExamBlueprint.fromJson(Map<String, dynamic> json) {
    return ExamBlueprint(
      code: json['code'] as String? ?? '',
      name: json['name'] as String? ?? '',
      subject: json['subject'] as String? ?? '',
      grade: json['grade'] as int?,
      examType: json['exam_type'] as String? ?? 'unit',
      totalScore: (json['total_score'] as num?)?.toInt() ?? 100,
      timeLimitMin: (json['time_limit_min'] as num?)?.toInt() ?? 60,
    );
  }
}

/// 组卷发布结果（POST /api/exams/generate）。
class ExamGenerateResult {
  const ExamGenerateResult({
    required this.examId,
    required this.title,
    required this.seed,
    required this.questionCount,
    required this.totalScore,
    required this.kpCoverage,
    required this.difficultyMix,
    required this.fallbackCount,
    required this.insufficient,
  });

  final int examId;
  final String title;
  final int seed;
  final int questionCount;
  final double totalScore;
  final double kpCoverage;
  final Map<String, int> difficultyMix;
  final int fallbackCount;
  final bool insufficient;

  factory ExamGenerateResult.fromJson(Map<String, dynamic> json) {
    final rawMix = json['difficulty_mix'];
    final mix = <String, int>{};
    if (rawMix is Map) {
      rawMix.forEach((key, value) {
        mix[key.toString()] = (value as num?)?.toInt() ?? 0;
      });
    }
    return ExamGenerateResult(
      examId: json['exam_id'] as int? ?? 0,
      title: json['title'] as String? ?? '',
      seed: json['seed'] as int? ?? 0,
      questionCount: json['question_count'] as int? ?? 0,
      totalScore: (json['total_score'] as num?)?.toDouble() ?? 0,
      kpCoverage: (json['kp_coverage'] as num?)?.toDouble() ?? 0,
      difficultyMix: mix,
      fallbackCount: json['fallback_count'] as int? ?? 0,
      insufficient: json['insufficient'] as bool? ?? false,
    );
  }
}
