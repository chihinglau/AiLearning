/// 读题（TTS）开放范围判定，集中一处，避免各页面各写一份门禁。
///
/// 口径（设计 §3.9.1 + CR-007 扩展）：
/// - 低年级（1–3 年级）语文 / 数学 / 英语：题干与选项朗读（识字量不足需要代读）；
/// - 英语全年级：题面本身就是外语，任何年级都需要朗读辅助理解与正音；
/// - 4–9 年级语文 / 数学及其他学科：不开放（题干可自主阅读，避免课堂外放干扰）；
///   要放开须走 CR 评估，不要在各页面私自放宽。
class SpeechPolicy {
  SpeechPolicy._();

  static const Set<String> _lowerGradeSubjects = {'chinese', 'math', 'english'};

  /// 是否对该年级 + 科目开放读题入口。
  static bool enabled({required int? grade, required String? subject}) {
    final s = (subject ?? '').trim().toLowerCase();
    if (s.isEmpty) return false;
    // 英语全年级开放，不受年级门禁限制。
    if (s == 'english') return true;
    if (grade == null || grade < 1 || grade > 3) return false;
    return _lowerGradeSubjects.contains(s);
  }

  /// 该年级是否默认自动读题（仅低年级；英语高年级手动触发）。
  static bool autoReadByDefault({required int? grade}) {
    if (grade == null) return false;
    return grade >= 1 && grade <= 3;
  }
}
