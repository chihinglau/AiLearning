import 'package:ai_learning/core/constants/app_constants.dart';

class Textbook {
  const Textbook({
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

  String get subjectLabel => Subject.fromCode(subject).label;

  String get semesterLabel => semester == 'second' ? '下册' : '上册';

  String get displayName => '$subjectLabel $grade年级 · $version · $semesterLabel';

  factory Textbook.fromJson(Map<String, dynamic> json) {
    return Textbook(
      id: json['id'] as int,
      subject: json['subject'] as String? ?? '',
      grade: json['grade'] as int? ?? 1,
      version: json['version'] as String? ?? '',
      semester: json['semester'] as String? ?? 'first',
    );
  }
}

class Chapter {
  const Chapter({
    required this.id,
    required this.textbookId,
    required this.grade,
    required this.name,
    required this.orderIndex,
    this.summary,
  });

  final int id;
  final int textbookId;
  final int grade;
  final String name;
  final int orderIndex;
  final String? summary;

  factory Chapter.fromJson(Map<String, dynamic> json) {
    return Chapter(
      id: json['id'] as int,
      textbookId: json['textbook_id'] as int? ?? 0,
      grade: json['grade'] as int? ?? 1,
      name: json['name'] as String? ?? '',
      orderIndex: json['order_index'] as int? ?? 0,
      summary: json['summary'] as String?,
    );
  }
}

class QuestionOption {
  const QuestionOption({required this.key, required this.text});

  final String key;
  final String text;

  factory QuestionOption.fromJson(Map<String, dynamic> json) {
    return QuestionOption(
      key: json['key'] as String? ?? '',
      text: json['text'] as String? ?? '',
    );
  }
}

class Question {
  const Question({
    required this.id,
    required this.chapterId,
    required this.subject,
    required this.qType,
    required this.stem,
    this.knowledgePointId,
    this.options = const [],
    this.difficulty = 3,
    this.tags = const [],
  });

  final int id;
  final int chapterId;
  final String subject;
  final String qType;
  final String stem;
  final int? knowledgePointId;
  final List<QuestionOption> options;
  final int difficulty;
  final List<String> tags;

  factory Question.fromJson(Map<String, dynamic> json) {
    final content = json['content'] as Map<String, dynamic>? ?? const {};
    final rawOptions = json['options'] as List<dynamic>? ?? const [];
    return Question(
      id: json['id'] as int,
      chapterId: json['chapter_id'] as int? ?? 0,
      subject: json['subject'] as String? ?? '',
      qType: json['q_type'] as String? ?? 'choice',
      stem: content['stem'] as String? ?? '',
      knowledgePointId: json['knowledge_point_id'] as int?,
      options: rawOptions
          .map((item) => QuestionOption.fromJson(item as Map<String, dynamic>))
          .toList(),
      difficulty: json['difficulty'] as int? ?? 3,
      tags: (json['tags'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
    );
  }
}
