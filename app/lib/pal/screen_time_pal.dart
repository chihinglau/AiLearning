import 'package:ai_learning/core/constants/app_constants.dart';

abstract class ScreenTimePal {
  bool isCurfew(DateTime now);

  Future<int> todayUsageMinutes();
}

/// 合规红线：22:00 - 06:00 强制休息，跨零点时段需分段判断。
class CurfewScreenTimePal implements ScreenTimePal {
  const CurfewScreenTimePal({
    this.startHour = AppConfig.curfewStartHour,
    this.endHour = AppConfig.curfewEndHour,
  });

  final int startHour;
  final int endHour;

  @override
  bool isCurfew(DateTime now) {
    if (startHour > endHour) {
      return now.hour >= startHour || now.hour < endHour;
    }
    return now.hour >= startHour && now.hour < endHour;
  }

  @override
  Future<int> todayUsageMinutes() async {
    // 占位实现：M2 接入系统使用时长统计（Android UsageStats / HarmonyOS 应用使用统计）。
    return 0;
  }
}
