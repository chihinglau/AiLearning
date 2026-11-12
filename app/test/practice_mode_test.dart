import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/models/practice_mode.dart';
import 'package:ai_learning/core/models/practice_session.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('三种练习模式的默认配置互不相同', () {
    final special = practiceModeOf('special');
    final sync = practiceModeOf('sync');
    final preExam = practiceModeOf('pre_exam');

    expect(kPracticeModeOrder, ['special', 'sync', 'pre_exam']);
    expect({special.defaultCount, sync.defaultCount, preExam.defaultCount},
        {10, 15, 20});
    expect(preExam.defaultQTypes.contains('answer'), isTrue);
    expect(special.defaultQTypes.contains('answer'), isFalse);
    expect(sync.preferredScope, 'chapter');
    expect(preExam.preferredScope, 'textbook');
    expect(special.preferredScope, isNull);
    expect(
      {special.description, sync.description, preExam.description}.length,
      3,
    );
  });

  test('未知模式回退为专项突破', () {
    expect(practiceModeOf(null).key, 'special');
    expect(practiceModeOf('unknown').key, 'special');
  });

  test('组卷预览解析后端返回的模式策略', () {
    final preview = PracticePreview.fromJson({
      'count': 20,
      'available': 40,
      'insufficient': false,
      'estimated_minutes': 18,
      'kp_coverage': 1.0,
      'covered_kp_count': 4,
      'range_kp_count': 4,
      'q_type_mix': {'choice': 8},
      'due_review_count': 2,
      'seed': 42,
      'mode': 'pre_exam',
      'mode_label': '考前速练',
      'strategy': '全范围模拟卷',
    });
    expect(preview.mode, 'pre_exam');
    expect(preview.modeLabel, '考前速练');
    expect(preview.strategy, '全范围模拟卷');
    expect(practiceModeOf(preview.mode).label, '考前速练');
  });

  test('组卷预览兼容旧接口（无模式字段）', () {
    final preview = PracticePreview.fromJson({
      'count': 10,
      'available': 10,
      'insufficient': false,
      'estimated_minutes': 5,
      'kp_coverage': 1.0,
      'covered_kp_count': 2,
      'range_kp_count': 2,
      'q_type_mix': {},
      'due_review_count': 0,
      'seed': 1,
    });
    expect(preview.mode, 'special');
    expect(preview.modeLabel, '');
    expect(preview.strategy, '');
  });

  test('前置知识点按节序号 → 节内序号 → id 稳定排序', () {
    Map<String, dynamic> brief(
      int id,
      int sectionOrder,
      int orderIndex,
      String name,
    ) =>
        {
          'id': id,
          'name': name,
          'subject': 'chinese',
          'mastery_score': 0,
          'order_index': orderIndex,
          'section_order': sectionOrder,
          'section_name': '第$sectionOrder节',
          'has_explanation': true,
        };

    final raw = [
      brief(30, 2, 1, '第二节知识点'),
      brief(20, 1, 2, '第一节第2点'),
      brief(10, 1, 1, '第一节第1点'),
    ];
    final sorted = sortedPrerequisites(raw);
    expect(sorted.map((item) => item.id).toList(), [10, 20, 30]);
    expect(sorted.first.sectionName, '第1节');
    expect(sorted.first.hasExplanation, isTrue);
  });

  test('旧离线包缺排序字段时不会报错且顺序确定', () {
    final raw = [
      {'id': 9, 'name': '甲', 'subject': 'math'},
      {'id': 2, 'name': '乙', 'subject': 'math'},
    ];
    final sorted = sortedPrerequisites(raw);
    expect(sorted.map((item) => item.id).toList(), [2, 9]);
    expect(sorted.every((item) => item.orderIndex == 0), isTrue);
  });
}
