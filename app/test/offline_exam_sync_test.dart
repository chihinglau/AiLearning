import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/offline/offline_exam_store.dart';
import 'package:ai_learning/core/offline/offline_exam_sync.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/exam_service.dart';
import 'package:flutter_test/flutter_test.dart';

class _MemoryStore implements OfflineExamStore {
  final Map<int, OfflineAttemptSnapshot> snapshots = {};
  final List<OfflineQueueEntry> entries = [];

  @override
  Future<OfflineAttemptSnapshot?> snapshot(int examId) async => snapshots[examId];

  @override
  Future<void> saveSnapshot(OfflineAttemptSnapshot snapshot) async {
    snapshots[snapshot.examId] = snapshot;
  }

  @override
  Future<void> enqueue(OfflineQueueEntry entry) async => entries.add(entry);

  @override
  Future<List<OfflineQueueEntry>> pending() async =>
      List.of(entries..sort((a, b) => a.createdAt.compareTo(b.createdAt)));

  @override
  Future<void> remove(String entryId) async =>
      entries.removeWhere((entry) => entry.id == entryId);

  @override
  Future<void> clearForAttempt(int attemptId) async =>
      entries.removeWhere((entry) => entry.attemptId == attemptId);

  @override
  Future<void> clearForExam(int examId) async =>
      entries.removeWhere((entry) => entry.examId == examId);
}

class _FakeExamService extends ExamService {
  _FakeExamService() : super(ApiClient());

  bool offline = false;
  int? rejectStatusCode;
  final List<String> calls = [];
  int? submitted;

  @override
  Future<ExamSaveResult> saveAnswers(
    int attemptId,
    List<Map<String, dynamic>> answers,
  ) async {
    if (offline) throw const ApiException('网络不可用');
    final status = rejectStatusCode;
    if (status != null) throw ApiException('服务端拒绝', statusCode: status);
    calls.add('save:$attemptId:${answers.first['question_id']}');
    return ExamSaveResult(
      attemptId: attemptId,
      saved: answers.length,
      status: 'in_progress',
      remainingSeconds: 120,
    );
  }

  @override
  Future<ExamSubmitResult> submit(
    int attemptId, {
    required String submitToken,
    List<Map<String, dynamic>> answers = const [],
    int? durationMs,
  }) async {
    if (offline) throw const ApiException('网络不可用');
    calls.add('submit:$attemptId');
    submitted = attemptId;
    return ExamSubmitResult(attemptId: attemptId, status: 'grading');
  }
}

OfflineQueueEntry _saveEntry(int index, int attemptId) {
  return OfflineQueueEntry(
    id: 'save-$index',
    type: 'save',
    attemptId: attemptId,
    examId: 8,
    createdAt: DateTime(2026, 11, 7, 10, 0, index),
    answers: [
      {'question_id': index, 'user_answer': {'value': '本地答案 $index'}},
    ],
  );
}

void main() {
  test('断网时保留队列，联网后按顺序重放保存与交卷', () async {
    final store = _MemoryStore();
    final service = _FakeExamService();
    final sync = OfflineExamSync(service, store);
    await store.enqueue(_saveEntry(1, 31));
    await store.enqueue(_saveEntry(2, 31));
    await store.enqueue(
      OfflineQueueEntry(
        id: 'submit-3',
        type: 'submit',
        attemptId: 31,
        examId: 8,
        createdAt: DateTime(2026, 11, 7, 10, 0, 3),
        answers: const [],
        submitToken: 'offline-token',
      ),
    );

    service.offline = true;
    var result = await sync.replay(attemptId: 31);
    expect(result.saved, 0);
    expect(result.remaining, 3);
    expect(result.submittedAttemptId, isNull);
    expect(store.entries, hasLength(3));

    service.offline = false;
    result = await sync.replay(attemptId: 31);
    expect(result.saved, 2);
    expect(result.remaining, 0);
    expect(result.submittedAttemptId, 31);
    expect(service.calls, ['save:31:1', 'save:31:2', 'submit:31']);
    expect(store.entries, isEmpty);
  });

  test('服务端已拒绝的条目以服务端为准并丢弃', () async {
    final store = _MemoryStore();
    final service = _FakeExamService()..rejectStatusCode = 409;
    final sync = OfflineExamSync(service, store);
    await store.enqueue(_saveEntry(1, 31));
    await store.enqueue(_saveEntry(2, 31));

    final result = await sync.replay(attemptId: 31);

    expect(result.remaining, 0);
    expect(store.entries, isEmpty);
  });
}
