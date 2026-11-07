/// 今日学习时长与青少年模式额度（R-04）。
class DailyUsage {
  const DailyUsage({
    required this.dailyLimitMinutes,
    required this.usedMinutes,
    this.remainingMinutes,
    this.limited = false,
    this.unlocksAt,
  });

  final int dailyLimitMinutes;
  final int usedMinutes;
  final int? remainingMinutes;
  final bool limited;
  final DateTime? unlocksAt;

  factory DailyUsage.fromJson(Map<String, dynamic> json) {
    final unlocks = json['unlocks_at'] as String?;
    return DailyUsage(
      dailyLimitMinutes: (json['daily_limit_minutes'] as num?)?.toInt() ?? 0,
      usedMinutes: (json['used_minutes'] as num?)?.toInt() ?? 0,
      remainingMinutes: (json['remaining_minutes'] as num?)?.toInt(),
      limited: json['limited'] as bool? ?? false,
      unlocksAt: unlocks == null ? null : DateTime.tryParse(unlocks),
    );
  }
}
