class AppUser {
  const AppUser({
    required this.id,
    required this.phone,
    required this.nickname,
    required this.role,
    this.stage,
    this.grade,
    this.isChild = false,
    this.dailyLimitMinutes = 120,
  });

  final int id;
  final String phone;
  final String nickname;
  final String role;
  final String? stage;
  final int? grade;
  final bool isChild;
  final int dailyLimitMinutes;

  bool get isStudent => role == 'student';

  factory AppUser.fromJson(Map<String, dynamic> json) {
    return AppUser(
      id: json['id'] as int,
      phone: json['phone'] as String? ?? '',
      nickname: json['nickname'] as String? ?? '',
      role: json['role'] as String? ?? 'student',
      stage: json['stage'] as String?,
      grade: json['grade'] as int?,
      isChild: json['is_child'] as bool? ?? false,
      dailyLimitMinutes: json['daily_limit_minutes'] as int? ?? 120,
    );
  }
}
