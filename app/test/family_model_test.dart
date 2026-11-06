import 'package:ai_learning/core/models/family.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('FamilyChild', () {
    test('fromJson 解析孩子摘要与家长控制项', () {
      final child = FamilyChild.fromJson({
        'id': 12,
        'nickname': '小明',
        'stage': 'primary',
        'grade': 3,
        'grade_group': 'primary_low',
        'is_child': true,
        'daily_limit_minutes': 90,
        'teen_mode': true,
      });

      expect(child.id, 12);
      expect(child.nickname, '小明');
      expect(child.stage, 'primary');
      expect(child.grade, 3);
      expect(child.gradeGroup, 'primary_low');
      expect(child.isChild, isTrue);
      expect(child.dailyLimitMinutes, 90);
      expect(child.teenMode, isTrue);
      expect(child.gradeLabel, '3 年级');
    });

    test('缺省值：120 分钟、未开启青少年模式、未设置年级', () {
      final child = FamilyChild.fromJson({'id': 5});

      expect(child.nickname, '孩子');
      expect(child.grade, isNull);
      expect(child.isChild, isFalse);
      expect(child.dailyLimitMinutes, 120);
      expect(child.teenMode, isFalse);
      expect(child.gradeLabel, '未设置年级');
    });
  });
}
