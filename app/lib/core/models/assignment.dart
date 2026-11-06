import 'package:ai_learning/core/constants/app_constants.dart';

/// 班级作业摘要/详情（GET /api/assignments、/api/assignments/{id}）。
class AssignmentInfo {
  const AssignmentInfo({
    required this.id,
    required this.title,
    required this.subject,
    required this.classId,
    required this.className,
    required this.examId,
    this.dueAt,
    this.status = 'published',
    this.createdAt,
    this.studentCount = 0,
    this.submittedCount = 0,
    this.pendingGrading = 0,
    this.myAttemptId,
    this.myStatus,
    this.myTotalScore,
    this.students = const [],
  });

  final int id;
  final String title;
  final String subject;
  final int classId;
  final String className;
  final int examId;
  final DateTime? dueAt;
  final String status;
  final DateTime? createdAt;
  final int studentCount;
  final int submittedCount;
  final int pendingGrading;
  final int? myAttemptId;
  final String? myStatus;
  final double? myTotalScore;
  final List<AssignmentStudent> students;

  String get subjectLabel => Subject.fromCode(subject).label;

  bool get notStarted => myStatus == null || myStatus == 'not_started';
  bool get inProgress => myStatus == 'in_progress';
  bool get grading => myStatus == 'grading';
  bool get completed => myStatus == 'completed';

  String get myStatusLabel {
    if (notStarted) return '未开始';
    switch (myStatus) {
      case 'in_progress':
        return '进行中';
      case 'grading':
        return '待批改';
      case 'completed':
        return '已完成';
      default:
        return myStatus ?? '';
    }
  }

  String? get dueLabel {
    if (dueAt == null) return null;
    final local = dueAt!.toLocal();
    String two(int number) => number.toString().padLeft(2, '0');
    return '${two(local.month)}-${two(local.day)} ${two(local.hour)}:${two(local.minute)}';
  }

  factory AssignmentInfo.fromJson(Map<String, dynamic> json) {
    final rawStudents = json['students'] as List<dynamic>? ?? const [];
    return AssignmentInfo(
      id: json['id'] as int? ?? 0,
      title: json['title'] as String? ?? '',
      subject: json['subject'] as String? ?? '',
      classId: json['class_id'] as int? ?? 0,
      className: json['class_name'] as String? ?? '',
      examId: json['exam_id'] as int? ?? 0,
      dueAt: DateTime.tryParse(json['due_at'] as String? ?? ''),
      status: json['status'] as String? ?? 'published',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
      studentCount: json['student_count'] as int? ?? 0,
      submittedCount: json['submitted_count'] as int? ?? 0,
      pendingGrading: json['pending_grading'] as int? ?? 0,
      myAttemptId: json['my_attempt_id'] as int?,
      myStatus: json['my_status'] as String?,
      myTotalScore: (json['my_total_score'] as num?)?.toDouble(),
      students: rawStudents
          .map((item) => AssignmentStudent.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class AssignmentStudent {
  const AssignmentStudent({
    required this.studentId,
    this.nickname,
    this.attemptId,
    this.status,
    this.objectiveScore,
    this.subjectiveScore,
    this.totalScore,
    this.submittedAt,
  });

  final int studentId;
  final String? nickname;
  final int? attemptId;
  final String? status;
  final double? objectiveScore;
  final double? subjectiveScore;
  final double? totalScore;
  final DateTime? submittedAt;

  String get statusLabel {
    switch (status) {
      case 'in_progress':
        return '作答中';
      case 'grading':
        return '待批改';
      case 'completed':
        return '已完成';
      default:
        return '未开始';
    }
  }

  factory AssignmentStudent.fromJson(Map<String, dynamic> json) {
    return AssignmentStudent(
      studentId: json['student_id'] as int? ?? 0,
      nickname: json['nickname'] as String?,
      attemptId: json['attempt_id'] as int?,
      status: json['status'] as String?,
      objectiveScore: (json['objective_score'] as num?)?.toDouble(),
      subjectiveScore: (json['subjective_score'] as num?)?.toDouble(),
      totalScore: (json['total_score'] as num?)?.toDouble(),
      submittedAt: DateTime.tryParse(json['submitted_at'] as String? ?? ''),
    );
  }
}

/// 教师批改清单（GET /api/assignments/{id}/grading）。
class GradingItem {
  const GradingItem({
    required this.attemptId,
    required this.studentId,
    this.studentName,
    required this.questionId,
    required this.qType,
    this.stem = '',
    this.reference = '',
    this.analysis,
    this.userAnswer,
    this.images = const [],
    required this.maxScore,
    this.currentScore,
    this.comment,
  });

  final int attemptId;
  final int studentId;
  final String? studentName;
  final int questionId;
  final String qType;
  final String stem;
  final String reference;
  final String? analysis;
  final String? userAnswer;
  final List<String> images;
  final double maxScore;
  final double? currentScore;
  final String? comment;

  factory GradingItem.fromJson(Map<String, dynamic> json) {
    final content = json['content'] as Map<String, dynamic>? ?? const {};
    final answer = json['answer'] as Map<String, dynamic>? ?? const {};
    final userAnswer = json['user_answer'] as Map<String, dynamic>?;
    return GradingItem(
      attemptId: json['attempt_id'] as int? ?? 0,
      studentId: json['student_id'] as int? ?? 0,
      studentName: json['student_name'] as String?,
      questionId: json['question_id'] as int? ?? 0,
      qType: json['q_type'] as String? ?? '',
      stem: content['stem'] as String? ?? '',
      reference: answer['value'] as String? ?? '',
      analysis: json['analysis'] as String?,
      userAnswer: userAnswer?['value'] as String?,
      images: (userAnswer?['images'] as List<dynamic>? ?? const [])
          .whereType<String>()
          .toList(),
      maxScore: (json['max_score'] as num?)?.toDouble() ?? 0,
      currentScore: (json['current_score'] as num?)?.toDouble(),
      comment: json['comment'] as String?,
    );
  }
}

class GradingList {
  const GradingList({required this.assignmentId, this.items = const []});

  final int assignmentId;
  final List<GradingItem> items;

  factory GradingList.fromJson(Map<String, dynamic> json) {
    final raw = json['items'] as List<dynamic>? ?? const [];
    return GradingList(
      assignmentId: json['assignment_id'] as int? ?? 0,
      items: raw
          .map((item) => GradingItem.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class GradeBatchResult {
  const GradeBatchResult({
    required this.graded,
    required this.completedAttempts,
    required this.pendingAttempts,
  });

  final int graded;
  final int completedAttempts;
  final int pendingAttempts;

  factory GradeBatchResult.fromJson(Map<String, dynamic> json) {
    return GradeBatchResult(
      graded: json['graded'] as int? ?? 0,
      completedAttempts: json['completed_attempts'] as int? ?? 0,
      pendingAttempts: json['pending_attempts'] as int? ?? 0,
    );
  }
}
