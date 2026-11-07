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
    this.permissions = const [],
    this.scope,
    this.needsReconsent = false,
  });

  final int id;
  final String phone;
  final String nickname;
  final String role;
  final String? stage;
  final int? grade;
  final bool isChild;
  final int dailyLimitMinutes;
  final List<String> permissions;
  final String? scope;

  /// 政策版本升高后为 true，登录后须重新阅读并同意（R-03）。
  final bool needsReconsent;

  bool get isStudent => role == 'student';

  bool get isSuperAdmin => permissions.contains('*');

  bool hasPermission(String permission) {
    return isSuperAdmin || permissions.contains(permission);
  }

  bool hasAnyPermission(Iterable<String> required) {
    if (isSuperAdmin) return true;
    return required.any(permissions.contains);
  }

  AppUser copyWith({
    String? stage,
    int? grade,
    List<String>? permissions,
    bool? needsReconsent,
  }) {
    return AppUser(
      id: id,
      phone: phone,
      nickname: nickname,
      role: role,
      stage: stage ?? this.stage,
      grade: grade ?? this.grade,
      isChild: isChild,
      dailyLimitMinutes: dailyLimitMinutes,
      permissions: permissions ?? this.permissions,
      scope: scope,
      needsReconsent: needsReconsent ?? this.needsReconsent,
    );
  }

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
      permissions: (json['permissions'] as List<dynamic>? ?? const [])
          .map((item) => item as String)
          .toList(),
      scope: json['scope'] as String?,
      needsReconsent: json['needs_reconsent'] as bool? ?? false,
    );
  }
}
