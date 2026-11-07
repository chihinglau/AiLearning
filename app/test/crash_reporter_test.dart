import 'dart:convert';

import 'package:ai_learning/core/monitoring/crash_reporter.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/pal/storage_pal.dart';
import 'package:flutter_test/flutter_test.dart';

class _MemoryStorage implements StoragePal {
  final Map<String, String> values = {};

  @override
  Future<void> init() async {}

  @override
  Future<String?> read(String key) async => values[key];

  @override
  Future<void> write(String key, String value) async => values[key] = value;

  @override
  Future<void> delete(String key) async => values.remove(key);
}

List<Map<String, dynamic>> _queueOf(_MemoryStorage storage) {
  final raw = storage.values[CrashReporter.queueKey];
  if (raw == null) return [];
  return List<Map<String, dynamic>>.from(
    (jsonDecode(raw) as List).map((item) => Map<String, dynamic>.from(item)),
  );
}

void main() {
  test('payload 掩码隐私并截断超长栈', () {
    final payload = CrashReporter.buildPayload(
      message: '家长 13800001111 邮箱 parent@example.com\u0000',
      stack: 'Exception: boom\n${'x' * 5000}',
      errorType: 'StateError',
      route: '/exam/1',
      occurredAt: DateTime.utc(2026, 11, 7, 2),
      platform: 'android',
      appVersion: '1.0.0',
    );
    final message = payload['message'] as String;
    expect(message, contains('1**********'));
    expect(message, contains('***@***'));
    expect(message, isNot(contains('13800001111')));
    expect(message, isNot(contains('\u0000')));
    expect((payload['stack'] as String).length, CrashReporter.maxStackChars);
    expect(payload['occurred_at'], '2026-11-07T02:00:00.000Z');
    expect(payload['platform'], 'android');
    expect(payload['app_version'], '1.0.0');
  });

  test('本地队列最多保留 10 条', () async {
    final storage = _MemoryStorage();
    final reporter = CrashReporter(storage: storage, sender: (_) async {});
    for (var index = 0; index < 12; index++) {
      await reporter.enqueue(
        message: 'boom-$index',
        occurredAt: DateTime.utc(2026, 11, 7, 2, index),
      );
    }
    final queue = _queueOf(storage);
    expect(queue.length, CrashReporter.maxQueued);
    expect(queue.first['message'], 'boom-2');
    expect(queue.last['message'], 'boom-11');
  });

  test('flush 成功上报后清空队列', () async {
    final storage = _MemoryStorage();
    final sent = <Map<String, dynamic>>[];
    final reporter = CrashReporter(
      storage: storage,
      sender: (payload) async => sent.add(payload),
    );
    await reporter.enqueue(message: 'first', occurredAt: DateTime.utc(2026));
    await reporter.enqueue(message: 'second', occurredAt: DateTime.utc(2026));

    expect(await reporter.flush(), 2);
    expect(sent.length, 2);
    expect(storage.values.containsKey(CrashReporter.queueKey), isFalse);
  });

  test('服务端 5xx 时保留队列等待下次重放', () async {
    final storage = _MemoryStorage();
    var attempts = 0;
    final reporter = CrashReporter(
      storage: storage,
      sender: (_) async {
        attempts++;
        throw const ApiException('服务暂不可用', statusCode: 503);
      },
    );
    await reporter.enqueue(message: 'keep-me', occurredAt: DateTime.utc(2026));

    expect(await reporter.flush(), 0);
    expect(attempts, 1);
    expect(_queueOf(storage).single['message'], 'keep-me');
  });

  test('参数非法（422）时丢弃该条并继续上报其余记录', () async {
    final storage = _MemoryStorage();
    final accepted = <String>[];
    final reporter = CrashReporter(
      storage: storage,
      sender: (payload) async {
        if (payload['message'] == 'invalid') {
          throw const ApiException('参数非法', statusCode: 422);
        }
        accepted.add(payload['message'] as String);
      },
    );
    await reporter.enqueue(message: 'invalid', occurredAt: DateTime.utc(2026));
    await reporter.enqueue(message: 'valid', occurredAt: DateTime.utc(2026));

    expect(await reporter.flush(), 1);
    expect(accepted, ['valid']);
    expect(_queueOf(storage), isEmpty);
  });
}
