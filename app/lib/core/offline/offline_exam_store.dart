import 'dart:convert';

import 'package:hive_flutter/hive_flutter.dart';

/// 离线作答队列条目（save / submit），断网时按创建顺序重放。
class OfflineQueueEntry {
  const OfflineQueueEntry({
    required this.id,
    required this.type,
    required this.attemptId,
    required this.examId,
    required this.createdAt,
    this.answers = const [],
    this.submitToken,
    this.durationMs,
  });

  final String id;
  final String type;
  final int attemptId;
  final int examId;
  final DateTime createdAt;
  final List<Map<String, dynamic>> answers;
  final String? submitToken;
  final int? durationMs;

  Map<String, dynamic> toJson() => {
        'id': id,
        'type': type,
        'attempt_id': attemptId,
        'exam_id': examId,
        'created_at': createdAt.toIso8601String(),
        'answers': answers,
        'submit_token': submitToken,
        'duration_ms': durationMs,
      };

  factory OfflineQueueEntry.fromJson(Map<String, dynamic> json) {
    return OfflineQueueEntry(
      id: json['id'] as String? ?? '',
      type: json['type'] as String? ?? 'save',
      attemptId: json['attempt_id'] as int? ?? 0,
      examId: json['exam_id'] as int? ?? 0,
      createdAt:
          DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      answers: (json['answers'] as List<dynamic>? ?? const [])
          .map((item) => Map<String, dynamic>.from(item as Map))
          .toList(),
      submitToken: json['submit_token'] as String?,
      durationMs: json['duration_ms'] as int?,
    );
  }
}

/// 整卷离线快照：原始 attempts 响应 + 本地已答 + 剩余秒数。
class OfflineAttemptSnapshot {
  const OfflineAttemptSnapshot({
    required this.examId,
    required this.attempt,
    required this.answers,
    required this.remainingSeconds,
    required this.savedAt,
  });

  final int examId;
  final Map<String, dynamic> attempt;
  final Map<int, Map<String, dynamic>> answers;
  final int remainingSeconds;
  final DateTime savedAt;

  Map<String, dynamic> toJson() => {
        'exam_id': examId,
        'attempt': attempt,
        'answers': {
          for (final entry in answers.entries) '${entry.key}': entry.value,
        },
        'remaining_seconds': remainingSeconds,
        'saved_at': savedAt.toIso8601String(),
      };

  factory OfflineAttemptSnapshot.fromJson(Map<String, dynamic> json) {
    final rawAnswers = json['answers'] as Map<String, dynamic>? ?? const {};
    return OfflineAttemptSnapshot(
      examId: json['exam_id'] as int? ?? 0,
      attempt: Map<String, dynamic>.from(
        json['attempt'] as Map? ?? const <String, dynamic>{},
      ),
      answers: {
        for (final entry in rawAnswers.entries)
          int.tryParse(entry.key) ?? 0:
              Map<String, dynamic>.from(entry.value as Map),
      },
      remainingSeconds: json['remaining_seconds'] as int? ?? 0,
      savedAt: DateTime.tryParse(json['saved_at'] as String? ?? '') ??
          DateTime.now(),
    );
  }
}

abstract class OfflineExamStore {
  Future<OfflineAttemptSnapshot?> snapshot(int examId);
  Future<void> saveSnapshot(OfflineAttemptSnapshot snapshot);
  Future<void> enqueue(OfflineQueueEntry entry);
  Future<List<OfflineQueueEntry>> pending();
  Future<void> remove(String entryId);
  Future<void> clearForAttempt(int attemptId);
  Future<void> clearForExam(int examId);
}

/// Hive 实现：快照与队列均以 JSON 字符串存储，便于跨版本兼容。
class HiveOfflineExamStore implements OfflineExamStore {
  static const _boxName = 'offline_exam';
  static const _snapshotPrefix = 'snapshot:';
  static const _queuePrefix = 'queue:';

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
  Future<OfflineAttemptSnapshot?> snapshot(int examId) async {
    final box = await _open();
    final raw = box.get('$_snapshotPrefix$examId');
    if (raw == null) return null;
    final data = jsonDecode(raw);
    if (data is! Map<String, dynamic>) return null;
    return OfflineAttemptSnapshot.fromJson(data);
  }

  @override
  Future<void> saveSnapshot(OfflineAttemptSnapshot snapshot) async {
    final box = await _open();
    await box.put(
      '$_snapshotPrefix${snapshot.examId}',
      jsonEncode(snapshot.toJson()),
    );
  }

  @override
  Future<void> enqueue(OfflineQueueEntry entry) async {
    final box = await _open();
    await box.put('$_queuePrefix${entry.id}', jsonEncode(entry.toJson()));
  }

  @override
  Future<List<OfflineQueueEntry>> pending() async {
    final box = await _open();
    final entries = <OfflineQueueEntry>[];
    for (final key in box.keys) {
      if (key is! String || !key.startsWith(_queuePrefix)) continue;
      final raw = box.get(key);
      if (raw == null) continue;
      final data = jsonDecode(raw);
      if (data is! Map<String, dynamic>) continue;
      entries.add(OfflineQueueEntry.fromJson(data));
    }
    entries.sort((a, b) => a.createdAt.compareTo(b.createdAt));
    return entries;
  }

  @override
  Future<void> remove(String entryId) async {
    final box = await _open();
    await box.delete('$_queuePrefix$entryId');
  }

  @override
  Future<void> clearForAttempt(int attemptId) async {
    final box = await _open();
    final keys = <String>[];
    for (final key in box.keys) {
      if (key is! String || !key.startsWith(_queuePrefix)) continue;
      final raw = box.get(key);
      if (raw == null) continue;
      final data = jsonDecode(raw);
      if (data is Map<String, dynamic> && data['attempt_id'] == attemptId) {
        keys.add(key);
      }
    }
    await box.deleteAll(keys);
  }

  @override
  Future<void> clearForExam(int examId) async {
    final box = await _open();
    await box.delete('$_snapshotPrefix$examId');
    final keys = <String>[];
    for (final key in box.keys) {
      if (key is! String || !key.startsWith(_queuePrefix)) continue;
      final raw = box.get(key);
      if (raw == null) continue;
      final data = jsonDecode(raw);
      if (data is Map<String, dynamic> && data['exam_id'] == examId) {
        keys.add(key);
      }
    }
    await box.deleteAll(keys);
  }
}
