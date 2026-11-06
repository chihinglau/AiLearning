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
    this.parentId,
    this.nodeType = 'point',
    this.orderIndex = 0,
    this.prerequisites = const [],
    this.state = '未学习',
    this.lastStudiedAt,
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
  final int? parentId;
  final String nodeType;
  final int orderIndex;
  final List<int> prerequisites;
  final String state;
  final DateTime? lastStudiedAt;

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
      parentId: json['parent_id'] as int?,
      nodeType: json['node_type'] as String? ?? 'point',
      orderIndex: json['order_index'] as int? ?? 0,
      prerequisites: (json['prerequisites'] as List<dynamic>? ?? const [])
          .map((item) => item as int)
          .toList(),
      state: json['state'] as String? ?? '未学习',
      lastStudiedAt: DateTime.tryParse(json['last_studied_at'] as String? ?? ''),
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

/// 首页：当前教材（含绑定与年级冲突标识）。
class HomeTextbook {
  const HomeTextbook({
    required this.subject,
    required this.textbookId,
    required this.version,
    required this.grade,
    required this.semester,
    this.mismatch = false,
  });

  final String subject;
  final int textbookId;
  final String version;
  final int grade;
  final String semester;
  final bool mismatch;

  String get subjectLabel => Subject.fromCode(subject).label;

  factory HomeTextbook.fromJson(Map<String, dynamic> json) {
    return HomeTextbook(
      subject: json['subject'] as String? ?? '',
      textbookId: json['textbook_id'] as int? ?? 0,
      version: json['version'] as String? ?? '',
      grade: json['grade'] as int? ?? 1,
      semester: json['semester'] as String? ?? '',
      mismatch: json['mismatch'] as bool? ?? false,
    );
  }
}

/// 今日计划：到期复习、建议练题量与用时、新知识点目标。
class HomeTodayPlan {
  const HomeTodayPlan({
    required this.dueReview,
    required this.practiceQuestions,
    required this.practiceMinutes,
    required this.newKpTarget,
  });

  final int dueReview;
  final int practiceQuestions;
  final int practiceMinutes;
  final int newKpTarget;

  factory HomeTodayPlan.fromJson(Map<String, dynamic> json) {
    return HomeTodayPlan(
      dueReview: json['due_review'] as int? ?? 0,
      practiceQuestions: json['practice_questions'] as int? ?? 0,
      practiceMinutes: json['practice_minutes'] as int? ?? 0,
      newKpTarget: json['new_kp_target'] as int? ?? 0,
    );
  }
}

/// 继续学习：上次学习到的章节/知识点。
class HomeContinue {
  const HomeContinue({
    required this.subject,
    this.chapterId,
    this.chapterName,
    this.knowledgePointId,
    this.knowledgePointName,
  });

  final String subject;
  final int? chapterId;
  final String? chapterName;
  final int? knowledgePointId;
  final String? knowledgePointName;

  String get subjectLabel => Subject.fromCode(subject).label;

  String get title {
    if (knowledgePointName != null && knowledgePointName!.isNotEmpty) {
      return knowledgePointName!;
    }
    return chapterName ?? '上次学习内容';
  }

  factory HomeContinue.fromJson(Map<String, dynamic> json) {
    return HomeContinue(
      subject: json['subject'] as String? ?? '',
      chapterId: json['chapter_id'] as int?,
      chapterName: json['chapter_name'] as String?,
      knowledgePointId: json['knowledge_point_id'] as int?,
      knowledgePointName: json['knowledge_point_name'] as String?,
    );
  }
}

/// 首页推荐行动：review / learn_kp / practice / continue / daily。
class HomeRecommendation {
  const HomeRecommendation({
    required this.action,
    required this.label,
    required this.reason,
    this.knowledgePointId,
  });

  final String action;
  final String label;
  final String reason;
  final int? knowledgePointId;

  factory HomeRecommendation.fromJson(Map<String, dynamic> json) {
    return HomeRecommendation(
      action: json['action'] as String? ?? 'daily',
      label: json['label'] as String? ?? '每日一练',
      reason: json['reason'] as String? ?? '',
      knowledgePointId: json['knowledge_point_id'] as int?,
    );
  }
}

/// 学习首页聚合 /learn/home。
class HomeData {
  const HomeData({
    required this.grade,
    required this.stage,
    required this.gradeGroup,
    required this.semester,
    required this.region,
    required this.needsBinding,
    required this.todayPlan,
    required this.recommendation,
    this.textbooks = const [],
    this.recommended = const [],
    this.mismatchSubjects = const [],
    this.continueLearning,
    this.pendingExams = const [],
  });

  final int grade;
  final String stage;
  final String gradeGroup;
  final String semester;
  final String region;
  final bool needsBinding;
  final List<HomeTextbook> textbooks;
  final List<HomeTextbook> recommended;
  final List<String> mismatchSubjects;
  final HomeTodayPlan todayPlan;
  final HomeContinue? continueLearning;
  final HomeRecommendation recommendation;
  final List<Map<String, dynamic>> pendingExams;

  Stage? get stageEnum => Stage.fromCode(stage);

  /// 按学科取当前已绑定教材。
  HomeTextbook? textbookOf(String subject) {
    for (final item in textbooks) {
      if (item.subject == subject) return item;
    }
    return null;
  }

  factory HomeData.fromJson(Map<String, dynamic> json) {
    final rawTextbooks = json['textbooks'] as List<dynamic>? ?? const [];
    final rawRecommended = json['recommended'] as List<dynamic>? ?? const [];
    final rawMismatch = json['mismatch_subjects'] as List<dynamic>? ?? const [];
    final rawExams = json['pending_exams'] as List<dynamic>? ?? const [];
    final rawContinue = json['continue_learning'];
    return HomeData(
      grade: json['grade'] as int? ?? 1,
      stage: json['stage'] as String? ?? '',
      gradeGroup: json['grade_group'] as String? ?? '',
      semester: json['semester'] as String? ?? '',
      region: json['region'] as String? ?? '',
      needsBinding: json['needs_binding'] as bool? ?? false,
      textbooks: rawTextbooks
          .map((item) => HomeTextbook.fromJson(item as Map<String, dynamic>))
          .toList(),
      recommended: rawRecommended
          .map((item) => HomeTextbook.fromJson(item as Map<String, dynamic>))
          .toList(),
      mismatchSubjects: rawMismatch.map((item) => item.toString()).toList(),
      todayPlan: HomeTodayPlan.fromJson(
        json['today_plan'] as Map<String, dynamic>? ?? const {},
      ),
      continueLearning: rawContinue is Map<String, dynamic>
          ? HomeContinue.fromJson(rawContinue)
          : null,
      recommendation: HomeRecommendation.fromJson(
        json['recommendation'] as Map<String, dynamic>? ?? const {},
      ),
      pendingExams: rawExams
          .map((item) => item as Map<String, dynamic>)
          .toList(),
    );
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

String masteryBandLabel(String band) {
  switch (band) {
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

Color masteryBandColor(String band) {
  switch (band) {
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

/// 单元目录 /learn/textbook/{id}/units。
class UnitSummary {
  const UnitSummary({
    required this.id,
    required this.textbookId,
    required this.grade,
    required this.name,
    required this.orderIndex,
    this.summary,
    this.sectionCount = 0,
    this.kpCount = 0,
    this.questionCount = 0,
    this.avgMastery = 0,
    this.masteryBand = 'weak',
    this.learnedKpCount = 0,
    this.progress = 0,
  });

  final int id;
  final int textbookId;
  final int grade;
  final String name;
  final int orderIndex;
  final String? summary;
  final int sectionCount;
  final int kpCount;
  final int questionCount;
  final double avgMastery;
  final String masteryBand;
  final int learnedKpCount;
  final double progress;

  String get bandLabelText => masteryBandLabel(masteryBand);

  Color get bandColor => masteryBandColor(masteryBand);

  String get progressText => '已学 $learnedKpCount/$kpCount 知识点';

  factory UnitSummary.fromJson(Map<String, dynamic> json) {
    return UnitSummary(
      id: json['id'] as int? ?? 0,
      textbookId: json['textbook_id'] as int? ?? 0,
      grade: json['grade'] as int? ?? 1,
      name: json['name'] as String? ?? '',
      orderIndex: json['order_index'] as int? ?? 0,
      summary: json['summary'] as String?,
      sectionCount: json['section_count'] as int? ?? 0,
      kpCount: json['kp_count'] as int? ?? 0,
      questionCount: json['question_count'] as int? ?? 0,
      avgMastery: (json['avg_mastery'] as num?)?.toDouble() ?? 0,
      masteryBand: json['mastery_band'] as String? ?? 'weak',
      learnedKpCount: json['learned_kp_count'] as int? ?? 0,
      progress: (json['progress'] as num?)?.toDouble() ?? 0,
    );
  }
}

/// 单元下的节。
class UnitSection {
  const UnitSection({
    required this.id,
    required this.name,
    required this.orderIndex,
    this.kpCount = 0,
    this.avgMastery = 0,
    this.masteryBand = 'weak',
  });

  final int id;
  final String name;
  final int orderIndex;
  final int kpCount;
  final double avgMastery;
  final String masteryBand;

  Color get bandColor => masteryBandColor(masteryBand);

  factory UnitSection.fromJson(Map<String, dynamic> json) {
    return UnitSection(
      id: json['id'] as int? ?? 0,
      name: json['name'] as String? ?? '',
      orderIndex: json['order_index'] as int? ?? 0,
      kpCount: json['kp_count'] as int? ?? 0,
      avgMastery: (json['avg_mastery'] as num?)?.toDouble() ?? 0,
      masteryBand: json['mastery_band'] as String? ?? 'weak',
    );
  }
}

/// 单元详情 /learn/unit/{id}。
class UnitDetail {
  const UnitDetail({
    required this.unit,
    this.sections = const [],
    this.knowledgePoints = const [],
  });

  final UnitSummary unit;
  final List<UnitSection> sections;
  final List<KnowledgeNode> knowledgePoints;

  /// 按节分组；无节归属的知识点归入「未分节」。
  List<KnowledgeNode> nodesOfSection(int? sectionId) {
    return knowledgePoints
        .where((node) => node.parentId == sectionId)
        .toList()
      ..sort((a, b) => a.orderIndex.compareTo(b.orderIndex));
  }

  factory UnitDetail.fromJson(Map<String, dynamic> json) {
    return UnitDetail(
      unit: UnitSummary.fromJson(
        json['unit'] as Map<String, dynamic>? ?? const {},
      ),
      sections: (json['sections'] as List<dynamic>? ?? const [])
          .map((item) => UnitSection.fromJson(item as Map<String, dynamic>))
          .toList(),
      knowledgePoints: (json['knowledge_points'] as List<dynamic>? ?? const [])
          .map((item) => KnowledgeNode.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// 前置知识点（/learn/kp/{id}）。
class KpBrief {
  const KpBrief({
    required this.id,
    required this.name,
    required this.subject,
    this.masteryScore = 0,
  });

  final int id;
  final String name;
  final String subject;
  final double masteryScore;

  factory KpBrief.fromJson(Map<String, dynamic> json) {
    return KpBrief(
      id: json['id'] as int? ?? 0,
      name: json['name'] as String? ?? '',
      subject: json['subject'] as String? ?? '',
      masteryScore: (json['mastery_score'] as num?)?.toDouble() ?? 0,
    );
  }
}

/// 知识点详情 /learn/kp/{id}：讲解、状态、前置、掌握度。
class KpDetail {
  const KpDetail({
    required this.id,
    required this.subject,
    required this.name,
    this.grade,
    this.nodeType = 'point',
    this.explanation,
    this.sectionId,
    this.sectionName,
    this.prerequisites = const [],
    this.masteryScore = 0,
    this.masteryConfidence = 0,
    this.masteryBand = 'weak',
    this.questionCount = 0,
    this.state = '未学习',
    this.stateEvidence = 0,
    this.lastStudiedAt,
  });

  final int id;
  final String subject;
  final int? grade;
  final String name;
  final String nodeType;
  final String? explanation;
  final int? sectionId;
  final String? sectionName;
  final List<KpBrief> prerequisites;
  final double masteryScore;
  final int masteryConfidence;
  final String masteryBand;
  final int questionCount;
  final String state;
  final int stateEvidence;
  final DateTime? lastStudiedAt;

  Color get bandColor => masteryBandColor(masteryBand);

  String get bandLabelText => masteryBandLabel(masteryBand);

  factory KpDetail.fromJson(Map<String, dynamic> json) {
    return KpDetail(
      id: json['id'] as int? ?? 0,
      subject: json['subject'] as String? ?? '',
      grade: json['grade'] as int?,
      name: json['name'] as String? ?? '',
      nodeType: json['node_type'] as String? ?? 'point',
      explanation: json['explanation'] as String?,
      sectionId: json['section_id'] as int?,
      sectionName: json['section_name'] as String?,
      prerequisites: (json['prerequisites'] as List<dynamic>? ?? const [])
          .map((item) => KpBrief.fromJson(item as Map<String, dynamic>))
          .toList(),
      masteryScore: (json['mastery_score'] as num?)?.toDouble() ?? 0,
      masteryConfidence: json['mastery_confidence'] as int? ?? 0,
      masteryBand: json['mastery_band'] as String? ?? 'weak',
      questionCount: json['question_count'] as int? ?? 0,
      state: json['state'] as String? ?? '未学习',
      stateEvidence: json['state_evidence'] as int? ?? 0,
      lastStudiedAt: DateTime.tryParse(json['last_studied_at'] as String? ?? ''),
    );
  }
}

/// 知识点例题（带答案与解析）。
class KpExample {
  const KpExample({
    required this.id,
    required this.qType,
    required this.stem,
    this.options = const [],
    required this.correctAnswer,
    this.analysis,
    this.difficulty = 3,
  });

  final int id;
  final String qType;
  final String stem;
  final List<KpExampleOption> options;
  final String correctAnswer;
  final String? analysis;
  final int difficulty;

  String get typeLabel {
    switch (qType) {
      case 'choice':
        return '单选题';
      case 'fill':
        return '填空题';
      case 'judge':
        return '判断题';
      case 'short':
        return '简答题';
      default:
        return qType;
    }
  }

  factory KpExample.fromJson(Map<String, dynamic> json) {
    final content = json['content'] as Map<String, dynamic>? ?? const {};
    final answer = json['correct_answer'] as Map<String, dynamic>? ?? const {};
    return KpExample(
      id: json['id'] as int? ?? 0,
      qType: json['q_type'] as String? ?? 'choice',
      stem: content['stem'] as String? ?? '',
      options: (json['options'] as List<dynamic>? ?? const [])
          .map((item) => KpExampleOption.fromJson(item as Map<String, dynamic>))
          .toList(),
      correctAnswer: answer['value']?.toString() ?? '',
      analysis: json['analysis'] as String?,
      difficulty: json['difficulty'] as int? ?? 3,
    );
  }
}

class KpExampleOption {
  const KpExampleOption({required this.key, required this.text});

  final String key;
  final String text;

  factory KpExampleOption.fromJson(Map<String, dynamic> json) {
    return KpExampleOption(
      key: json['key']?.toString() ?? '',
      text: json['text']?.toString() ?? '',
    );
  }
}
