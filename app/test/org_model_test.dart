import 'package:ai_learning/core/models/org.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ClassSummary', () {
    test('fromJson 解析班级摘要', () {
      final item = ClassSummary.fromJson({
        'id': 8,
        'school_id': 3,
        'grade': 6,
        'name': '1 班',
        'head_teacher_id': 21,
        'school_year': '2026-2027',
        'member_count': 42,
      });

      expect(item.id, 8);
      expect(item.grade, 6);
      expect(item.name, '1 班');
      expect(item.memberCount, 42);
      expect(item.label, '6 年级 1 班');
    });
  });

  group('ClassStats', () {
    test('fromJson 解析聚合值与薄弱知识点', () {
      final stats = ClassStats.fromJson({
        'class_id': 8,
        'class_name': '1 班',
        'grade': 6,
        'subject': null,
        'student_count': 40,
        'active_student_count': 32,
        'submission_rate': 0.8,
        'total_answered': 1200,
        'accuracy': 0.825,
        'avg_mastery': 61.4,
        'weak_points': [
          {
            'knowledge_point_id': 101,
            'name': '分数乘法',
            'subject': 'math',
            'avg_mastery': 42.5,
          },
        ],
      });

      expect(stats.label, '6 年级 1 班');
      expect(stats.submissionRatePercent, '80%');
      expect(stats.accuracyPercent, '83%');
      expect(stats.avgMasteryText, '61');
      expect(stats.subjectLabel, '全部学科');
      expect(stats.weakPoints.single.name, '分数乘法');
      expect(stats.weakPoints.single.subjectLabel, '数学');
    });

    test('学科筛选时返回学科标签', () {
      final stats = ClassStats.fromJson({
        'class_id': 8,
        'class_name': '1 班',
        'grade': 6,
        'subject': 'english',
        'student_count': 0,
      });

      expect(stats.subjectLabel, '英语');
      expect(stats.submissionRatePercent, '0%');
      expect(stats.weakPoints, isEmpty);
    });
  });
}
