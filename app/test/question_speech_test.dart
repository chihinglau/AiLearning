import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/speech/question_speech.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('QuestionSpeech 读法规则', () {
    test('1. 分数：3/4 → 四分之三', () {
      expect(QuestionSpeech.normalize('3/4'), '四分之三');
    });

    test('2. 分数：1/2 → 二分之一', () {
      expect(QuestionSpeech.normalize('1/2'), '二分之一');
    });

    test('3. 分数：10/25 → 二十五分之十', () {
      expect(QuestionSpeech.normalize('10/25'), '二十五分之十');
    });

    test('4. 幂：x² → x 的平方', () {
      expect(QuestionSpeech.normalize('x²'), 'x 的平方');
    });

    test('5. 幂：x³ → x 的立方', () {
      expect(QuestionSpeech.normalize('x³'), 'x 的立方');
    });

    test('6. 幂：2⁴ → 2 的 4 次方', () {
      expect(QuestionSpeech.normalize('2⁴'), '2 的 4 次方');
    });

    test('7. 下标：a₁ → a 下标 1', () {
      expect(QuestionSpeech.normalize('a₁'), 'a 下标 1');
    });

    test('8. 运算符：÷ → 除以', () {
      expect(QuestionSpeech.normalize('12÷4'), '12除以4');
    });

    test('9. 运算符：× → 乘', () {
      expect(QuestionSpeech.normalize('3×5'), '3乘5');
    });

    test('10. 运算符：± → 正负', () {
      expect(QuestionSpeech.normalize('±5'), '正负5');
    });

    test('11. 运算符：≥ → 大于等于', () {
      expect(QuestionSpeech.normalize('a≥b'), 'a大于等于b');
    });

    test('12. 运算符：≤ → 小于等于', () {
      expect(QuestionSpeech.normalize('a≤b'), 'a小于等于b');
    });

    test('13. 单位：3cm → 三厘米', () {
      expect(QuestionSpeech.normalize('3cm'), '三厘米');
    });

    test('14. 单位：5kg → 五千克', () {
      expect(QuestionSpeech.normalize('5kg'), '五千克');
    });

    test('15. 单位：2L → 两升', () {
      expect(QuestionSpeech.normalize('2L'), '两升');
    });

    test('16. 填空线：____ → 空格', () {
      expect(QuestionSpeech.normalize('____'), '空格');
    });

    test('17. 选项：A. 三个苹果 → 选项 A，三个苹果', () {
      expect(QuestionSpeech.optionScript('A', '三个苹果'), '选项 A，三个苹果');
    });

    test('18. 组合：3/4 × 2cm = ____', () {
      expect(
        QuestionSpeech.normalize('3/4 × 2cm = ____'),
        '四分之三 乘 两厘米 等于 空格',
      );
    });

    test('19. 英语整句不改写', () {
      expect(
        QuestionSpeech.normalize('How many apples?'),
        'How many apples?',
      );
    });

    test('20. 幂等：清洗后的文本再次清洗不变', () {
      const raw = '3/4 × 2cm = ____';
      final once = QuestionSpeech.normalize(raw);
      expect(QuestionSpeech.normalize(once), once);
    });
  });

  group('QuestionSpeech.questionScript', () {
    test('题干与选项按「选项 X，」拼接', () {
      final script = QuestionSpeech.questionScript(
        stem: '3/4 是多少',
        options: const [
          QuestionOption(key: 'A', text: '1/2'),
          QuestionOption(key: 'B', text: '2/3'),
        ],
      );
      expect(script, '四分之三 是多少。选项 A，二分之一。选项 B，三分之二');
    });

    test('选项文本已带字母前缀时不重复朗读', () {
      expect(QuestionSpeech.optionScript('A', 'A. 三个'), '选项 A，三个');
    });

    test('空选项跳过', () {
      final script = QuestionSpeech.questionScript(
        stem: '2加3是多少',
        options: const [QuestionOption(key: 'A', text: '  ')],
      );
      expect(script, '2加3是多少');
    });
  });

  group('SpeechRules', () {
    test('规则版本为 1，供音频缓存键使用', () {
      expect(SpeechRules.version, 1);
    });
  });
}
