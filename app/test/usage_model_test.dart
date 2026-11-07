import 'package:ai_learning/core/models/usage.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('DailyUsage 解析时长与解锁时间', () {
    final usage = DailyUsage.fromJson({
      'daily_limit_minutes': 120,
      'used_minutes': 120,
      'remaining_minutes': 0,
      'limited': true,
      'unlocks_at': '2026-11-07T16:00:00',
    });

    expect(usage.dailyLimitMinutes, 120);
    expect(usage.usedMinutes, 120);
    expect(usage.remainingMinutes, 0);
    expect(usage.limited, isTrue);
    expect(usage.unlocksAt, isNotNull);
  });

  test('DailyUsage 未启用限额时剩余为空', () {
    final usage = DailyUsage.fromJson({
      'daily_limit_minutes': 0,
      'used_minutes': 0,
      'remaining_minutes': null,
      'limited': false,
      'unlocks_at': null,
    });

    expect(usage.remainingMinutes, isNull);
    expect(usage.limited, isFalse);
    expect(usage.unlocksAt, isNull);
  });
}
