import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/exam_service.dart';
import 'package:ai_learning/features/exam/exam_list_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

class _FakeExamService extends ExamService {
  _FakeExamService() : super(ApiClient());

  @override
  Future<List<ExamSummary>> list({String? type, String? status}) async {
    return const [
      ExamSummary(
        id: 1,
        title: '第一单元测试',
        subject: 'math',
        grade: 3,
        examType: 'unit',
        totalScore: 100,
        timeLimitMin: 45,
        questionCount: 20,
        category: 'available',
        windowState: 'open',
      ),
      ExamSummary(
        id: 2,
        title: '三年级数学期中',
        subject: 'math',
        grade: 3,
        examType: 'midterm',
        totalScore: 100,
        timeLimitMin: 90,
        questionCount: 28,
        category: 'available',
        windowState: 'scheduled',
        windowEnd: null,
      ),
      ExamSummary(
        id: 3,
        title: '三年级英语期末',
        subject: 'english',
        grade: 3,
        examType: 'final',
        totalScore: 100,
        timeLimitMin: 90,
        questionCount: 36,
        category: 'available',
        windowState: 'closed',
      ),
    ];
  }
}

Widget _app() {
  return ProviderScope(
    overrides: [examServiceProvider.overrideWithValue(_FakeExamService())],
    child: MaterialApp.router(
      routerConfig: GoRouter(
        initialLocation: '/exams',
        routes: [
          GoRoute(
            path: '/exams',
            builder: (context, state) => const ExamListPage(),
          ),
        ],
      ),
    ),
  );
}

void main() {
  testWidgets('按考试类型筛选并展示窗口状态', (tester) async {
    tester.view.physicalSize = const Size(1000, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    expect(find.text('单元测'), findsOneWidget);
    expect(find.text('期中'), findsOneWidget);
    expect(find.text('期末'), findsOneWidget);
    expect(find.text('模考'), findsOneWidget);

    expect(find.text('第一单元测试'), findsOneWidget);
    expect(find.text('三年级数学期中'), findsOneWidget);
    expect(find.text('三年级英语期末'), findsOneWidget);
    expect(find.text('未到开放时间'), findsOneWidget);
    expect(find.text('已结束'), findsOneWidget);

    await tester.tap(find.text('期中'));
    await tester.pumpAndSettle();

    expect(find.text('三年级数学期中'), findsOneWidget);
    expect(find.text('第一单元测试'), findsNothing);
    expect(find.text('三年级英语期末'), findsNothing);
  });

  testWidgets('窗口未开放时不进入考试并提示', (tester) async {
    tester.view.physicalSize = const Size(1000, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_app());
    await tester.pumpAndSettle();

    await tester.tap(find.text('三年级数学期中'));
    await tester.pump();

    expect(find.text('未到开放时间，暂不可进入考试'), findsOneWidget);
  });
}
