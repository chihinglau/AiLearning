/// 家长中心孩子摘要（/family/children）。
class FamilyChild {
  const FamilyChild({
    required this.id,
    required this.nickname,
    this.stage,
    this.grade,
    this.gradeGroup,
    this.isChild = false,
    this.dailyLimitMinutes = 120,
    this.teenMode = false,
  });

  final int id;
  final String nickname;
  final String? stage;
  final int? grade;
  final String? gradeGroup;
  final bool isChild;
  final int dailyLimitMinutes;
  final bool teenMode;

  String get gradeLabel => grade != null ? '$grade 年级' : '未设置年级';

  factory FamilyChild.fromJson(Map<String, dynamic> json) {
    return FamilyChild(
      id: json['id'] as int,
      nickname: json['nickname'] as String? ?? '孩子',
      stage: json['stage'] as String?,
      grade: json['grade'] as int?,
      gradeGroup: json['grade_group'] as String?,
      isChild: json['is_child'] as bool? ?? false,
      dailyLimitMinutes: json['daily_limit_minutes'] as int? ?? 120,
      teenMode: json['teen_mode'] as bool? ?? false,
    );
  }
}
