import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/exam_service.dart';
import 'package:ai_learning/features/exam/exam_list_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

/// 模拟服务端筛选：断言筛选确实被下推为查询参数，而不是客户端本地过滤。
class _FakeExamService extends ExamService {
  _FakeExamService() : super(ApiClient());

  final List<Map<String, String?>> calls = [];

  static const _all = [
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

  @override
  Future<List<ExamSummary>> list({
    String? type,
    String? status,
    String? subject,
    String? windowState,
    String? query,
    int? page,
    int? pageSize,
  }) async {
    calls.add({
      'type': type,
      'status': status,
      'subject': subject,
      'window_state': windowState,
      'q': query,
    });
    return _all.where((exam) {
      if (type != null && exam.examType != type) return false;
      if (status != null && exam.category != status) return false;
      if (subject != null && exam.subject != subject) return false;
      if (windowState != null && exam.windowState != windowState) return false;
      if (query != null && !exam.title.contains(query)) return false;
      return true;
    }).toList();
  }
}

Widget _app(_FakeExamService service) {
  return ProviderScope(
    overrides: [examServiceProvider.overrideWithValue(service)],
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
  testWidgets('按考试类型筛选下推服务端并展示窗口状态', (tester) async {
    tester.view.physicalSize = const Size(1000, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final service = _FakeExamService();
    await tester.pumpWidget(_app(service));
    await tester.pumpAndSettle();

    expect(find.text('单元测'), findsOneWidget);
    expect(find.text('期中'), findsOneWidget);
    expect(find.text('期末'), findsOneWidget);
    expect(find.text('模考'), findsOneWidget);

    expect(find.text('第一单元测试'), findsOneWidget);
    expect(find.text('三年级数学期中'), findsOneWidget);
    expect(find.text('三年级英语期末'), findsOneWidget);
    // 窗口状态既出现在筛选 chip，也出现在卡片状态徽标
    expect(find.text('未开始'), findsWidgets);
    expect(find.text('已结束'), findsWidgets);

    await tester.tap(find.text('期中'));
    await tester.pumpAndSettle();

    expect(service.calls.last['type'], 'midterm');
    expect(find.text('三年级数学期中'), findsOneWidget);
    expect(find.text('第一单元测试'), findsNothing);
    expect(find.text('三年级英语期末'), findsNothing);
  });

  testWidgets('窗口未开放时不进入考试并提示', (tester) async {
    tester.view.physicalSize = const Size(1000, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_app(_FakeExamService()));
    await tester.pumpAndSettle();

    await tester.tap(find.text('三年级数学期中'));
    await tester.pump();

    expect(find.textContaining('开放时间'), findsWidgets);
  });

  testWidgets('筛选后为空提供清除筛选入口', (tester) async {
    tester.view.physicalSize = const Size(1000, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_app(_FakeExamService()));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), '不存在的试卷');
    await tester.testTextInput.receiveAction(TextInputAction.search);
    await tester.pumpAndSettle();

    expect(find.text('没有符合条件的考试'), findsOneWidget);
    expect(find.text('清除筛选'), findsOneWidget);
  });
}
