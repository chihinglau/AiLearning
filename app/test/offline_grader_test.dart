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

  group('主观题按关键内容覆盖判分（与后端同规则）', () {
    final gougu = _question(
      {'value': '示例：a 的平方加 b 的平方等于 c 的平方'},
      qType: 'answer',
    );

    test('数学符号写法与文字表述等价', () {
      expect(OfflineGrader.grade(gougu, {'value': 'a²+b²=c²'}), true);
      expect(OfflineGrader.grade(gougu, {'value': 'a的平方+b的平方=c的平方'}), true);
    });

    test('照抄结论句判对', () {
      expect(
        OfflineGrader.grade(gougu, {'value': 'a 的平方加 b 的平方等于 c 的平方'}),
        true,
      );
    });

    test('跑题答案判错', () {
      expect(OfflineGrader.grade(gougu, {'value': '三角形内角和等于 180 度'}), false);
      expect(OfflineGrader.grade(gougu, {'value': '不知道'}), false);
    });

    test('只写对一半要点仍判错', () {
      final bio = _question(
        {'value': '示例：大气圈的底部、水圈的大部、岩石圈的表面。'},
        qType: 'answer',
      );
      expect(OfflineGrader.grade(bio, {'value': '大气圈、水圈、岩石圈'}), true);
      expect(OfflineGrader.grade(bio, {'value': '大气圈和水圈'}), false);
    });

    test('参考答案过短时退回全等比较', () {
      final short = _question({'value': '是'}, qType: 'answer');
      expect(OfflineGrader.grade(short, {'value': '是'}), true);
      expect(OfflineGrader.grade(short, {'value': '是的'}), false);
    });
  });
}
