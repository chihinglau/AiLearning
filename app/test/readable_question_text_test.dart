import 'package:ai_learning/features/speech/readable_question_text.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('按中英文标点切句并保留标点', () {
    expect(
      ReadableQuestionText.splitSentences('第一句。第二句！没有标点'),
      ['第一句。', '第二句！', '没有标点'],
    );
    expect(
      ReadableQuestionText.splitSentences('What is this? It is a book.'),
      ['What is this?', ' It is a book.'],
    );
  });

  test('播放进度映射到题干句子，超出题干部分不返回句子', () {
    const lengths = [4, 5, 3];
    // 题干 12 字、朗读脚本 24 字 → 题干占比 0.5。
    expect(
      ReadableQuestionText.sentenceIndexFor(
        progress: 0.1,
        sentenceLengths: lengths,
        spokenLength: 24,
      ),
      0,
    );
    expect(
      ReadableQuestionText.sentenceIndexFor(
        progress: 0.3,
        sentenceLengths: lengths,
        spokenLength: 24,
      ),
      1,
    );
    expect(
      ReadableQuestionText.sentenceIndexFor(
        progress: 0.48,
        sentenceLengths: lengths,
        spokenLength: 24,
      ),
      2,
    );
    // 0.6 > 0.5，此时正在朗读选项。
    expect(
      ReadableQuestionText.sentenceIndexFor(
        progress: 0.6,
        sentenceLengths: lengths,
        spokenLength: 24,
      ),
      isNull,
    );
    expect(
      ReadableQuestionText.sentenceIndexFor(
        progress: null,
        sentenceLengths: lengths,
        spokenLength: 24,
      ),
      isNull,
    );
  });
}
