import 'package:ai_learning/core/models/content.dart';

/// 本地判分，规则与后端 `learning.grade_answer` 保持一致。
class OfflineGrader {
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
    // 填空题：标准答案可为「可接受答案列表」，任意匹配即可。
    if (expected is List) {
      return expected.any((item) => _normalize(actual) == _normalize(item));
    }
    return _normalize(expected) == _normalize(actual);
  }
}
