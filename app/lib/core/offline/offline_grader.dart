import 'package:ai_learning/core/models/content.dart';

/// 本地判分，规则与后端 `learning.grade_answer` 保持一致。
///
/// 客观题（选择/判断/填空）仍按归一化后全等比较；主观题
/// （解答/计算/习作）改为「关键内容覆盖」判分，学生表述与参考答案
/// 不完全一致（如只写要点、换用数学符号）也能判对。
class OfflineGrader {
  /// 主观题题型：参考答案多为「示例：…」式完整表述，全等比较等于永远判错。
  static const _subjectiveTypes = {
    'answer',
    'calc',
    'composition',
    'essay',
    'writing',
  };

  /// 参考答案前缀引导语（「示例：」「参考答案：」等）不参与匹配。
  static const _answerPrefixes = [
    '参考答案',
    '正确答案',
    '评分要点',
    '评分标准',
    '参考',
    '示例',
    '例如',
    '答案',
  ];

  /// 虚词：不作为关键词，也不参与汉字二元组。
  static const _stopChars = '的了是在和与及或也就都而又把被对从向这那其之并且则于等吗呢吧啊很更最将已';

  static const _powerWords = {
    '四次方': '4',
    '三次方': '3',
    '平方': '2',
    '立方': '3',
  };

  static const _superscripts = {
    '⁰': '0',
    '¹': '1',
    '²': '2',
    '³': '3',
    '⁴': '4',
    '⁵': '5',
  };

  static final _latinRun = RegExp(r'[0-9a-z]+');
  static final _cjkRun = RegExp(r'[\u4e00-\u9fff]+');
  static final _nonWord = RegExp(r'[^0-9a-z\u4e00-\u9fff]+');

  /// 参考答案关键词过少（是/否、单值）时不做宽松判分。
  static const _minUnits = 5;

  /// 关键词覆盖率阈值，与后端一致（主观题二元对错，取偏宽松口径）。
  static const _hitRatio = 0.5;

  /// 作答长度下限（相对参考答案），避免只写一两个词就判对。
  static const _minLengthRatio = 0.3;

  static String _normalize(dynamic value) {
    if (value is List) {
      final parts = value.map(_normalize).toList()..sort();
      return parts.join('|');
    }
    var text = value.toString().trim().toLowerCase();
    text = text.replaceAll(RegExp(r'[ \t\u3000]'), '');
    return text.replaceAll('，', ',').replaceAll('（', '(').replaceAll('）', ')');
  }

  /// 返回 null 表示该题缺少答案（离线包不完整），调用方应跳过本地判定。
  static bool? grade(Question question, Map<String, dynamic> userAnswer) {
    final expected = question.answer?['value'];
    final actual = userAnswer['value'];
    if (expected == null || actual == null) return null;
    // 多选题：标准答案可能是列表或 "A|C" 形式，做整体等价比较。
    if (expected is List && actual is List) {
      return _normalize(actual) == _normalize(expected);
    }
    if (actual is List) {
      return _normalize(expected) == _normalize(actual);
    }
    // 主观题：按关键内容覆盖判分，避免「必须逐字相同」。
    if (_subjectiveTypes.contains(question.qType)) {
      return _gradeSubjective(expected, actual);
    }
    // 填空题：标准答案可为「可接受答案列表」，任意匹配即可。
    if (expected is List) {
      return expected.any((item) => _normalize(actual) == _normalize(item));
    }
    return _normalize(expected) == _normalize(actual);
  }

  // ------------------------------------------------------------------
  // 主观题关键内容覆盖判分（与后端 learning.py 同规则）
  // ------------------------------------------------------------------

  static String _clean(String text) {
    var s = text.trim().toLowerCase();
    s = s.replaceAll(RegExp(r'[ \t\u3000]'), '');
    _powerWords.forEach((word, power) => s = s.replaceAll(word, power));
    _superscripts.forEach((sup, digit) => s = s.replaceAll(sup, digit));
    s = s.replaceAll(_nonWord, '');
    var changed = true;
    while (changed) {
      changed = false;
      for (final prefix in _answerPrefixes) {
        if (s.startsWith(prefix) && s.length > prefix.length + 1) {
          s = s.substring(prefix.length);
          changed = true;
        }
      }
    }
    return s;
  }

  /// 二元组（权重 2）+ 字母数字词（权重 1），近似「主谓宾」。
  static Map<String, int> _keywordUnits(String text) {
    final units = <String, int>{};
    for (final match in _cjkRun.allMatches(text)) {
      final kept = match.group(0)!.split('').where((ch) => !_stopChars.contains(ch)).join();
      if (kept.length <= 1) {
        if (kept.isNotEmpty) units[kept] = 2;
      } else {
        for (var i = 0; i < kept.length - 1; i++) {
          units[kept.substring(i, i + 2)] = 2;
        }
      }
    }
    for (final match in _latinRun.allMatches(text)) {
      units[match.group(0)!] = 1;
    }
    return units;
  }

  /// 单字关键词（去虚词），覆盖「学生只写要点名词」的作答。
  static Map<String, int> _charUnits(String text) {
    final units = <String, int>{};
    for (final match in _cjkRun.allMatches(text)) {
      for (final ch in match.group(0)!.split('')) {
        if (!_stopChars.contains(ch)) units[ch] = 2;
      }
    }
    for (final match in _latinRun.allMatches(text)) {
      units[match.group(0)!] = 1;
    }
    return units;
  }

  static String _symbolSignature(String text) {
    return text.split('').where((ch) => !_isCjk(ch)).join();
  }

  static bool _isCjk(String ch) {
    final code = ch.codeUnitAt(0);
    return code >= 0x4e00 && code <= 0x9fff;
  }

  static double _coverage(Map<String, int> expected, Map<String, int> actual) {
    final total = expected.values.fold<int>(0, (sum, v) => sum + v);
    if (total == 0 || actual.isEmpty) return 0;
    var hit = 0;
    expected.forEach((unit, weight) {
      if (actual.containsKey(unit)) hit += weight;
    });
    return hit / total;
  }

  /// 0~1 的关键内容覆盖率（1 = 完全覆盖）。
  static double subjectiveScore(dynamic expected, dynamic actual) {
    final e = _clean(expected.toString());
    final a = _clean(actual.toString());
    if (e.isEmpty || a.isEmpty) return 0;
    if (e == a) return 1;
    // 数学式等价：a²+b²=c² ↔ a的平方加b的平方等于c的平方
    final eSymbols = _symbolSignature(e);
    if (eSymbols.length >= 2 && eSymbols == _symbolSignature(a)) return 1;
    final bigram = _coverage(_keywordUnits(e), _keywordUnits(a));
    final unigram = _coverage(_charUnits(e), _charUnits(a));
    return bigram > unigram ? bigram : unigram;
  }

  static bool _gradeSubjective(dynamic expected, dynamic actual) {
    if (expected is List) {
      return expected.any((item) => _gradeSubjective(item, actual));
    }
    final e = _clean(expected.toString());
    final a = _clean(actual.toString());
    if (e.isEmpty || a.isEmpty) return false;
    if (_keywordUnits(e).length < _minUnits) {
      // 参考答案太短（是/否、单个数值）→ 保持全等，宽松会把是非题放水。
      return _normalize(expected) == _normalize(actual);
    }
    final eSymbols = _symbolSignature(e);
    if (a == e || (eSymbols.length >= 2 && eSymbols == _symbolSignature(a))) {
      return true;
    }
    final minLength = (e.length * _minLengthRatio).floor();
    if (a.length < (minLength < 2 ? 2 : minLength)) return false;
    return subjectiveScore(e, a) >= _hitRatio;
  }
}
