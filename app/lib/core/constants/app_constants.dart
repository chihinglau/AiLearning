/// 学科 / 学段 / 全局配置常量。
library;

enum Subject {
  chinese('chinese', '语文'),
  math('math', '数学'),
  english('english', '英语'),
  physics('physics', '物理'),
  chemistry('chemistry', '化学'),
  biology('biology', '生物'),
  history('history', '历史'),
  geography('geography', '地理'),
  politics('politics', '政治');

  const Subject(this.code, this.label);

  final String code;
  final String label;

  static Subject fromCode(String code) {
    return values.firstWhere((item) => item.code == code, orElse: () => Subject.math);
  }
}

enum Stage {
  primary('primary', '小学'),
  junior('junior', '初中'),
  senior('senior', '高中');

  const Stage(this.code, this.label);

  final String code;
  final String label;

  static Stage? fromCode(String? code) {
    if (code == null) return null;
    for (final stage in values) {
      if (stage.code == code) return stage;
    }
    return null;
  }
}

class AppConfig {
  AppConfig._();

  /// 可通过 `flutter run --dart-define=API_BASE_URL=http://x.x.x.x:18080` 覆盖。
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:18080',
  );

  /// 深圳本地化教材版本。
  static const List<String> shenzhenTextbookVersions = ['人教版', '粤教版', '牛津深圳版'];

  /// 合规：22:00 - 06:00 强制休息，未成年账号默认每日 120 分钟。
  static const int curfewStartHour = 22;
  static const int curfewEndHour = 6;
  static const int defaultDailyLimitMinutes = 120;
}
