import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/offline/offline_grader.dart';
import 'package:flutter_test/flutter_test.dart';

Question _question(Map<String, dynamic>? answer, {String qType = 'choice'}) {
  return Question(
    id: 1,
    chapterId: 1,
    subject: 'math',
    qType: qType,
    stem: '题干',
    answer: answer,
  );
}

void main() {
  test('单选答案匹配', () {
    final question = _question({'value': 'A'});
    expect(OfflineGrader.grade(question, {'value': 'A'}), true);
    expect(OfflineGrader.grade(question, {'value': 'B'}), false);
  });

  test('多选答案顺序无关', () {
    final question = _question({
      'value': ['A', 'C'],
    }, qType: 'multiple');
    expect(
      OfflineGrader.grade(question, {
        'value': ['C', 'A'],
      }),
      true,
    );
  });

  test('填空忽略空白与中英文标点', () {
    final question = _question({'value': ['（3，4）']}, qType: 'fill');
    expect(
      OfflineGrader.grade(question, {'value': ' (3, 4) '}),
      true,
    );
  });

  test('缺少答案时返回 null', () {
    expect(OfflineGrader.grade(_question(null), {'value': 'A'}), isNull);
  });
}
