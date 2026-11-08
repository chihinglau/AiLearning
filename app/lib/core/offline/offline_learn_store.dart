import 'dart:convert';

import 'package:hive_flutter/hive_flutter.dart';

/// 离线答题记录：联网后批量幂等同步。
class OfflineAttemptEntry {
  const OfflineAttemptEntry({
    required this.clientKey,
    required this.questionId,
    required this.userAnswer,
    required this.answeredAt,
    this.durationMs = 0,
    this.source = 'practice',
  });

  final String clientKey;
  final int questionId;
  final Map<String, dynamic> userAnswer;
  final DateTime answeredAt;
  final int durationMs;
  final String source;

  Map<String, dynamic> toJson() => {
        'client_key': clientKey,
        'question_id': questionId,
        'user_answer': userAnswer,
        'answered_at': answeredAt.toIso8601String(),
        'duration_ms': durationMs,
        'source': source,
      };

  factory OfflineAttemptEntry.fromJson(Map<String, dynamic> json) {
    return OfflineAttemptEntry(
      clientKey: json['client_key'] as String? ?? '',
      questionId: json['question_id'] as int? ?? 0,
      userAnswer: Map<String, dynamic>.from(
        json['user_answer'] as Map? ?? const <String, dynamic>{},
      ),
      answeredAt:
          DateTime.tryParse(json['answered_at'] as String? ?? '') ??
              DateTime.now(),
      durationMs: json['duration_ms'] as int? ?? 0,
      source: json['source'] as String? ?? 'practice',
    );
  }
}

abstract class OfflineLearnStore {
  Future<void> saveBundle(int textbookId, Map<String, dynamic> bundle);
  Future<Map<String, dynamic>?> bundle(int textbookId);
  Future<void> saveMeta(int textbookId, Map<String, dynamic> meta);
  Future<Map<String, dynamic>?> meta(int textbookId);
  Future<List<int>> downloadedTextbookIds();
  Future<void> removeBundle(int textbookId);
  Future<void> saveHome(Map<String, dynamic> home);
  Future<Map<String, dynamic>?> home();
  Future<void> saveWrongQuestions(String status, List<dynamic> items);
  Future<List<dynamic>?> wrongQuestions(String status);
  Future<void> saveStats(Map<String, dynamic> stats);
  Future<Map<String, dynamic>?> stats();
  Future<void> enqueue(OfflineAttemptEntry entry);
  Future<List<OfflineAttemptEntry>> pendingAttempts();
  Future<void> removeAttempt(String clientKey);
}

/// Hive 实现：所有内容以 JSON 字符串保存，避免模型升级导致读取失败。
class HiveOfflineLearnStore implements OfflineLearnStore {
  static const _boxName = 'offline_learn';
  static const _bundlePrefix = 'bundle:';
  static const _metaPrefix = 'meta:';
  static const _queuePrefix = 'queue:';
  static const _homeKey = 'home';
  static const _wrongPrefix = 'wrong:';
  static const _statsKey = 'stats';

  Box<String>? _box;

  Future<Box<String>> _open() async {
    final existing = _box;
    if (existing != null) return existing;
    await Hive.initFlutter();
    final box = await Hive.openBox<String>(_boxName);
    _box = box;
    return box;
  }

  @override
  Future<void> saveBundle(int textbookId, Map<String, dynamic> bundle) async {
    final box = await _open();
    await box.put('$_bundlePrefix$textbookId', jsonEncode(bundle));
  }

  @override
  Future<Map<String, dynamic>?> bundle(int textbookId) async {
    final box = await _open();
    final raw = box.get('$_bundlePrefix$textbookId');
    if (raw == null) return null;
    final data = jsonDecode(raw);
    return data is Map<String, dynamic> ? data : null;
  }

  @override
  Future<void> saveMeta(int textbookId, Map<String, dynamic> meta) async {
    final box = await _open();
    await box.put('$_metaPrefix$textbookId', jsonEncode(meta));
  }

  @override
  Future<Map<String, dynamic>?> meta(int textbookId) async {
    final box = await _open();
    final raw = box.get('$_metaPrefix$textbookId');
    if (raw == null) return null;
    final data = jsonDecode(raw);
    return data is Map<String, dynamic> ? data : null;
  }

  @override
  Future<List<int>> downloadedTextbookIds() async {
    final box = await _open();
    final ids = <int>[];
    for (final key in box.keys) {
      if (key is! String || !key.startsWith(_metaPrefix)) continue;
      final id = int.tryParse(key.substring(_metaPrefix.length));
      if (id != null) ids.add(id);
    }
    ids.sort();
    return ids;
  }

  @override
  Future<void> removeBundle(int textbookId) async {
    final box = await _open();
    await box.delete('$_bundlePrefix$textbookId');
    await box.delete('$_metaPrefix$textbookId');
  }

  @override
  Future<void> saveHome(Map<String, dynamic> home) async {
    final box = await _open();
    await box.put(_homeKey, jsonEncode(home));
  }

  @override
  Future<Map<String, dynamic>?> home() async {
    final box = await _open();
    final raw = box.get(_homeKey);
    if (raw == null) return null;
    final data = jsonDecode(raw);
    return data is Map<String, dynamic> ? data : null;
  }

  @override
  Future<void> saveWrongQuestions(String status, List<dynamic> items) async {
    final box = await _open();
    await box.put('$_wrongPrefix$status', jsonEncode(items));
  }

  @override
  Future<List<dynamic>?> wrongQuestions(String status) async {
    final box = await _open();
    final raw = box.get('$_wrongPrefix$status');
    if (raw == null) return null;
    final data = jsonDecode(raw);
    return data is List<dynamic> ? data : null;
  }

  @override
  Future<void> saveStats(Map<String, dynamic> stats) async {
    final box = await _open();
    await box.put(_statsKey, jsonEncode(stats));
  }

  @override
  Future<Map<String, dynamic>?> stats() async {
    final box = await _open();
    final raw = box.get(_statsKey);
    if (raw == null) return null;
    final data = jsonDecode(raw);
    return data is Map<String, dynamic> ? data : null;
  }

  @override
  Future<void> enqueue(OfflineAttemptEntry entry) async {
    final box = await _open();
    await box.put('$_queuePrefix${entry.clientKey}', jsonEncode(entry.toJson()));
  }

  @override
  Future<List<OfflineAttemptEntry>> pendingAttempts() async {
    final box = await _open();
    final entries = <OfflineAttemptEntry>[];
    for (final key in box.keys) {
      if (key is! String || !key.startsWith(_queuePrefix)) continue;
      final raw = box.get(key);
      if (raw == null) continue;
      final data = jsonDecode(raw);
      if (data is Map<String, dynamic>) {
        entries.add(OfflineAttemptEntry.fromJson(data));
      }
    }
    entries.sort((a, b) => a.answeredAt.compareTo(b.answeredAt));
    return entries;
  }

  @override
  Future<void> removeAttempt(String clientKey) async {
    final box = await _open();
    await box.delete('$_queuePrefix$clientKey');
  }
}
