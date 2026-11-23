import 'package:ai_learning/core/offline/offline_learn_store.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/offline_learn_service.dart';
import 'package:flutter_test/flutter_test.dart';

class _MemoryStore implements OfflineLearnStore {
  final Map<int, Map<String, dynamic>> bundles = {};
  final List<OfflineAttemptEntry> queue = [];
  final List<int> downloaded = [];

  @override
  Future<void> saveBundle(int textbookId, Map<String, dynamic> bundle) async {
    bundles[textbookId] = bundle;
  }

  @override
  Future<Map<String, dynamic>?> bundle(int textbookId) async =>
      bundles[textbookId];

  @override
  Future<List<int>> downloadedTextbookIds() async => downloaded;

  @override
  Future<void> saveMeta(int textbookId, Map<String, dynamic> meta) async {}

  @override
  Future<Map<String, dynamic>?> meta(int textbookId) async => null;

  @override
  Future<void> removeBundle(int textbookId) async {
    bundles.remove(textbookId);
  }

  @override
  Future<void> saveHome(Map<String, dynamic> home) async {}

  @override
  Future<Map<String, dynamic>?> home() async => null;

  @override
  Future<void> saveWrongQuestions(String status, List<dynamic> items) async {}

  @override
  Future<List<dynamic>?> wrongQuestions(String status) async => null;

  @override
  Future<void> saveStats(Map<String, dynamic> stats) async {}

  @override
  Future<Map<String, dynamic>?> stats() async => null;

  @override
  Future<void> enqueue(OfflineAttemptEntry entry) async {
    queue.add(entry);
  }

  @override
  Future<List<OfflineAttemptEntry>> pendingAttempts() async => List.of(queue);

  @override
  Future<void> removeAttempt(String clientKey) async {
    queue.removeWhere((entry) => entry.clientKey == clientKey);
  }
}

Map<String, dynamic> _question(int id, {required String answer}) {
  return {
    'id': id,
    'chapter_id': 1,
    'subject': 'math',
    'q_type': 'choice',
    'content': {'stem': '题目 $id'},
    'options': [
      {'key': 'A', 'text': '选项 A'},
      {'key': 'B', 'text': '选项 B'},
    ],
    'answer': {'value': answer},
    'difficulty': 2,
    'knowledge_point_id': 9,
  };
}

OfflineAttemptEntry _attempt(
  int questionId, {
  required String answer,
  required DateTime at,
}) {
  return OfflineAttemptEntry(
    clientKey: '$questionId-${at.millisecondsSinceEpoch}',
    questionId: questionId,
    userAnswer: {'value': answer},
    answeredAt: at,
  );
}

void main() {
  late _MemoryStore store;
  late OfflineLearnService service;

  setUp(() {
    store = _MemoryStore()
      ..downloaded.add(1)
      ..bundles[1] = {
        'questions': [
          _question(101, answer: 'B'),
          _question(102, answer: 'A'),
          _question(103, answer: 'A'),
        ],
      };
    service = OfflineLearnService(ApiClient(), store);
  });

  test('只聚合同一题答错的最新记录并累计次数', () async {
    final early = DateTime(2026, 11, 22, 8);
    final late = DateTime(2026, 11, 22, 9);
    store.queue.addAll([
      _attempt(101, answer: 'A', at: early),
      _attempt(101, answer: 'A', at: late),
      _attempt(102, answer: 'A', at: late), // 答对，不应进入错题
    ]);

    final items = await service.pendingWrongQuestions();

    expect(items, hasLength(1));
    final item = items.single;
    expect(item.questionId, 101);
    expect(item.id, -101, reason: '本地待同步条目用负 ID 与服务端错题区分');
    expect(item.wrongCount, 2);
    expect(item.lastWrongAt, late);
    expect(item.subject, 'math');
    expect(item.stem, '题目 101');
    expect(item.status, 'active');
  });

  test('缺少本地题目或缺少答案时跳过而不是误判', () async {
    store.queue.addAll([
      _attempt(999, answer: 'A', at: DateTime(2026, 11, 22, 8)),
      _attempt(103, answer: 'B', at: DateTime(2026, 11, 22, 9)),
    ]);
    store.bundles[1] = {
      'questions': [
        _question(103, answer: 'A'),
        {
          'id': 104,
          'chapter_id': 1,
          'subject': 'math',
          'q_type': 'choice',
          'content': {'stem': '无答案题'},
          'answer': null,
        },
      ],
    };
    store.queue.add(_attempt(104, answer: 'A', at: DateTime(2026, 11, 22, 10)));

    final items = await service.pendingWrongQuestions();

    expect(items, hasLength(1));
    expect(items.single.questionId, 103);
  });

  test('没有待同步记录时返回空列表', () async {
    expect(await service.pendingWrongQuestions(), isEmpty);
  });
}
