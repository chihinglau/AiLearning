import 'package:flutter/material.dart';

/// 品牌柔和彩 accent 色板（UX-01）。
///
/// 一种功能固定一种 accent，禁止页面硬编码色值；未来接入暗色主题时只需在
/// [lerp] 或主题层调整，不改调用方。
class AppAccents extends ThemeExtension<AppAccents> {
  const AppAccents({
    required this.practice,
    required this.learn,
    required this.exam,
    required this.assignment,
  });

  final Color practice;
  final Color learn;
  final Color exam;
  final Color assignment;

  static const AppAccents light = AppAccents(
    practice: Color(0xFF4F46C8),
    learn: Color(0xFF0B7A6D),
    exam: Color(0xFFB45309),
    assignment: Color(0xFFA63D6D),
  );

  static AppAccents of(BuildContext context) =>
      Theme.of(context).extension<AppAccents>() ?? light;

  @override
  AppAccents copyWith({
    Color? practice,
    Color? learn,
    Color? exam,
    Color? assignment,
  }) {
    return AppAccents(
      practice: practice ?? this.practice,
      learn: learn ?? this.learn,
      exam: exam ?? this.exam,
      assignment: assignment ?? this.assignment,
    );
  }

  @override
  AppAccents lerp(covariant AppAccents? other, double t) {
    if (other == null) return this;
    return AppAccents(
      practice: Color.lerp(practice, other.practice, t)!,
      learn: Color.lerp(learn, other.learn, t)!,
      exam: Color.lerp(exam, other.exam, t)!,
      assignment: Color.lerp(assignment, other.assignment, t)!,
    );
  }
}
