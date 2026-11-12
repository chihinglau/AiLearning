import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/models/exam_entry.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('pendingExamRoute', () {
    test('普通考试直达试卷详情', () {
      expect(
        pendingExamRoute({'exam_id': 7, 'window_state': 'open'}),
        '/exam/7',
      );
    });

    test('字符串 exam_id 兼容旧离线包', () {
      expect(
        pendingExamRoute({'exam_id': '12', 'window_state': 'scheduled'}),
        '/exam/12',
      );
    });

    test('真题走真题库，不进入通用考试详情', () {
      expect(
        pendingExamRoute({
          'exam_id': 3,
          'entry': 'past_paper',
          'window_state': 'open',
        }),
        '/past-papers',
      );
    });

    test('窗口关闭不跳转', () {
      expect(
        pendingExamRoute({'exam_id': 4, 'window_state': 'closed'}),
        isNull,
      );
    });

    test('缺少 exam_id 回退考试中心', () {
      expect(pendingExamRoute({}), '/exams');
      expect(pendingExamRoute({'exam_id': 'abc'}), '/exams');
    });
  });

  group('pendingExamSubtitle', () {
    test('包含考试类型、学科与窗口状态', () {
      final text = pendingExamSubtitle({
        'exam_type': 'final',
        'subject': 'math',
        'window_state': 'open',
      });
      expect(text, contains('期末考试'));
      expect(text, contains('math'));
      expect(text, contains('点击进卷'));
    });

    test('旧数据缺字段不抛异常', () {
      expect(pendingExamSubtitle({}), '待办考试');
    });
  });

  group('考试入库模型', () {
    test('ExamBlueprint.fromJson 容错', () {
      final blueprint = ExamBlueprint.fromJson({
        'code': 'math_g1_unit',
        'name': '一年级数学单元测',
        'subject': 'math',
        'grade': 1,
        'exam_type': 'unit',
        'total_score': 100,
        'time_limit_min': 40,
      });
      expect(blueprint.code, 'math_g1_unit');
      expect(blueprint.timeLimitMin, 40);
      expect(ExamBlueprint.fromJson({}).totalScore, 100);
    });

    test('ExamGenerateResult.fromJson 数值与难度分布容错', () {
      final result = ExamGenerateResult.fromJson({
        'exam_id': 9,
        'title': '一年级数学单元测',
        'seed': 42,
        'question_count': 12,
        'total_score': 100.0,
        'kp_coverage': 0.85,
        'difficulty_mix': {'easy': 6, 'medium': 6},
        'fallback_count': 1,
        'insufficient': false,
      });
      expect(result.examId, 9);
      expect(result.questionCount, 12);
      expect(result.difficultyMix, {'easy': 6, 'medium': 6});
      expect(ExamGenerateResult.fromJson({}).difficultyMix, isEmpty);
    });
  });
}
