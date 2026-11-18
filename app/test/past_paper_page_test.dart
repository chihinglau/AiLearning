import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/exam_service.dart';
import 'package:ai_learning/features/exam/past_paper_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

ExamSummary _paper({
  required int id,
  required String title,
  required String subject,
  required int year,
  required String region,
}) {
  return ExamSummary(
    id: id,
    title: title,
    subject: subject,
    grade: 1,
    year: year,
    examType: 'mock',
    totalScore: 100,
    timeLimitMin: 60,
    questionCount: 10,
    category: 'available',
    windowState: 'open',
    region: region,
    isPastPaper: true,
  );
}

/// 模拟真题库服务端：筛选项独立下发，列表按全部参数过滤。
class _FakeExamService extends ExamService {
  _FakeExamService() : super(ApiClient());

  final List<Map<String, String?>> calls = [];

  static final _items = [
    _paper(
      id: 1,
      title: '深圳市一年级数学期末真题（2025）',
      subject: 'math',
      year: 2025,
      region: '深圳',
    ),
    _paper(
      id: 2,
      title: '深圳市一年级语文期末真题（2024）',
      subject: 'chinese',
      year: 2024,
      region: '深圳',
    ),
  ];

  @override
  Future<PastPaperFilters> pastPaperFilters() async => const PastPaperFilters(
        years: [2025, 2024],
        subjects: ['chinese', 'english', 'math'],
        regions: ['深圳'],
        grades: [1],
        examTypes: ['mock'],
      );

  @override
  Future<List<ExamSummary>> pastPapers({
    String? subject,
    int? year,
    String? region,
    int? grade,
    String? examType,
    String? attemptStatus,
    String? query,
    int? page,
    int? pageSize,
  }) async {
    calls.add({
      'subject': subject,
      'year': year == null ? null : '$year',
      'region': region,
      'attempt_status': attemptStatus,
    });
    return _items.where((item) {
      if (subject != null && item.subject != subject) return false;
      if (year != null && item.year != year) return false;
      if (region != null && item.region != region) return false;
      if (query != null && !item.title.contains(query)) return false;
      return true;
    }).toList();
  }
}

Widget _app(_FakeExamService service) {
  return ProviderScope(
    overrides: [examServiceProvider.overrideWithValue(service)],
    child: const MaterialApp(home: PastPaperPage()),
  );
}

void main() {
  testWidgets('真题库按学科与年份筛选（服务端）并展示来源', (tester) async {
    tester.view.physicalSize = const Size(900, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final service = _FakeExamService();
    await tester.pumpWidget(_app(service));
    await tester.pumpAndSettle();

    expect(find.text('真题库'), findsOneWidget);
    expect(find.text('深圳市一年级数学期末真题（2025）'), findsOneWidget);
    expect(find.text('深圳市一年级语文期末真题（2024）'), findsOneWidget);
    expect(find.text('2025'), findsOneWidget);
    expect(find.text('2024'), findsOneWidget);
    expect(find.text('开始模考'), findsNWidgets(2));
    // L24：缺来源明确显示「来源待补录」，不空白也不伪造
    expect(find.text('来源：来源待补录'), findsNWidgets(2));

    await tester.tap(find.text('数学'));
    await tester.pumpAndSettle();
    expect(service.calls.last['subject'], 'math');
    expect(find.text('深圳市一年级数学期末真题（2025）'), findsOneWidget);
    expect(find.text('深圳市一年级语文期末真题（2024）'), findsNothing);

    await tester.tap(find.text('2025'));
    await tester.pumpAndSettle();
    expect(service.calls.last['year'], '2025');
    expect(find.text('深圳市一年级数学期末真题（2025）'), findsOneWidget);
  });

  testWidgets('真题库筛选后空态提示', (tester) async {
    final service = _FakeExamService();
    await tester.pumpWidget(_app(service));
    await tester.pumpAndSettle();
    await tester.tap(find.text('英语'));
    await tester.pumpAndSettle();
    expect(find.text('没有符合条件的真题'), findsOneWidget);
    expect(find.text('清除筛选'), findsOneWidget);
  });
}
