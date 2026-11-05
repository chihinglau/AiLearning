import 'package:ai_learning/core/models/user.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('AppUser.fromJson 解析后端字段', () {
    final user = AppUser.fromJson({
      'id': 7,
      'phone': '13900000000',
      'nickname': '小明',
      'role': 'student',
      'stage': 'primary',
      'grade': 3,
      'is_child': true,
      'daily_limit_minutes': 90,
    });

    expect(user.id, 7);
    expect(user.nickname, '小明');
    expect(user.grade, 3);
    expect(user.isChild, isTrue);
    expect(user.dailyLimitMinutes, 90);
    expect(user.isStudent, isTrue);
  });
}
