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

class _FakeExamService extends ExamService {
  _FakeExamService() : super(ApiClient());

  final List<String?> requested = [];

  @override
  Future<List<ExamSummary>> pastPapers({
    String? subject,
    int? year,
    String? region,
  }) async {
    requested.add(subject);
    final items = [
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
    return subject == null
        ? items
        : items.where((item) => item.subject == subject).toList();
  }
}

Widget _app(_FakeExamService service) {
  return ProviderScope(
    overrides: [examServiceProvider.overrideWithValue(service)],
    child: const MaterialApp(home: PastPaperPage()),
  );
}

void main() {
  testWidgets('真题库按学科与年份筛选', (tester) async {
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

    await tester.tap(find.text('数学'));
    await tester.pumpAndSettle();
    expect(service.requested.last, 'math');
    expect(find.text('深圳市一年级数学期末真题（2025）'), findsOneWidget);
    expect(find.text('深圳市一年级语文期末真题（2024）'), findsNothing);

    await tester.tap(find.text('2025'));
    await tester.pumpAndSettle();
    expect(find.text('深圳市一年级数学期末真题（2025）'), findsOneWidget);
  });

  testWidgets('真题库空态提示', (tester) async {
    final service = _FakeExamService();
    await tester.pumpWidget(_app(service));
    await tester.pumpAndSettle();
    await tester.tap(find.text('英语'));
    await tester.pumpAndSettle();
    expect(find.text('暂无匹配的真题'), findsOneWidget);
  });
}
