import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/exam_service.dart';
import 'package:ai_learning/features/exam/exam_report_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

class _FakeExamService extends ExamService {
  _FakeExamService() : super(ApiClient());

  bool assessed = false;
  final List<Map<int, double>> calls = [];

  @override
  Future<ExamReport> report(int attemptId) async {
    return ExamReport(
      attemptId: attemptId,
      examId: 4,
      examTitle: '三年级数学期中',
      examType: 'midterm',
      status: assessed ? 'completed' : 'grading',
      totalScore: assessed ? 90 : 50,
      fullScore: 100,
      objectiveScore: 50,
      subjectiveScore: assessed ? 40 : null,
      questionCount: 2,
      answeredCount: 2,
      pendingSubjective: assessed
          ? const []
          : const [
              ExamSubjectiveQuestion(
                questionId: 101,
                qType: 'answer',
                stem: '计算 3/4 + 1/4 并写出过程',
                fullScore: 50,
                userAnswer: {'value': '4/4'},
                referenceAnswer: {'value': '1'},
                scoringPoints: ['列式正确（25 分）', '结果正确（25 分）'],
                analysis: '同分母分数相加，分子相加。',
                selfScore: 40,
              ),
            ],
    );
  }

  @override
  Future<void> selfAssess(int attemptId, Map<int, double> scores) async {
    calls.add(scores);
    assessed = true;
  }
}

Widget _app(_FakeExamService service) {
  return ProviderScope(
    overrides: [examServiceProvider.overrideWithValue(service)],
    child: MaterialApp.router(
      routerConfig: GoRouter(
        initialLocation: '/report',
        routes: [
          GoRoute(
            path: '/report',
            builder: (context, state) => const ExamReportPage(attemptId: 1),
          ),
          GoRoute(
            path: '/exams',
            builder: (context, state) => const SizedBox.shrink(),
          ),
          GoRoute(
            path: '/shell',
            builder: (context, state) => const SizedBox.shrink(),
          ),
        ],
      ),
    ),
  );
}

void main() {
  testWidgets('展示主观题自评卡并提交自评分后刷新报告', (tester) async {
    tester.view.physicalSize = const Size(1000, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final service = _FakeExamService();
    await tester.pumpWidget(_app(service));
    await tester.pumpAndSettle();

    expect(find.text('主观题自评（1）'), findsOneWidget);
    expect(find.text('计算 3/4 + 1/4 并写出过程'), findsOneWidget);
    expect(find.text('你的答案：4/4'), findsOneWidget);
    expect(find.text('参考答案：1'), findsOneWidget);
    expect(find.text('· 列式正确（25 分）'), findsOneWidget);
    expect(find.text('40 / 50'), findsOneWidget);

    await tester.tap(find.text('提交自评'));
    await tester.pumpAndSettle();

    expect(service.calls, hasLength(1));
    expect(service.calls.first[101], 40.0);
    expect(find.text('自评已提交，成绩与学情已更新'), findsOneWidget);
    expect(find.text('主观题自评（1）'), findsNothing);
    expect(find.textContaining('主观题待批改'), findsNothing);
  });
}
