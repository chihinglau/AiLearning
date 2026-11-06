import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/learn_service.dart';
import 'package:ai_learning/features/learn/knowledge_graph_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const _unitOne = UnitSummary(
  id: 11,
  textbookId: 1,
  grade: 1,
  name: '第一单元 数一数',
  orderIndex: 1,
);
const _unitTwo = UnitSummary(
  id: 12,
  textbookId: 1,
  grade: 1,
  name: '第二单元 10以内加减法',
  orderIndex: 2,
);

const _nodeOne = KnowledgeNode(
  id: 101,
  subject: 'math',
  name: '数一数',
  masteryScore: 20,
  masteryBand: 'weak',
  state: '未学习',
);
const _nodeTwo = KnowledgeNode(
  id: 102,
  subject: 'math',
  name: '10以内加法',
  masteryScore: 90,
  masteryBand: 'mastered',
  state: '已掌握',
  prerequisites: [101],
);

class _FakeLearnService extends LearnService {
  _FakeLearnService() : super(ApiClient());

  @override
  Future<List<UnitSummary>> units(int textbookId) async =>
      const [_unitOne, _unitTwo];

  @override
  Future<UnitDetail> unitDetail(int chapterId) async {
    if (chapterId == _unitOne.id) {
      return const UnitDetail(unit: _unitOne, knowledgePoints: [_nodeOne]);
    }
    return const UnitDetail(unit: _unitTwo, knowledgePoints: [_nodeTwo]);
  }
}

Widget _app(_FakeLearnService fake) {
  return ProviderScope(
    overrides: [learnServiceProvider.overrideWithValue(fake)],
    child: const MaterialApp(
      home: KnowledgeGraphPage(textbookId: 1, textbookName: '数学一年级上册'),
    ),
  );
}

void main() {
  testWidgets('知识图谱展示前置依赖节点与薄弱高亮', (tester) async {
    final fake = _FakeLearnService();
    await tester.pumpWidget(_app(fake));
    await tester.pumpAndSettle();

    expect(find.text('知识图谱 · 数学一年级上册'), findsOneWidget);
    expect(find.text('数一数'), findsOneWidget);
    expect(find.text('10以内加法'), findsOneWidget);
    expect(find.text('薄弱'), findsWidgets);
    expect(find.text('已精通'), findsOneWidget);
    expect(find.textContaining('箭头从「前置知识」指向'), findsOneWidget);
    expect(find.byKey(const ValueKey('graph-node-101')), findsOneWidget);
    expect(find.byKey(const ValueKey('graph-node-102')), findsOneWidget);
  });

  testWidgets('按单元筛选仅展示该单元知识点', (tester) async {
    final fake = _FakeLearnService();
    await tester.pumpWidget(_app(fake));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('graph-unit-11')));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('graph-node-101')), findsOneWidget);
    expect(find.byKey(const ValueKey('graph-node-102')), findsNothing);
  });
}
