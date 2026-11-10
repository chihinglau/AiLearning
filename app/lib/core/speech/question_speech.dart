import 'package:ai_learning/core/models/content.dart';

/// 读题文本预处理规则（设计 §3.9.5，落地拆解见 §3.9.12）。
///
/// 纯 Dart 实现，不依赖 Flutter 与平台能力；服务端合成脚本（TT-03）
/// 复用同一份规则表。规则变更必须同步自增 [SpeechRules.version]，
/// 该版本号参与音频缓存键（TT-04）。
class SpeechRules {
  SpeechRules._();

  static const int version = 1;
}

/// 把题目文本转换成适合系统 TTS 朗读的口语文本。
class QuestionSpeech {
  QuestionSpeech._();

  static const List<String> _digits = [
    '零', '一', '二', '三', '四', '五', '六', '七', '八', '九',
  ];

  static const Map<String, String> _unitLabels = {
    'km': '千米',
    'cm': '厘米',
    'mm': '毫米',
    'kg': '千克',
    'ml': '毫升',
    'm': '米',
    'g': '克',
    'L': '升',
  };

  static const Map<String, String> _superscriptDigits = {
    '⁰': '0',
    '¹': '1',
    '²': '2',
    '³': '3',
    '⁴': '4',
    '⁵': '5',
    '⁶': '6',
    '⁷': '7',
    '⁸': '8',
    '⁹': '9',
  };

  static const Map<String, String> _subscriptDigits = {
    '₀': '0',
    '₁': '1',
    '₂': '2',
    '₃': '3',
    '₄': '4',
    '₅': '5',
    '₆': '6',
    '₇': '7',
    '₈': '8',
    '₉': '9',
  };

  static final RegExp _blankPattern = RegExp(r'[_＿]{2,}');
  static final RegExp _fractionPattern = RegExp(r'(\d+)\s*/\s*(\d+)');
  static final RegExp _unitPattern =
      RegExp(r'(\d+(?:\.\d+)?)\s*(km|cm|mm|kg|ml|m|g|L)');
  static final RegExp _superscriptPattern =
      RegExp('([0-9A-Za-z)\\)])([⁰¹²³⁴⁵⁶⁷⁸⁹]+)');
  static final RegExp _subscriptPattern =
      RegExp('([0-9A-Za-z)\\)])([₀₁₂₃₄₅₆₇₈₉]+)');
  static final RegExp _optionPrefixPattern =
      RegExp(r'(^|\n)[ \t]*([A-Za-z])[.、．]');
  static final RegExp _spacePattern = RegExp(r'\s+');

  /// 按 §3.9.12 的顺序清洗文本：填空线 → 分数 → 单位 → 幂/上下标 → 运算符 → 归一化。
  static String normalize(String text) {
    if (text.isEmpty) return text;
    var out = text;
    out = out.replaceAll(_blankPattern, '空格');
    out = out.replaceAllMapped(_fractionPattern, (match) {
      final numerator = int.tryParse(match.group(1)!) ?? 0;
      final denominator = int.tryParse(match.group(2)!) ?? 0;
      return '${toChineseNumber(denominator)}分之${toChineseNumber(numerator)}';
    });
    out = out.replaceAllMapped(_unitPattern, (match) {
      final label = _unitLabels[match.group(2)] ?? '';
      return '${_spokenNumber(match.group(1)!, liang: true)}$label';
    });
    out = out.replaceAllMapped(_superscriptPattern, (match) {
      final buffer = StringBuffer(match.group(1)!);
      for (final rune in match.group(2)!.runes) {
        final mark = String.fromCharCode(rune);
        buffer.write(switch (mark) {
          '²' => ' 的平方',
          '³' => ' 的立方',
          _ => ' 的 ${_superscriptDigits[mark]} 次方',
        });
      }
      return buffer.toString();
    });
    out = out.replaceAllMapped(_subscriptPattern, (match) {
      final digits = match
          .group(2)!
          .runes
          .map((rune) => _subscriptDigits[String.fromCharCode(rune)] ?? '')
          .join();
      return '${match.group(1)} 下标 $digits';
    });
    out = out
        .replaceAll('÷', '除以')
        .replaceAll('×', '乘')
        .replaceAll('±', '正负')
        .replaceAll('≥', '大于等于')
        .replaceAll('≤', '小于等于')
        .replaceAll('=', '等于');
    out = out.replaceAllMapped(
      _optionPrefixPattern,
      (match) => '${match.group(1)}选项 ${match.group(2)}，',
    );
    return out.replaceAll(_spacePattern, ' ').trim();
  }

  /// 单个选项的朗读文本：「选项 A，……」。已带字母前缀时先剥离，避免重复。
  static String optionScript(String key, String text) {
    final cleaned = normalize(text).replaceFirst(
      RegExp('^选项\\s*[A-Za-z]\\s*[，,]?\\s*'),
      '',
    );
    return '选项 $key，$cleaned';
  }

  /// 整题朗读文本：题干 + 逐项选项，句间断开。
  static String questionScript({
    required String stem,
    List<QuestionOption> options = const [],
  }) {
    final parts = <String>[normalize(stem)];
    for (final option in options) {
      if (option.text.trim().isEmpty) continue;
      parts.add(optionScript(option.key, option.text));
    }
    return parts.where((part) => part.isNotEmpty).join('。');
  }

  /// 阿拉伯数字转中文读法，覆盖 0–999；超出范围原样返回。
  static String toChineseNumber(int value) {
    if (value < 0 || value > 999) return value.toString();
    if (value < 10) return _digits[value];
    if (value < 20) {
      final rest = value % 10;
      return rest == 0 ? '十' : '十${_digits[rest]}';
    }
    if (value < 100) {
      final tens = value ~/ 10;
      final rest = value % 10;
      return rest == 0 ? '${_digits[tens]}十' : '${_digits[tens]}十${_digits[rest]}';
    }
    final hundreds = value ~/ 100;
    final rest = value % 100;
    if (rest == 0) return '${_digits[hundreds]}百';
    if (rest < 10) return '${_digits[hundreds]}百零${_digits[rest]}';
    return '${_digits[hundreds]}百${toChineseNumber(rest)}';
  }

  static String _spokenNumber(String raw, {bool liang = false}) {
    final dot = raw.indexOf('.');
    if (dot < 0) {
      final value = int.tryParse(raw) ?? 0;
      if (liang && value == 2) return '两';
      return toChineseNumber(value);
    }
    final whole = int.tryParse(raw.substring(0, dot)) ?? 0;
    final decimals = raw
        .substring(dot + 1)
        .split('')
        .map((digit) => _digits[int.tryParse(digit) ?? 0])
        .join();
    final wholeText = whole == 0 ? '零' : toChineseNumber(whole);
    return '$wholeText点$decimals';
  }
}
