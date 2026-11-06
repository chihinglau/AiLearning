import 'package:ai_learning/core/models/ai.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/ai_service.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/learn_service.dart';
import 'package:ai_learning/features/mistakes/mistakes_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

final _wrongItem = WrongQuestionItem(
  id: 1,
  questionId: 11,
  wrongCount: 3,
  correctStreak: 0,
  status: 'active',
  intervalDays: 1,
  lastWrongAt: DateTime(2026, 11, 6),
  nextReviewAt: DateTime(2026, 11, 7),
  wrongReason: null,
  subject: 'math',
  qType: 'choice',
  stem: '3 + 4 = ?',
  chapterId: 2,
);

class _FakeLearnService extends LearnService {
  _FakeLearnService() : super(ApiClient());

  final List<String> tagged = [];

  @override
  Future<List<WrongQuestionItem>> wrongQuestions({
    String status = 'active',
    String? subject,
  }) async {
    return [_wrongItem];
  }

  @override
  Future<LearnStats> stats({int? studentId}) async {
    return const LearnStats(
      totalAnswered: 10,
      totalCorrect: 6,
      accuracy: 0.6,
      streakDays: 3,
      dueReviewCount: 2,
      activeWrongCount: 1,
    );
  }

  @override
  Future<WrongQuestionItem> tagReason(int wrongId, String reason) async {
    tagged.add(reason);
    return _wrongItem;
  }
}

class _FakeAIService extends AIService {
  _FakeAIService() : super(ApiClient());

  int calls = 0;

  @override
  Future<AIDiagnosis> diagnose(int wrongQuestionId, {int? studentId}) async {
    calls += 1;
    return AIDiagnosis(
      wrongId: wrongQuestionId,
      questionId: 11,
      provider: 'rule',
      reason: 'concept',
      reasonLabel: '概念',
      confidence: 'high',
      explanation: '本题累计做错 3 次，判断更接近「概念」类问题。',
      suggestions: const ['回看知识点定义与典型例题', '做 2 道同知识点基础题'],
      remainingQuota: 19,
    );
  }
}

Widget _app(_FakeLearnService learn, _FakeAIService ai) {
  return ProviderScope(
    overrides: [
      learnServiceProvider.overrideWithValue(learn),
      aiServiceProvider.overrideWithValue(ai),
    ],
    child: const MaterialApp(home: MistakesPage()),
  );
}

void main() {
  test('AIExplanation 解析步骤与提示', () {
    final model = AIExplanation.fromJson({
      'question_id': 11,
      'provider': 'llm',
      'focus': 'steps',
      'explanation': '先审题',
      'steps': ['读题', '定位'],
      'cautions': ['检查单位'],
      'remaining_quota': 9,
    });
    expect(model.provider, 'llm');
    expect(model.steps, hasLength(2));
    expect(model.cautions.single, '检查单位');
    expect(model.remainingQuota, 9);
  });

  test('AIDiagnosis 解析置信度标签', () {
    final model = AIDiagnosis.fromJson({
      'wrong_id': 1,
      'question_id': 11,
      'provider': 'rule',
      'reason': 'calculation',
      'reason_label': '计算',
      'confidence': 'medium',
      'explanation': '计算过程不严谨',
      'suggestions': ['分步计算'],
      'remaining_quota': 8,
    });
    expect(model.reasonLabel, '计算');
    expect(model.confidenceLabel, '中置信');
    expect(model.suggestions.single, '分步计算');
  });

  testWidgets('错题本 AI 归因弹出分析并可采纳错因', (tester) async {
    tester.view.physicalSize = const Size(900, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final learn = _FakeLearnService();
    final ai = _FakeAIService();
    await tester.pumpWidget(_app(learn, ai));
    await tester.pumpAndSettle();

    expect(find.text('3 + 4 = ?'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('ai-diagnose-1')));
    await tester.pumpAndSettle();

    expect(ai.calls, 1);
    expect(find.text('AI 错因分析'), findsOneWidget);
    expect(find.text('候选错因：概念'), findsOneWidget);
    expect(find.text('高置信'), findsOneWidget);
    expect(find.textContaining('回看知识点定义'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('apply-ai-reason')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(learn.tagged, ['concept']);
    expect(find.byType(SnackBar), findsOneWidget);
    expect(find.textContaining('错因已标注为「概念不清」'), findsOneWidget);
    await tester.pumpAndSettle();
  });
}
