import 'package:ai_learning/core/constants/app_constants.dart';

/// 教材绑定（GET /api/me/textbooks）。
class TextbookBinding {
  const TextbookBinding({
    required this.id,
    required this.subject,
    required this.semester,
    required this.source,
    required this.isPrimary,
    required this.status,
    required this.mismatch,
    required this.textbook,
  });

  final int id;
  final String subject;
  final String semester;
  final String source;
  final bool isPrimary;
  final String status;
  final bool mismatch;
  final BindingTextbook textbook;

  String get subjectLabel => Subject.fromCode(subject).label;

  factory TextbookBinding.fromJson(Map<String, dynamic> json) {
    return TextbookBinding(
      id: json['id'] as int? ?? 0,
      subject: json['subject'] as String? ?? '',
      semester: json['semester'] as String? ?? 'first',
      source: json['source'] as String? ?? 'auto',
      isPrimary: json['is_primary'] as bool? ?? false,
      status: json['status'] as String? ?? 'active',
      mismatch: json['mismatch'] as bool? ?? false,
      textbook: BindingTextbook.fromJson(
        json['textbook'] as Map<String, dynamic>? ?? const {},
      ),
    );
  }
}

class BindingTextbook {
  const BindingTextbook({
    required this.id,
    required this.subject,
    required this.grade,
    required this.version,
    required this.semester,
  });

  final int id;
  final String subject;
  final int grade;
  final String version;
  final String semester;

  String get displayName {
    final subjectLabel = Subject.fromCode(subject).label;
    final semesterLabel = semester == 'second' ? '下册' : '上册';
    return '$subjectLabel $grade年级 · $version · $semesterLabel';
  }

  factory BindingTextbook.fromJson(Map<String, dynamic> json) {
    return BindingTextbook(
      id: json['id'] as int? ?? 0,
      subject: json['subject'] as String? ?? '',
      grade: json['grade'] as int? ?? 1,
      version: json['version'] as String? ?? '',
      semester: json['semester'] as String? ?? 'first',
    );
  }
}

/// 推荐教材（GET /api/me/textbooks/recommend）。
class TextbookRecommendation {
  const TextbookRecommendation({
    required this.grade,
    required this.semester,
    required this.region,
    required this.subjects,
  });

  final int grade;
  final String semester;
  final String region;
  final List<RecommendedSubject> subjects;

  factory TextbookRecommendation.fromJson(Map<String, dynamic> json) {
    return TextbookRecommendation(
      grade: json['grade'] as int? ?? 1,
      semester: json['semester'] as String? ?? 'first',
      region: json['region'] as String? ?? 'shenzhen',
      subjects: (json['subjects'] as List<dynamic>? ?? const [])
          .map((item) => RecommendedSubject.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class RecommendedSubject {
  const RecommendedSubject({
    required this.subject,
    required this.textbookId,
    required this.version,
    required this.grade,
  });

  final String subject;
  final int textbookId;
  final String version;
  final int grade;

  String get subjectLabel => Subject.fromCode(subject).label;

  factory RecommendedSubject.fromJson(Map<String, dynamic> json) {
    return RecommendedSubject(
      subject: json['subject'] as String? ?? '',
      textbookId: json['textbook_id'] as int? ?? 0,
      version: json['version'] as String? ?? '',
      grade: json['grade'] as int? ?? 1,
    );
  }
}

/// 学段与年级区间映射，供引导页选择。
Stage stageForGrade(int grade) {
  if (grade <= 6) return Stage.primary;
  if (grade <= 9) return Stage.junior;
  return Stage.senior;
}

List<int> gradesForStage(Stage stage) {
  switch (stage) {
    case Stage.primary:
      return const [1, 2, 3, 4, 5, 6];
    case Stage.junior:
      return const [7, 8, 9];
    case Stage.senior:
      return const [10, 11, 12];
  }
}
