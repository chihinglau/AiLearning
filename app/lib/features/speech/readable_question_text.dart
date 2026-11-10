import 'dart:async';

import 'package:ai_learning/core/providers.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 题干展示（TT-06）：预生成音频播放时按句高亮，英语单词可点读。
///
/// 高亮按「朗读文本字符占比 × 播放进度」估算，不是字级时间戳，
/// 因此仅用于阅读引导；[spokenText] 为实际朗读脚本（含选项），
/// 用于把播放进度映射到题干句子上。
class ReadableQuestionText extends ConsumerStatefulWidget {
  const ReadableQuestionText({
    super.key,
    required this.text,
    this.spokenText,
    this.language = 'zh-CN',
    this.style,
  });

  /// 题干原文（展示用）。
  final String text;

  /// 实际朗读脚本（含选项前缀）；为空时按 [text] 估算。
  final String? spokenText;

  /// 中文题 `zh-CN`，英语题 `en-US`（启用单词点读）。
  final String language;

  final TextStyle? style;

  /// 按中英文标点切句，保留标点。
  static List<String> splitSentences(String text) {
    const delimiters = '。！？!?；;';
    final sentences = <String>[];
    final buffer = StringBuffer();
    for (final rune in text.runes) {
      final char = String.fromCharCode(rune);
      buffer.write(char);
      if (delimiters.contains(char)) {
        sentences.add(buffer.toString());
        buffer.clear();
      }
    }
    final rest = buffer.toString();
    if (rest.isNotEmpty) sentences.add(rest);
    return sentences;
  }

  /// 播放进度对应的句子下标；进度超出题干部分（正在读选项）返回 null。
  static int? sentenceIndexFor({
    required double? progress,
    required List<int> sentenceLengths,
    required int spokenLength,
  }) {
    if (progress == null || sentenceLengths.isEmpty) return null;
    final total = sentenceLengths.fold<int>(0, (sum, item) => sum + item);
    if (total == 0) return null;
    final share = spokenLength <= 0 ? 1.0 : (total / spokenLength).clamp(0.0, 1.0);
    if (progress > share) return null;
    final ratio = share <= 0 ? 0.0 : (progress / share).clamp(0.0, 1.0);
    final target = ratio * total;
    var cumulative = 0;
    for (var index = 0; index < sentenceLengths.length; index++) {
      cumulative += sentenceLengths[index];
      if (target <= cumulative) return index;
    }
    return sentenceLengths.length - 1;
  }

  @override
  ConsumerState<ReadableQuestionText> createState() =>
      _ReadableQuestionTextState();
}

class _Token {
  const _Token(this.text, this.sentence, {this.word});

  final String text;
  final int sentence;
  final String? word;
}

class _ReadableQuestionTextState extends ConsumerState<ReadableQuestionText> {
  static final _wordPattern = RegExp(r"[A-Za-z][A-Za-z'’\-]*");

  List<_Token> _tokens = const [];
  List<int> _sentenceLengths = const [];
  final Map<int, TapGestureRecognizer> _recognizers = {};

  @override
  void initState() {
    super.initState();
    _rebuild();
  }

  @override
  void didUpdateWidget(covariant ReadableQuestionText oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.text != widget.text ||
        oldWidget.language != widget.language) {
      _rebuild();
    }
  }

  @override
  void dispose() {
    _disposeRecognizers();
    super.dispose();
  }

  void _disposeRecognizers() {
    for (final recognizer in _recognizers.values) {
      recognizer.dispose();
    }
    _recognizers.clear();
  }

  void _rebuild() {
    _disposeRecognizers();
    final sentences = ReadableQuestionText.splitSentences(widget.text);
    final tokens = <_Token>[];
    final lengths = <int>[];
    final tapWords = widget.language == 'en-US';
    for (var index = 0; index < sentences.length; index++) {
      final sentence = sentences[index];
      lengths.add(sentence.length);
      if (!tapWords) {
        tokens.add(_Token(sentence, index));
        continue;
      }
      var last = 0;
      for (final match in _wordPattern.allMatches(sentence)) {
        if (match.start > last) {
          tokens.add(_Token(sentence.substring(last, match.start), index));
        }
        tokens.add(_Token(match.group(0)!, index, word: match.group(0)));
        last = match.end;
      }
      if (last < sentence.length) {
        tokens.add(_Token(sentence.substring(last), index));
      }
    }
    _tokens = tokens;
    _sentenceLengths = lengths;
  }

  TapGestureRecognizer _recognizer(int index, String word) {
    return _recognizers.putIfAbsent(
      index,
      () => TapGestureRecognizer()..onTap = () => unawaited(_speakWord(word)),
    );
  }

  Future<void> _speakWord(String word) async {
    final speed = await ref.read(speechSettingsStoreProvider).speed();
    try {
      await ref.read(questionAudioServiceProvider).stop();
      await ref.read(ttsServiceProvider).speak(
            word,
            language: 'en-US',
            speed: speed,
          );
    } catch (_) {
      // 设备不支持朗读时忽略。
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final progress = ref.watch(questionAudioServiceProvider).progress;
    return ValueListenableBuilder<double?>(
      valueListenable: progress,
      builder: (context, value, _) {
        final current = ReadableQuestionText.sentenceIndexFor(
          progress: value,
          sentenceLengths: _sentenceLengths,
          spokenLength: (widget.spokenText ?? widget.text).length,
        );
        final highlight = TextStyle(
          backgroundColor: theme.colorScheme.primary.withValues(alpha: 0.16),
        );
        return Text.rich(
          TextSpan(
            children: [
              for (var index = 0; index < _tokens.length; index++)
                _spanFor(index, current, highlight),
            ],
          ),
          style: widget.style,
        );
      },
    );
  }

  InlineSpan _spanFor(int index, int? current, TextStyle highlight) {
    final token = _tokens[index];
    final word = token.word;
    final style = token.sentence == current ? highlight : null;
    if (word == null) {
      return TextSpan(text: token.text, style: style);
    }
    return TextSpan(
      text: token.text,
      style: style,
      recognizer: _recognizer(index, word),
      mouseCursor: SystemMouseCursors.click,
    );
  }
}
