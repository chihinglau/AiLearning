import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:flutter/material.dart';

/// 知识点树节点（章 → 知识点，挂个人掌握度）。
class KnowledgeNode {
  const KnowledgeNode({
    required this.id,
    required this.subject,
    required this.name,
    this.grade,
    this.explanation,
    this.masteryScore = 0,
    this.masteryConfidence = 0,
    this.masteryBand = 'weak',
    this.questionCount = 0,
  });

  final int id;
  final String subject;
  final String name;
  final int? grade;
  final String? explanation;
  final double masteryScore;
  final int masteryConfidence;
  final String masteryBand;
  final int questionCount;

  String get subjectLabel => Subject.fromCode(subject).label;

  String get bandLabel {
    switch (masteryBand) {
      case 'growing':
        return '巩固中';
      case 'skilled':
        return '较熟练';
      case 'mastered':
        return '已精通';
      default:
        return '薄弱';
    }
  }

  Color get bandColor {
    switch (masteryBand) {
      case 'growing':
        return Colors.orange;
      case 'skilled':
        return Colors.blue;
      case 'mastered':
        return Colors.green;
      default:
        return Colors.redAccent;
    }
  }

  factory KnowledgeNode.fromJson(Map<String, dynamic> json) {
    return KnowledgeNode(
      id: json['id'] as int,
      subject: json['subject'] as String? ?? '',
      name: json['name'] as String? ?? '',
      grade: json['grade'] as int?,
      explanation: json['explanation'] as String?,
      masteryScore: (json['mastery_score'] as num?)?.toDouble() ?? 0,
      masteryConfidence: json['mastery_confidence'] as int? ?? 0,
      masteryBand: json['mastery_band'] as String? ?? 'weak',
      questionCount: json['question_count'] as int? ?? 0,
    );
  }
}

/// 教材章节 + 其下知识点。
class ChapterTree {
  const ChapterTree({
    required this.id,
    required this.textbookId,
    required this.grade,
    required this.name,
    required this.orderIndex,
    this.summary,
    this.knowledgePoints = const [],
  });

  final int id;
  final int textbookId;
  final int grade;
  final String name;
  final int orderIndex;
  final String? summary;
  final List<KnowledgeNode> knowledgePoints;

  factory ChapterTree.fromJson(Map<String, dynamic> json) {
    final rawNodes = json['knowledge_points'] as List<dynamic>? ?? const [];
    return ChapterTree(
      id: json['id'] as int,
      textbookId: json['textbook_id'] as int? ?? 0,
      grade: json['grade'] as int? ?? 1,
      name: json['name'] as String? ?? '',
      orderIndex: json['order_index'] as int? ?? 0,
      summary: json['summary'] as String?,
      knowledgePoints: rawNodes
          .map((item) => KnowledgeNode.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// /learn/submit 返回：判题结果 + 解析 + 掌握度变化。
class LearnSubmitResult {
  const LearnSubmitResult({
    required this.isCorrect,
    required this.correctAnswer,
    this.analysis,
    this.masteryScore,
    this.inWrongBook = false,
  });

  final bool isCorrect;
  final Map<String, dynamic> correctAnswer;
  final String? analysis;
  final double? masteryScore;
  final bool inWrongBook;

  String get correctAnswerText {
    final value = correctAnswer['value'];
    if (value is List) return value.map((e) => e.toString()).join('、');
    return value?.toString() ?? '-';
  }

  factory LearnSubmitResult.fromJson(Map<String, dynamic> json) {
    return LearnSubmitResult(
      isCorrect: json['is_correct'] as bool? ?? false,
      correctAnswer: json['correct_answer'] as Map<String, dynamic>? ?? const {},
      analysis: json['analysis'] as String?,
      masteryScore: (json['mastery_score'] as num?)?.toDouble(),
      inWrongBook: json['in_wrong_book'] as bool? ?? false,
    );
  }
}

/// 错题本条目。
class WrongQuestionItem {
  const WrongQuestionItem({
    required this.id,
    required this.questionId,
    required this.wrongCount,
    required this.correctStreak,
    required this.status,
    required this.intervalDays,
    required this.lastWrongAt,
    this.nextReviewAt,
    this.wrongReason,
    this.subject = '',
    this.qType = 'choice',
    this.stem = '',
    this.chapterId = 0,
    this.knowledgePointId,
    this.difficulty = 3,
  });

  final int id;
  final int questionId;
  final int wrongCount;
  final int correctStreak;
  final String status;
  final int intervalDays;
  final DateTime lastWrongAt;
  final DateTime? nextReviewAt;
  final String? wrongReason;
  final String subject;
  final String qType;
  final String stem;
  final int chapterId;
  final int? knowledgePointId;
  final int difficulty;

  bool get isActive => status == 'active';
  String get subjectLabel => Subject.fromCode(subject).label;

  static DateTime? _parseDate(dynamic value) {
    if (value == null) return null;
    return DateTime.tryParse(value.toString());
  }

  factory WrongQuestionItem.fromJson(Map<String, dynamic> json) {
    return WrongQuestionItem(
      id: json['id'] as int,
      questionId: json['question_id'] as int,
      wrongCount: json['wrong_count'] as int? ?? 1,
      correctStreak: json['correct_streak'] as int? ?? 0,
      status: json['status'] as String? ?? 'active',
      intervalDays: json['interval_days'] as int? ?? 1,
      lastWrongAt:
          _parseDate(json['last_wrong_at']) ?? DateTime.fromMillisecondsSinceEpoch(0),
      nextReviewAt: _parseDate(json['next_review_at']),
      wrongReason: json['wrong_reason'] as String?,
      subject: json['subject'] as String? ?? '',
      qType: json['q_type'] as String? ?? 'choice',
      stem: json['stem'] as String? ?? '',
      chapterId: json['chapter_id'] as int? ?? 0,
      knowledgePointId: json['knowledge_point_id'] as int?,
      difficulty: json['difficulty'] as int? ?? 3,
    );
  }
}

/// 错因枚举（与后端 WrongReasonIn 对齐）。
class WrongReason {
  const WrongReason(this.code, this.label);

  final String code;
  final String label;

  static const List<WrongReason> all = [
    WrongReason('careless', '粗心大意'),
    WrongReason('concept', '概念不清'),
    WrongReason('method', '方法不会'),
    WrongReason('calculation', '计算失误'),
    WrongReason('reading', '审题不清'),
    WrongReason('other', '其他原因'),
  ];

  static String labelOf(String? code) {
    return all
        .firstWhere((r) => r.code == code, orElse: () => const WrongReason('', '未标注'))
        .label;
  }
}

/// 学情总览 /learn/stats。
class LearnStats {
  const LearnStats({
    required this.totalAnswered,
    required this.totalCorrect,
    required this.accuracy,
    required this.streakDays,
    required this.dueReviewCount,
    required this.activeWrongCount,
    this.weakPoints = const [],
  });

  final int totalAnswered;
  final int totalCorrect;
  final double accuracy;
  final int streakDays;
  final int dueReviewCount;
  final int activeWrongCount;
  final List<KnowledgeNode> weakPoints;

  String get accuracyPercent => '${(accuracy * 100).round()}%';

  factory LearnStats.fromJson(Map<String, dynamic> json) {
    final rawWeak = json['weak_points'] as List<dynamic>? ?? const [];
    return LearnStats(
      totalAnswered: json['total_answered'] as int? ?? 0,
      totalCorrect: json['total_correct'] as int? ?? 0,
      accuracy: (json['accuracy'] as num?)?.toDouble() ?? 0,
      streakDays: json['streak_days'] as int? ?? 0,
      dueReviewCount: json['due_review_count'] as int? ?? 0,
      activeWrongCount: json['active_wrong_count'] as int? ?? 0,
      weakPoints: rawWeak
          .map((item) => KnowledgeNode.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}
