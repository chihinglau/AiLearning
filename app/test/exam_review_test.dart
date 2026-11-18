import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/exam_service.dart';
import 'package:ai_learning/features/exam/exam_review_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeExamService extends ExamService {
  _FakeExamService() : super(ApiClient());

  final List<String> decisions = [];
  final List<ExamReviewItem> items = const [
    ExamReviewItem(
      id: 7,
      title: '待复核真题卷',
      subject: 'math',
      grade: 1,
      status: 'pending_review',
      isPastPaper: true,
      year: 2020,
      region: '深圳',
      sourceName: '深圳市教育考试院公开真题',
      licenseNote: 'R-07 台账已登记',
    ),
  ];

  @override
  Future<List<ExamReviewItem>> listReviews({
    String status = 'pending_review',
  }) async =>
      items.where((item) => item.status == status).toList();

  @override
  Future<String> reviewExam(
    int examId,
    String decision, {
    String? note,
  }) async {
    decisions.add('$examId:$decision');
    return 'published';
  }
}

Widget _app(_FakeExamService service) {
  return ProviderScope(
    overrides: [examServiceProvider.overrideWithValue(service)],
    child: const MaterialApp(home: ExamReviewPage()),
  );
}

void main() {
  test('EX-10 模型：状态文案与来源标签不伪造', () {
    const item = ExamReviewItem(
      id: 1,
      title: '缺来源卷',
      subject: 'math',
      grade: 1,
      status: 'pending_review',
      isPastPaper: true,
    );
    expect(item.statusLabel, '待复核');
    expect(item.sourceLabel, '来源待补录');

    const published = ExamReviewItem(
      id: 2,
      title: '已发布卷',
      subject: 'math',
      grade: 1,
      status: 'published',
      isPastPaper: true,
      sourceName: '已核验来源',
    );
    expect(published.statusLabel, '已发布');
    expect(published.sourceLabel, '已核验来源');
  });

  test('EX-10 模型：JSON 解析与组卷结果草稿态', () {
    final item = ExamReviewItem.fromJson({
      'id': 9,
      'title': '草稿卷',
      'subject': 'chinese',
      'grade': 3,
      'status': 'draft',
      'is_past_paper': true,
      'source_name': NoneSource.name,
    });
    expect(item.statusLabel, '草稿');
    expect(item.sourceLabel, NoneSource.name);

    final draft = ExamGenerateResult.fromJson({
      'exam_id': 5,
      'title': '真题',
      'seed': 1,
      'question_count': 10,
      'total_score': 100,
      'kp_coverage': 0.9,
      'status': 'draft',
    });
    expect(draft.isDraft, isTrue);

    final normal = ExamGenerateResult.fromJson({
      'exam_id': 6,
      'title': '普通卷',
      'seed': 1,
      'question_count': 10,
      'total_score': 100,
      'kp_coverage': 0.9,
    });
    expect(normal.isDraft, isFalse);
    expect(normal.status, 'published');
  });

  testWidgets('EX-10 审核队列展示来源并通过发布', (tester) async {
    tester.view.physicalSize = const Size(900, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final service = _FakeExamService();
    await tester.pumpWidget(_app(service));
    await tester.pumpAndSettle();

    expect(find.text('待复核真题卷'), findsOneWidget);
    expect(find.textContaining('来源：深圳市教育考试院公开真题'), findsOneWidget);
    expect(find.text('通过并发布'), findsOneWidget);
    expect(find.text('退回草稿'), findsOneWidget);

    await tester.tap(find.text('通过并发布'));
    await tester.pumpAndSettle();
    expect(service.decisions, ['7:approve']);
  });

  testWidgets('EX-10 退回必须先填复核意见', (tester) async {
    tester.view.physicalSize = const Size(900, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final service = _FakeExamService();
    await tester.pumpWidget(_app(service));
    await tester.pumpAndSettle();

    await tester.tap(find.text('退回草稿'));
    await tester.pumpAndSettle();
    expect(find.text('退回草稿并说明原因'), findsOneWidget);

    // 空意见点确认：应提示必填且不下发决策
    await tester.tap(find.text('确认退回'));
    await tester.pumpAndSettle();
    expect(find.text('退回必须填写复核意见'), findsOneWidget);
    expect(service.decisions, isEmpty);

    await tester.enterText(find.byType(TextField), '来源凭证未登记 R-07 台账');
    await tester.tap(find.text('确认退回'));
    await tester.pumpAndSettle();
    expect(service.decisions, ['7:reject']);
  });

  testWidgets('EX-10 切换到无卷状态显示空态', (tester) async {
    final service = _FakeExamService();
    await tester.pumpWidget(_app(service));
    await tester.pumpAndSettle();

    await tester.tap(find.text('已下线'));
    await tester.pumpAndSettle();
    expect(find.text('当前状态暂无试卷'), findsOneWidget);
  });
}

class NoneSource {
  static const name = '已登记来源';
}
