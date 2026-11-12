/// 首页「待办考试」入口的纯逻辑（D-04 §8.7.2），便于单测覆盖。
library;

const Map<String, String> kExamTypeLabels = <String, String>{
  'unit': '单元测',
  'midterm': '期中考试',
  'final': '期末考试',
  'mock': '模拟考',
  'past_paper': '历年真题',
};

/// 返回待办考试卡的跳转路由；窗口已关闭时返回 null（由调用方给提示）。
String? pendingExamRoute(Map<String, dynamic> item) {
  if (item['window_state']?.toString() == 'closed') return null;
  if (item['entry']?.toString() == 'past_paper') return '/past-papers';
  final id = item['exam_id'];
  if (id is int) return '/exam/$id';
  if (id is String && int.tryParse(id) != null) return '/exam/$id';
  return '/exams';
}

/// 待办考试卡副标题：考试类型 · 学科 · 窗口状态。
String pendingExamSubtitle(Map<String, dynamic> item) {
  final rawType = item['exam_type']?.toString();
  final parts = <String>[
    if (rawType != null && rawType.isNotEmpty)
      kExamTypeLabels[rawType] ?? rawType,
  ];
  final subject = item['subject']?.toString();
  if (subject != null && subject.isNotEmpty) parts.add(subject);
  final state = item['window_state']?.toString();
  if (state == 'scheduled') parts.add('尚未开始');
  if (state == 'open') parts.add('点击进卷');
  if (state == 'closed') parts.add('已结束');
  return parts.isEmpty ? '待办考试' : parts.join(' · ');
}
