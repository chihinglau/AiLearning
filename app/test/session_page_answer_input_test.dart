import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/learn_service.dart';
import 'package:ai_learning/features/session/session_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// 记录提交内容的假服务，用于断言文本框作答是否真的发出了 user_answer。
class _CapturingLearnService extends LearnService {
  _CapturingLearnService(this._questions)
      : super(ApiClient(baseUrl: 'http://127.0.0.1'));

  final List<Question> _questions;
  Map<String, dynamic>? lastAnswer;
  int submitCount = 0;

  @override
  Future<List<Question>> start({
    int? chapterId,
    int? knowledgePointId,
    String? subject,
    int count = 10,
  }) async {
    return _questions;
  }

  @override
  Future<LearnSubmitResult> submit({
    required int questionId,
    required Map<String, dynamic> userAnswer,
    int durationMs = 0,
    int? sessionId,
    String source = 'practice',
  }) async {
    submitCount += 1;
    lastAnswer = userAnswer;
    return const LearnSubmitResult(
      isCorrect: false,
      correctAnswer: {'value': 'a² + b² = c²'},
      analysis: '两直角边的平方和等于斜边的平方。',
    );
  }
}

const _fillQuestion = Question(
  id: 11,
  chapterId: 1,
  subject: 'math',
  qType: 'fill',
  stem: '直角三角形两直角边为 3 和 4，斜边的平方是（ ）。',
);

/// 线上题库真实存在的题型：q_type=answer，options 为空。
const _answerQuestion = Question(
  id: 12,
  chapterId: 1,
  subject: 'math',
  qType: 'answer',
  stem: '用 a、b 表示直角边，c 表示斜边，写出勾股定理的式子。',
);

Future<void> _pumpSession(
  WidgetTester tester,
  LearnService service,
) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [learnServiceProvider.overrideWithValue(service)],
      child: const MaterialApp(
        home: SessionPage(title: '练一练', chapterId: 1),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

FilledButton _submitButton(WidgetTester tester) {
  return tester.widget<FilledButton>(
    find.widgetWithText(FilledButton, '提交答案'),
  );
}

void main() {
  testWidgets('填空题渲染输入框，输入后可以提交', (tester) async {
    final service = _CapturingLearnService(const [_fillQuestion]);
    await _pumpSession(tester, service);

    expect(find.byKey(const ValueKey('answer-input-11')), findsOneWidget);
    expect(_submitButton(tester).onPressed, isNull);

    await tester.enterText(find.byType(TextField), '25');
    await tester.pump();
    expect(_submitButton(tester).onPressed, isNotNull);

    await tester.tap(find.widgetWithText(FilledButton, '提交答案'));
    await tester.pumpAndSettle();

    expect(service.submitCount, 1);
    expect(service.lastAnswer, {'value': '25'});
    expect(find.textContaining('正确答案'), findsOneWidget);
  });

  testWidgets('无选项的解答题也必须给出输入框，并可提交自查', (tester) async {
    final service = _CapturingLearnService(const [_answerQuestion]);
    await _pumpSession(tester, service);

    // 回归点：旧实现按单选分支渲染，options 为空 → 整块作答区空白，提交按钮永久置灰。
    expect(find.byKey(const ValueKey('answer-input-12')), findsOneWidget);
    expect(find.text('请写出解答过程与答案'), findsOneWidget);
    expect(_submitButton(tester).onPressed, isNull);

    await tester.enterText(find.byType(TextField), 'a² + b² = c²');
    await tester.pump();
    expect(_submitButton(tester).onPressed, isNotNull);

    await tester.tap(find.widgetWithText(FilledButton, '提交答案'));
    await tester.pumpAndSettle();

    expect(service.submitCount, 1);
    expect(service.lastAnswer, {'value': 'a² + b² = c²'});
    expect(find.textContaining('参考答案：'), findsOneWidget);
    expect(find.textContaining('表述不同也可能判对'), findsOneWidget);
  });
}
