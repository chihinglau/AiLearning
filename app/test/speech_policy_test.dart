import 'package:ai_learning/core/speech/speech_policy.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('SpeechPolicy.enabled', () {
    test('低年级语文/数学/英语开放', () {
      for (final grade in [1, 2, 3]) {
        for (final subject in ['chinese', 'math', 'english']) {
          expect(
            SpeechPolicy.enabled(grade: grade, subject: subject),
            isTrue,
            reason: 'grade=$grade subject=$subject 应开放读题',
          );
        }
      }
    });

    test('英语全年级开放（4–9 年级不再被年级门禁挡住）', () {
      for (var grade = 4; grade <= 9; grade++) {
        expect(
          SpeechPolicy.enabled(grade: grade, subject: 'english'),
          isTrue,
          reason: 'grade=$grade 的英语应可读题',
        );
      }
    });

    test('4–9 年级语文/数学不开放', () {
      for (var grade = 4; grade <= 9; grade++) {
        expect(SpeechPolicy.enabled(grade: grade, subject: 'chinese'), isFalse);
        expect(SpeechPolicy.enabled(grade: grade, subject: 'math'), isFalse);
      }
    });

    test('其他学科不开放', () {
      for (final subject in ['physics', 'chemistry', 'history', 'geography']) {
        expect(SpeechPolicy.enabled(grade: 1, subject: subject), isFalse);
        expect(SpeechPolicy.enabled(grade: 8, subject: subject), isFalse);
      }
    });

    test('科目为空或 null 不开放；grade 为空时英语仍开放', () {
      expect(SpeechPolicy.enabled(grade: 1, subject: null), isFalse);
      expect(SpeechPolicy.enabled(grade: 1, subject: ''), isFalse);
      expect(SpeechPolicy.enabled(grade: 1, subject: '  '), isFalse);
      expect(SpeechPolicy.enabled(grade: null, subject: 'english'), isTrue);
      expect(SpeechPolicy.enabled(grade: null, subject: 'chinese'), isFalse);
    });

    test('科目大小写与空白容错', () {
      expect(SpeechPolicy.enabled(grade: 6, subject: 'English'), isTrue);
      expect(SpeechPolicy.enabled(grade: 6, subject: ' english '), isTrue);
    });
  });

  group('SpeechPolicy.autoReadByDefault', () {
    test('仅 1–3 年级默认自动读题', () {
      expect(SpeechPolicy.autoReadByDefault(grade: 1), isTrue);
      expect(SpeechPolicy.autoReadByDefault(grade: 3), isTrue);
      expect(SpeechPolicy.autoReadByDefault(grade: 4), isFalse);
      expect(SpeechPolicy.autoReadByDefault(grade: null), isFalse);
    });
  });
}
