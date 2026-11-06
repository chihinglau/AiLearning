import 'package:ai_learning/core/constants/app_constants.dart';

/// 班级摘要（/org/classes）。
class ClassSummary {
  const ClassSummary({
    required this.id,
    required this.schoolId,
    required this.grade,
    required this.name,
    required this.schoolYear,
    this.headTeacherId,
    this.memberCount = 0,
  });

  final int id;
  final int schoolId;
  final int grade;
  final String name;
  final String schoolYear;
  final int? headTeacherId;
  final int memberCount;

  String get label => '$grade 年级 $name';

  factory ClassSummary.fromJson(Map<String, dynamic> json) {
    return ClassSummary(
      id: json['id'] as int,
      schoolId: json['school_id'] as int? ?? 0,
      grade: json['grade'] as int? ?? 1,
      name: json['name'] as String? ?? '班级',
      schoolYear: json['school_year'] as String? ?? '',
      headTeacherId: json['head_teacher_id'] as int?,
      memberCount: json['member_count'] as int? ?? 0,
    );
  }
}

/// 班级薄弱知识点（仅聚合值）。
class ClassWeakPoint {
  const ClassWeakPoint({
    required this.knowledgePointId,
    required this.name,
    required this.subject,
    required this.avgMastery,
  });

  final int knowledgePointId;
  final String name;
  final String subject;
  final double avgMastery;

  String get subjectLabel => Subject.fromCode(subject).label;

  factory ClassWeakPoint.fromJson(Map<String, dynamic> json) {
    return ClassWeakPoint(
      knowledgePointId: json['knowledge_point_id'] as int? ?? 0,
      name: json['name'] as String? ?? '',
      subject: json['subject'] as String? ?? '',
      avgMastery: (json['avg_mastery'] as num?)?.toDouble() ?? 0,
    );
  }
}

/// 班级学情聚合（/org/classes/{id}/stats，不含学生个人信息）。
class ClassStats {
  const ClassStats({
    required this.classId,
    required this.className,
    required this.grade,
    required this.studentCount,
    required this.activeStudentCount,
    required this.submissionRate,
    required this.totalAnswered,
    required this.accuracy,
    required this.avgMastery,
    this.subject,
    this.weakPoints = const [],
  });

  final int classId;
  final String className;
  final int grade;
  final int studentCount;
  final int activeStudentCount;
  final double submissionRate;
  final int totalAnswered;
  final double accuracy;
  final double avgMastery;
  final String? subject;
  final List<ClassWeakPoint> weakPoints;

  String get label => '$grade 年级 $className';

  String get submissionRatePercent => '${(submissionRate * 100).round()}%';

  String get accuracyPercent => '${(accuracy * 100).round()}%';

  String get avgMasteryText => '${avgMastery.round()}';

  String get subjectLabel =>
      subject == null || subject!.isEmpty ? '全部学科' : Subject.fromCode(subject!).label;

  factory ClassStats.fromJson(Map<String, dynamic> json) {
    final rawWeak = json['weak_points'] as List<dynamic>? ?? const [];
    return ClassStats(
      classId: json['class_id'] as int? ?? 0,
      className: json['class_name'] as String? ?? '班级',
      grade: json['grade'] as int? ?? 1,
      studentCount: json['student_count'] as int? ?? 0,
      activeStudentCount: json['active_student_count'] as int? ?? 0,
      submissionRate: (json['submission_rate'] as num?)?.toDouble() ?? 0,
      totalAnswered: json['total_answered'] as int? ?? 0,
      accuracy: (json['accuracy'] as num?)?.toDouble() ?? 0,
      avgMastery: (json['avg_mastery'] as num?)?.toDouble() ?? 0,
      subject: json['subject'] as String?,
      weakPoints: rawWeak
          .map((item) => ClassWeakPoint.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}
