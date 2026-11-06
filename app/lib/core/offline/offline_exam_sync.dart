import 'package:ai_learning/core/offline/offline_exam_store.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/exam_service.dart';

class OfflineSyncResult {
  const OfflineSyncResult({
    required this.saved,
    required this.remaining,
    this.submittedAttemptId,
  });

  /// 成功重放的保存条数。
  final int saved;

  /// 仍未同步的条数（通常为断网）。
  final int remaining;

  /// 若本次重放完成交卷，返回对应 attemptId。
  final int? submittedAttemptId;

  bool get online => remaining == 0;
}

/// 断网重放：按创建顺序提交本地保存/交卷队列，冲突以服务端为准。
class OfflineExamSync {
  OfflineExamSync(this._examService, this._store);

  final ExamService _examService;
  final OfflineExamStore _store;

  Future<OfflineSyncResult> replay({int? attemptId}) async {
    final entries = await _store.pending();
    var saved = 0;
    int? submitted;
    var remaining = 0;
    for (var index = 0; index < entries.length; index++) {
      final entry = entries[index];
      if (attemptId != null && entry.attemptId != attemptId) continue;
      try {
        if (entry.type == 'submit') {
          await _examService.submit(
            entry.attemptId,
            submitToken: entry.submitToken ?? 'offline-${entry.id}',
            answers: entry.answers,
            durationMs: entry.durationMs,
          );
          submitted = entry.attemptId;
        } else {
          await _examService.saveAnswers(entry.attemptId, entry.answers);
          saved += 1;
        }
        await _store.remove(entry.id);
      } on ApiException catch (error) {
        if (error.statusCode == null) {
          // 仍然断网：保留剩余条目，下次继续
          remaining = entries.length - index;
          break;
        }
        // 服务端已拒绝（如试卷已结束/已交卷）：以服务端为准，丢弃该条
        await _store.remove(entry.id);
      }
    }
    if (submitted != null) {
      await _store.clearForAttempt(submitted);
    }
    return OfflineSyncResult(
      saved: saved,
      remaining: remaining,
      submittedAttemptId: submitted,
    );
  }
}
