import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:ai_learning/core/models/textbook_binding.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('TextbookBinding', () {
    test('fromJson 解析教材、学期与年级不一致标记', () {
      final binding = TextbookBinding.fromJson({
        'id': 5,
        'subject': 'english',
        'semester': 'second',
        'source': 'manual',
        'is_primary': true,
        'status': 'active',
        'mismatch': true,
        'textbook': {
          'id': 9,
          'subject': 'english',
          'grade': 4,
          'version': '牛津深圳版',
          'semester': 'second',
        },
      });

      expect(binding.subjectLabel, '英语');
      expect(binding.semester, 'second');
      expect(binding.isPrimary, isTrue);
      expect(binding.mismatch, isTrue);
      expect(binding.textbook.displayName, '英语 4年级 · 牛津深圳版 · 下册');
    });
  });

  group('TextbookRecommendation', () {
    test('fromJson 解析地区与学科推荐', () {
      final recommendation = TextbookRecommendation.fromJson({
        'grade': 3,
        'semester': 'first',
        'region': 'shenzhen',
        'subjects': [
          {
            'subject': 'chinese',
            'textbook_id': 2,
            'version': '人教版',
            'grade': 3,
          },
        ],
      });

      expect(recommendation.region, 'shenzhen');
      expect(recommendation.semester, 'first');
      expect(recommendation.subjects.first.subjectLabel, '语文');
      expect(recommendation.subjects.first.textbookId, 2);
    });
  });

  group('学段映射', () {
    test('stageForGrade 覆盖小学/初中/高中边界', () {
      expect(stageForGrade(1), Stage.primary);
      expect(stageForGrade(6), Stage.primary);
      expect(stageForGrade(7), Stage.junior);
      expect(stageForGrade(9), Stage.junior);
      expect(stageForGrade(10), Stage.senior);
      expect(stageForGrade(12), Stage.senior);
    });

    test('gradesForStage 返回对应年级区间', () {
      expect(gradesForStage(Stage.primary), [1, 2, 3, 4, 5, 6]);
      expect(gradesForStage(Stage.junior), [7, 8, 9]);
      expect(gradesForStage(Stage.senior), [10, 11, 12]);
    });
  });
}
