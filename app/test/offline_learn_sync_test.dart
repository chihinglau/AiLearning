import 'package:ai_learning/core/offline/offline_learn_store.dart';
import 'package:ai_learning/core/offline/offline_learn_sync.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter_test/flutter_test.dart';

class _MemoryStore implements OfflineLearnStore {
  _MemoryStore(this.entries);

  final List<OfflineAttemptEntry> entries;

  @override
  Future<void> enqueue(OfflineAttemptEntry entry) async => entries.add(entry);

  @override
  Future<List<OfflineAttemptEntry>> pendingAttempts() async => [...entries];

  @override
  Future<void> removeAttempt(String clientKey) async {
    entries.removeWhere((entry) => entry.clientKey == clientKey);
  }

  @override
  Future<void> saveBundle(int textbookId, Map<String, dynamic> bundle) async {}

  @override
  Future<Map<String, dynamic>?> bundle(int textbookId) async => null;

  @override
  Future<void> saveMeta(int textbookId, Map<String, dynamic> meta) async {}

  @override
  Future<Map<String, dynamic>?> meta(int textbookId) async => null;

  @override
  Future<List<int>> downloadedTextbookIds() async => const [];

  @override
  Future<void> removeBundle(int textbookId) async {}

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
}

class _FakeApi extends ApiClient {
  _FakeApi({this.error});

  final ApiException? error;
  List<Map<String, dynamic>> postedItems = [];
  int calls = 0;

  @override
  Future<Map<String, dynamic>> postJson(
    String path,
    Map<String, dynamic> body,
  ) async {
    calls++;
    final failure = error;
    if (failure != null) throw failure;
    final items = body['items'] as List<dynamic>;
    postedItems = items.cast<Map<String, dynamic>>();
    return {
      'results': [
        for (final item in items)
          {'client_key': item['client_key'], 'skipped': false},
      ],
    };
  }
}

OfflineAttemptEntry _entry(String key, int questionId) {
  return OfflineAttemptEntry(
    clientKey: key,
    questionId: questionId,
    userAnswer: {'value': 'A'},
    answeredAt: DateTime(2026, 11, 8, 10, questionId),
  );
}

void main() {
  test('同步成功后清空本地队列', () async {
    final store = _MemoryStore([_entry('a', 1), _entry('b', 2)]);
    final api = _FakeApi();
    final sync = OfflineLearnSync(api, store);

    final synced = await sync.sync();

    expect(synced, 2);
    expect(store.entries, isEmpty);
    expect(api.postedItems, hasLength(2));
    expect(api.postedItems.first['client_key'], 'a');
  });

  test('断网时保留队列，联网后可再次同步', () async {
    final store = _MemoryStore([_entry('a', 1)]);
    final api = _FakeApi(error: const ApiException('无法连接服务器'));
    final sync = OfflineLearnSync(api, store);

    expect(await sync.sync(), 0);
    expect(store.entries, hasLength(1));

    final retry = OfflineLearnSync(_FakeApi(), store);
    expect(await retry.sync(), 1);
    expect(store.entries, isEmpty);
  });
}
