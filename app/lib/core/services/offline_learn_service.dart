import 'dart:convert';

import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/offline/offline_learn_store.dart';
import 'package:ai_learning/core/services/api_client.dart';

/// 已下载整册的元信息（版本、题量、体积、下载时间）。
class OfflineBundleMeta {
  const OfflineBundleMeta({
    required this.textbookId,
    required this.packVersion,
    required this.downloadedAt,
    required this.units,
    required this.knowledgePoints,
    required this.questions,
    required this.bytes,
  });

  final int textbookId;
  final String packVersion;
  final DateTime downloadedAt;
  final int units;
  final int knowledgePoints;
  final int questions;
  final int bytes;

  String get sizeText {
    if (bytes >= 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(bytes / 1024).toStringAsFixed(0)} KB';
  }

  factory OfflineBundleMeta.fromJson(Map<String, dynamic> json) {
    return OfflineBundleMeta(
      textbookId: json['textbook_id'] as int? ?? 0,
      packVersion: json['pack_version'] as String? ?? '',
      downloadedAt:
          DateTime.tryParse(json['downloaded_at'] as String? ?? '') ??
              DateTime.now(),
      units: json['units'] as int? ?? 0,
      knowledgePoints: json['knowledge_points'] as int? ?? 0,
      questions: json['questions'] as int? ?? 0,
      bytes: json['bytes'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() => {
        'textbook_id': textbookId,
        'pack_version': packVersion,
        'downloaded_at': downloadedAt.toIso8601String(),
        'units': units,
        'knowledge_points': knowledgePoints,
        'questions': questions,
        'bytes': bytes,
      };
}

/// 整册离线内容：下载、读取与离线答题队列的入口。
class OfflineLearnService {
  OfflineLearnService(this._api, this._store);

  final ApiClient _api;
  final OfflineLearnStore _store;

  Future<OfflineBundleMeta> download(
    int textbookId, {
    void Function(double progress)? onProgress,
  }) async {
    onProgress?.call(0.1);
    final bundle = await _api.getJson('/api/learn/textbook/$textbookId/bundle');
    onProgress?.call(0.6);
    final bytes = utf8.encode(jsonEncode(bundle)).length;
    await _store.saveBundle(textbookId, bundle);
    onProgress?.call(0.9);
    final counts = bundle['counts'] as Map<String, dynamic>? ?? const {};
    final meta = OfflineBundleMeta(
      textbookId: textbookId,
      packVersion: bundle['pack_version'] as String? ?? '',
      downloadedAt: DateTime.now(),
      units: counts['units'] as int? ?? 0,
      knowledgePoints: counts['knowledge_points'] as int? ?? 0,
      questions: counts['questions'] as int? ?? 0,
      bytes: bytes,
    );
    await _store.saveMeta(textbookId, meta.toJson());
    onProgress?.call(1);
    return meta;
  }

  Future<OfflineBundleMeta?> metaFor(int textbookId) async {
    final raw = await _store.meta(textbookId);
    return raw == null ? null : OfflineBundleMeta.fromJson(raw);
  }

  Future<bool> isDownloaded(int textbookId) async {
    return (await _store.meta(textbookId)) != null;
  }

  Future<void> remove(int textbookId) => _store.removeBundle(textbookId);

  Future<List<UnitSummary>> units(int textbookId) async {
    final bundle = await _store.bundle(textbookId);
    if (bundle == null) return const [];
    final raw = bundle['units'] as List<dynamic>? ?? const [];
    return raw
        .map((item) => UnitSummary.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<UnitDetail?> unitDetail(int chapterId) async {
    final bundle = await _bundleContaining('unit_details', chapterId);
    if (bundle == null) return null;
    final details = bundle['unit_details'] as Map<String, dynamic>? ?? const {};
    final data = details['$chapterId'];
    if (data is! Map<String, dynamic>) return null;
    return UnitDetail.fromJson(data);
  }

  Future<KpDetail?> kpDetail(int kpId) async {
    final bundle = await _bundleContaining('kp_details', kpId);
    if (bundle == null) return null;
    final details = bundle['kp_details'] as Map<String, dynamic>? ?? const {};
    final data = details['$kpId'];
    if (data is! Map<String, dynamic>) return null;
    return KpDetail.fromJson(data);
  }

  Future<List<KpExample>> kpExamples(int kpId) async {
    final localQuestions = await questions(knowledgePointId: kpId);
    final sorted = [...localQuestions]..sort((a, b) {
        final byDifficulty = a.difficulty.compareTo(b.difficulty);
        return byDifficulty != 0 ? byDifficulty : a.id.compareTo(b.id);
      });
    final examples = <KpExample>[];
    for (final question in sorted.take(2)) {
      final raw = await rawQuestion(question.id);
      if (raw == null) continue;
      examples.add(
        KpExample.fromJson({
          ...raw,
          'correct_answer': raw['answer'],
        }),
      );
    }
    return examples;
  }

  /// 本地题库（只含已发布题），供离线组卷使用。
  Future<List<Question>> questions({
    int? chapterId,
    int? knowledgePointId,
    String? subject,
    int? textbookId,
  }) async {
    final result = <Question>[];
    for (final id in await _store.downloadedTextbookIds()) {
      if (textbookId != null && id != textbookId) continue;
      final bundle = await _store.bundle(id);
      if (bundle == null) continue;
      final raw = bundle['questions'] as List<dynamic>? ?? const [];
      for (final item in raw) {
        final map = item as Map<String, dynamic>;
        if (chapterId != null && map['chapter_id'] != chapterId) continue;
        if (knowledgePointId != null &&
            map['knowledge_point_id'] != knowledgePointId) {
          continue;
        }
        if (subject != null && map['subject'] != subject) continue;
        result.add(Question.fromJson(map));
      }
    }
    return result;
  }

  /// 原始题目 JSON（含答案与解析），离线判分使用。
  Future<Map<String, dynamic>?> rawQuestion(int questionId) async {
    for (final textbookId in await _store.downloadedTextbookIds()) {
      final bundle = await _store.bundle(textbookId);
      if (bundle == null) continue;
      final raw = bundle['questions'] as List<dynamic>? ?? const [];
      for (final item in raw) {
        final map = item as Map<String, dynamic>;
        if (map['id'] == questionId) return map;
      }
    }
    return null;
  }

  Future<void> cacheHome(Map<String, dynamic> home) => _store.saveHome(home);

  Future<HomeData?> cachedHome() async {
    final raw = await _store.home();
    return raw == null ? null : HomeData.fromJson(raw);
  }

  /// 缓存错题本列表，断网时展示最近一次同步结果。
  Future<void> cacheWrongQuestions(String status, List<dynamic> items) {
    return _store.saveWrongQuestions(status, items);
  }

  Future<List<WrongQuestionItem>?> cachedWrongQuestions(String status) async {
    final raw = await _store.wrongQuestions(status);
    if (raw == null) return null;
    return raw
        .whereType<Map<String, dynamic>>()
        .map(WrongQuestionItem.fromJson)
        .toList();
  }

  /// 缓存学情统计，断网时「我的」与错题本仍可展示。
  Future<void> cacheStats(Map<String, dynamic> stats) {
    return _store.saveStats(stats);
  }

  Future<LearnStats?> cachedStats() async {
    final raw = await _store.stats();
    return raw == null ? null : LearnStats.fromJson(raw);
  }

  Future<void> enqueueAttempt(OfflineAttemptEntry entry) {
    return _store.enqueue(entry);
  }

  Future<List<OfflineAttemptEntry>> pendingAttempts() {
    return _store.pendingAttempts();
  }

  Future<void> removeAttempt(String clientKey) {
    return _store.removeAttempt(clientKey);
  }

  Future<Map<String, dynamic>?> _bundleContaining(
    String field,
    int id,
  ) async {
    for (final textbookId in await _store.downloadedTextbookIds()) {
      final bundle = await _store.bundle(textbookId);
      if (bundle == null) continue;
      final details = bundle[field] as Map<String, dynamic>? ?? const {};
      if (details.containsKey('$id')) return bundle;
    }
    return null;
  }
}
