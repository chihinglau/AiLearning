import 'package:ai_learning/core/offline/offline_learn_store.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/offline_learn_service.dart';
import 'package:flutter_test/flutter_test.dart';

class _MemoryStore implements OfflineLearnStore {
  final Map<String, dynamic> data = {};

  @override
  Future<void> saveBundle(int textbookId, Map<String, dynamic> bundle) async {
    data['bundle:$textbookId'] = bundle;
  }

  @override
  Future<Map<String, dynamic>?> bundle(int textbookId) async {
    return data['bundle:$textbookId'] as Map<String, dynamic>?;
  }

  @override
  Future<void> saveMeta(int textbookId, Map<String, dynamic> meta) async {
    data['meta:$textbookId'] = meta;
  }

  @override
  Future<Map<String, dynamic>?> meta(int textbookId) async {
    return data['meta:$textbookId'] as Map<String, dynamic>?;
  }

  @override
  Future<List<int>> downloadedTextbookIds() async => const [];

  @override
  Future<void> removeBundle(int textbookId) async {}

  @override
  Future<void> saveHome(Map<String, dynamic> home) async {
    data['home'] = home;
  }

  @override
  Future<Map<String, dynamic>?> home() async {
    return data['home'] as Map<String, dynamic>?;
  }

  @override
  Future<void> saveWrongQuestions(String status, List<dynamic> items) async {
    data['wrong:$status'] = items;
  }

  @override
  Future<List<dynamic>?> wrongQuestions(String status) async {
    return data['wrong:$status'] as List<dynamic>?;
  }

  @override
  Future<void> saveStats(Map<String, dynamic> stats) async {
    data['stats'] = stats;
  }

  @override
  Future<Map<String, dynamic>?> stats() async {
    return data['stats'] as Map<String, dynamic>?;
  }

  @override
  Future<void> enqueue(OfflineAttemptEntry entry) async {}

  @override
  Future<List<OfflineAttemptEntry>> pendingAttempts() async => const [];

  @override
  Future<void> removeAttempt(String clientKey) async {}
}

void main() {
  test('错题与统计写入缓存后可离线读回', () async {
    final store = _MemoryStore();
    final service = OfflineLearnService(ApiClient(), store);

    await service.cacheWrongQuestions('active', [
      {
        'id': 7,
        'question_id': 11,
        'wrong_count': 2,
        'correct_streak': 0,
        'status': 'active',
        'interval_days': 1,
        'last_wrong_at': '2026-11-08T10:00:00',
        'next_review_at': '2026-11-09T10:00:00',
        'subject': 'chinese',
        'q_type': 'choice',
        'stem': '下面属于声母的是（ ）。',
        'chapter_id': 3,
      },
    ]);
    await service.cacheStats({
      'total_answered': 12,
      'total_correct': 9,
      'accuracy': 0.75,
      'streak_days': 3,
      'due_review_count': 1,
      'active_wrong_count': 2,
      'weak_points': const [],
    });

    final items = await service.cachedWrongQuestions('active');
    final stats = await service.cachedStats();

    expect(items, hasLength(1));
    expect(items!.first.id, 7);
    expect(items.first.stem, '下面属于声母的是（ ）。');
    expect(stats!.totalAnswered, 12);
    expect(stats.dueReviewCount, 1);
    expect(stats.accuracyPercent, '75%');
  });

  test('未缓存时返回 null，页面可展示错误提示', () async {
    final service = OfflineLearnService(ApiClient(), _MemoryStore());

    expect(await service.cachedWrongQuestions('active'), isNull);
    expect(await service.cachedStats(), isNull);
  });
}
