import 'dart:math' as math;

import 'package:ai_learning/core/offline/offline_learn_store.dart';
import 'package:ai_learning/core/services/api_client.dart';

/// 离线答题队列批量同步：按 client_key 幂等入库，成功后删除本地记录。
class OfflineLearnSync {
  OfflineLearnSync(this._api, this._store);

  static const int batchSize = 200;

  final ApiClient _api;
  final OfflineLearnStore _store;

  Future<int> sync() async {
    final pending = await _store.pendingAttempts();
    if (pending.isEmpty) return 0;
    var synced = 0;
    for (var start = 0; start < pending.length; start += batchSize) {
      final batch = pending.sublist(
        start,
        math.min(start + batchSize, pending.length),
      );
      try {
        final data = await _api.postJson(
          '/api/learn/offline/attempts',
          {'items': batch.map((entry) => entry.toJson()).toList()},
        );
        final results = data['results'] as List<dynamic>? ?? const [];
        for (final item in results) {
          if (item is! Map) continue;
          final key = item['client_key'];
          if (key is String && key.isNotEmpty) {
            await _store.removeAttempt(key);
            synced++;
          }
        }
      } on ApiException {
        // 仍然离线或服务端暂不可用：保留队列，下次触发再同步。
        break;
      }
    }
    return synced;
  }
}
