import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/learn_service.dart';
import 'package:ai_learning/features/session/session_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeLearnService extends LearnService {
  _FakeLearnService() : super(ApiClient(baseUrl: 'http://127.0.0.1'));

  @override
  Future<List<Question>> start({
    int? chapterId,
    int? knowledgePointId,
    String? subject,
    int count = 10,
  }) async {
    return const [
      Question(
        id: 1,
        chapterId: 1,
        subject: 'math',
        qType: 'choice',
        stem: '1 + 1 = ?',
        options: [
          QuestionOption(key: 'A', text: '1'),
          QuestionOption(key: 'B', text: '2'),
        ],
      ),
    ];
  }

  @override
  Future<LearnSubmitResult> submit({
    required int questionId,
    required Map<String, dynamic> userAnswer,
    int durationMs = 0,
    int? sessionId,
    String source = 'practice',
  }) async {
    return const LearnSubmitResult(
      isCorrect: false,
      correctAnswer: {'value': 'B'},
    );
  }
}

void main() {
  testWidgets('提交后仍保留已选答案高亮', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          learnServiceProvider.overrideWithValue(_FakeLearnService()),
        ],
        child: const MaterialApp(
          home: SessionPage(title: '练一练', chapterId: 1),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('1'));
    await tester.pump();
    final before = tester.widget<ListTile>(
      find.ancestor(of: find.text('1'), matching: find.byType(ListTile)),
    );
    expect(before.selected, isTrue);

    await tester.tap(find.text('提交答案'));
    await tester.pumpAndSettle();

    final after = tester.widget<ListTile>(
      find.ancestor(of: find.text('1'), matching: find.byType(ListTile)),
    );
    expect(after.selected, isTrue);
    expect(find.byIcon(Icons.check_circle), findsOneWidget);
    expect(find.text('回答错误'), findsOneWidget);
  });
}
