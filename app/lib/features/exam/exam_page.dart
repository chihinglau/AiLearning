import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/offline/offline_exam_store.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/features/exam/signature_answer_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 考试答题页：倒计时、3 秒防抖自动保存、答题卡、交卷确认与超时自动交卷。
class ExamPage extends ConsumerStatefulWidget {
  const ExamPage({super.key, required this.examId});

  final int examId;

  @override
  ConsumerState<ExamPage> createState() => _ExamPageState();
}

class _ExamPageState extends ConsumerState<ExamPage> {
  static const _autoSaveDelay = Duration(seconds: 3);

  ExamAttempt? _attempt;
  final Map<int, Map<String, dynamic>> _answers = {};
  final Map<int, TextEditingController> _controllers = {};
  final Set<int> _dirty = {};

  int _index = 0;
  int _remaining = 0;
  DateTime? _deadline;
  Timer? _ticker;
  Timer? _saveTimer;
  Timer? _syncTimer;

  bool _loading = true;
  String? _error;
  bool _saving = false;
  bool _submitting = false;
  bool _offline = false;
  bool _syncing = false;
  bool _offlineSubmitQueued = false;
  int _pendingSync = 0;
  Map<String, dynamic>? _rawAttempt;
  DateTime? _lastSavedAt;

  List<ExamQuestion> get _questions => _attempt?.exam.questions ?? const [];

  ExamQuestion? get _current =>
      _index >= 0 && _index < _questions.length ? _questions[_index] : null;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _ticker?.cancel();
    _saveTimer?.cancel();
    _syncTimer?.cancel();
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final (attempt, raw) =
          await ref.read(examServiceProvider).startAttemptRaw(widget.examId);
      if (!mounted) return;
      final store = ref.read(offlineExamStoreProvider);
      if (attempt.status != 'in_progress') {
        await store.clearForExam(widget.examId);
        if (!mounted) return;
        context.pushReplacement('/exam/report/${attempt.id}');
        return;
      }
      final questions = attempt.exam.questions;
      var nextIndex = attempt.nextIndex;
      if (nextIndex < 0) nextIndex = 0;
      if (questions.isNotEmpty && nextIndex >= questions.length) {
        nextIndex = questions.length - 1;
      }
      if (questions.isEmpty) nextIndex = 0;
      setState(() {
        _attempt = attempt;
        _rawAttempt = raw;
        _answers
          ..clear()
          ..addEntries(
            attempt.answers
                .where((answer) => answer.userAnswer != null)
                .map((answer) => MapEntry(answer.questionId, answer.userAnswer!)),
          );
        _index = nextIndex;
        _remaining = attempt.remainingSeconds;
        _deadline = DateTime.now().add(Duration(seconds: attempt.remainingSeconds));
        _loading = false;
        _offline = false;
      });
      await _cacheSnapshot();
      _pendingSync = await _pendingCount(attempt.id);
      await _syncPending(attempt.id, silent: true);
      _startTicker();
      _startSyncTicker();
    } on ApiException catch (error) {
      if (!mounted) return;
      if (error.statusCode == null) {
        await _loadOffline();
        return;
      }
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loading = false;
      });
    }
  }

  /// 断网时使用本地整卷快照继续作答，并合并尚未同步的本地答案。
  Future<void> _loadOffline() async {
    final store = ref.read(offlineExamStoreProvider);
    final snapshot = await store.snapshot(widget.examId);
    if (!mounted) return;
    if (snapshot == null) {
      setState(() {
        _error = '当前网络不可用，且没有本地缓存试卷';
        _loading = false;
      });
      return;
    }
    final attempt = ExamAttempt.fromJson(snapshot.attempt);
    if (attempt.status != 'in_progress') {
      setState(() {
        _error = '该试卷已结束，联网后可查看考试报告';
        _loading = false;
      });
      return;
    }
    final elapsed = DateTime.now().difference(snapshot.savedAt).inSeconds;
    var remaining = snapshot.remainingSeconds - elapsed;
    if (remaining < 0) remaining = 0;
    final pending = await store.pending();
    final answers = <int, Map<String, dynamic>>{
      for (final entry in snapshot.answers.entries)
        entry.key: Map<String, dynamic>.from(entry.value),
    };
    for (final entry in pending) {
      if (entry.attemptId != attempt.id || entry.type != 'save') continue;
      for (final answer in entry.answers) {
        final questionId = answer['question_id'];
        final value = answer['user_answer'];
        if (questionId is int && value is Map) {
          answers[questionId] = Map<String, dynamic>.from(value);
        }
      }
    }
    var nextIndex = attempt.nextIndex;
    if (nextIndex < 0) nextIndex = 0;
    if (attempt.exam.questions.isNotEmpty && nextIndex >= attempt.exam.questions.length) {
      nextIndex = attempt.exam.questions.length - 1;
    }
    if (!mounted) return;
    setState(() {
      _attempt = attempt;
      _rawAttempt = snapshot.attempt;
      _answers
        ..clear()
        ..addAll(answers);
      _index = nextIndex;
      _remaining = remaining;
      _deadline = DateTime.now().add(Duration(seconds: remaining));
      _loading = false;
      _offline = true;
      _pendingSync = pending.where((entry) => entry.attemptId == attempt.id).length;
    });
    _startTicker();
    _startSyncTicker();
  }

  Future<void> _cacheSnapshot({int? remainingSeconds}) async {
    final raw = _rawAttempt;
    if (raw == null) return;
    await ref.read(offlineExamStoreProvider).saveSnapshot(
          OfflineAttemptSnapshot(
            examId: widget.examId,
            attempt: raw,
            answers: Map<int, Map<String, dynamic>>.from(_answers),
            remainingSeconds: remainingSeconds ?? _remaining,
            savedAt: DateTime.now(),
          ),
        );
  }

  Future<int> _pendingCount(int attemptId) async {
    final entries = await ref.read(offlineExamStoreProvider).pending();
    return entries.where((entry) => entry.attemptId == attemptId).length;
  }

  void _startSyncTicker() {
    _syncTimer?.cancel();
    _syncTimer = Timer.periodic(const Duration(seconds: 12), (_) {
      final attempt = _attempt;
      if (attempt == null) return;
      if (_pendingSync > 0 || _offline) unawaited(_syncPending(attempt.id));
    });
  }

  /// 重放离线队列：保存逐条上传，交卷成功后跳转报告。
  Future<void> _syncPending(int attemptId, {bool silent = false}) async {
    if (_syncing || _submitting) return;
    final entries = await ref.read(offlineExamStoreProvider).pending();
    if (!entries.any((entry) => entry.attemptId == attemptId)) {
      if (mounted) setState(() => _pendingSync = 0);
      return;
    }
    _syncing = true;
    try {
      final result = await ref.read(offlineExamSyncProvider).replay(attemptId: attemptId);
      if (!mounted) return;
      setState(() {
        _pendingSync = result.remaining;
        if (result.remaining == 0) _offline = false;
      });
      if (result.submittedAttemptId != null) {
        await ref.read(offlineExamStoreProvider).clearForExam(widget.examId);
        if (!mounted) return;
        _ticker?.cancel();
        _syncTimer?.cancel();
        context.pushReplacement('/exam/report/${result.submittedAttemptId}');
        return;
      }
      if (!silent && result.saved > 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('已同步 ${result.saved} 条离线作答')),
        );
      }
    } finally {
      _syncing = false;
    }
  }

  void _startTicker() {
    _ticker?.cancel();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      final deadline = _deadline;
      if (deadline == null) return;
      final remaining = deadline.difference(DateTime.now()).inSeconds;
      if (remaining <= 0) {
        _ticker?.cancel();
        setState(() => _remaining = 0);
        unawaited(_doSubmit(auto: true));
      } else {
        setState(() => _remaining = remaining);
      }
    });
  }

  // ------------------------------------------------------------------
  // 作答与自动保存
  // ------------------------------------------------------------------

  TextEditingController _controllerFor(int questionId) {
    return _controllers.putIfAbsent(questionId, () {
      final value = _answers[questionId]?['value'];
      return TextEditingController(text: value is String ? value : '');
    });
  }

  void _setAnswer(int questionId, Map<String, dynamic>? answer) {
    setState(() {
      if (answer == null) {
        _answers.remove(questionId);
      } else {
        _answers[questionId] = answer;
      }
    });
    _dirty.add(questionId);
    _saveTimer?.cancel();
    _saveTimer = Timer(_autoSaveDelay, () => unawaited(_flushSave()));
  }

  Future<void> _flushSave() async {
    final attempt = _attempt;
    if (attempt == null || _submitting || attempt.status != 'in_progress') {
      return;
    }
    if (_dirty.isEmpty) return;
    final ids = _dirty.toList();
    _dirty.removeAll(ids);
    final payload = [
      for (final id in ids)
        {'question_id': id, 'user_answer': _answers[id]},
    ];
    setState(() => _saving = true);
    try {
      final result =
          await ref.read(examServiceProvider).saveAnswers(attempt.id, payload);
      if (!mounted) return;
      if (result.status != 'in_progress') {
        _ticker?.cancel();
        await ref.read(offlineExamStoreProvider).clearForExam(widget.examId);
        if (!mounted) return;
        context.pushReplacement('/exam/report/${attempt.id}');
        return;
      }
      _deadline = DateTime.now().add(Duration(seconds: result.remainingSeconds));
      setState(() {
        _saving = false;
        _offline = false;
        _lastSavedAt = DateTime.now();
      });
      await _cacheSnapshot(remainingSeconds: result.remainingSeconds);
      if (_pendingSync > 0) {
        unawaited(_syncPending(attempt.id, silent: true));
      }
    } on ApiException catch (error) {
      if (!mounted) return;
      if (error.statusCode == null) {
        // 断网：写入本地队列，联网后按顺序重放
        await _queueSave(attempt, payload);
        if (!mounted) return;
        setState(() {
          _saving = false;
          _offline = true;
          _lastSavedAt = DateTime.now();
        });
        return;
      }
      _dirty.addAll(ids);
      setState(() => _saving = false);
      await handleApiError(context, ref, error);
    }
  }

  Future<void> _queueSave(
    ExamAttempt attempt,
    List<Map<String, dynamic>> payload,
  ) async {
    final store = ref.read(offlineExamStoreProvider);
    await store.enqueue(
      OfflineQueueEntry(
        id: '${attempt.id}-save-${DateTime.now().microsecondsSinceEpoch}',
        type: 'save',
        attemptId: attempt.id,
        examId: widget.examId,
        createdAt: DateTime.now(),
        answers: payload,
      ),
    );
    await _cacheSnapshot();
    if (!mounted) return;
    final pending = await _pendingCount(attempt.id);
    if (!mounted) return;
    setState(() => _pendingSync = pending);
  }

  // ------------------------------------------------------------------
  // 交卷
  // ------------------------------------------------------------------

  Future<void> _confirmSubmit() async {
    final total = _questions.length;
    final unanswered =
        _questions.where((item) => _answers[item.question.id] == null).length;
    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('确认交卷？'),
        content: Text(
          unanswered > 0
              ? '还有 $unanswered / $total 题未作答，交卷后不能修改。'
              : '全部 $total 题已作答，交卷后不能修改。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('继续检查'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('确认交卷'),
          ),
        ],
      ),
    );
    if (result == true) {
      await _doSubmit();
    }
  }

  Future<void> _doSubmit({bool auto = false}) async {
    final attempt = _attempt;
    if (attempt == null || _submitting) return;
    if (attempt.status != 'in_progress') {
      context.pushReplacement('/exam/report/${attempt.id}');
      return;
    }
    _saveTimer?.cancel();
    _ticker?.cancel();
    setState(() => _submitting = true);
    final limitSeconds = attempt.exam.timeLimitMin * 60;
    final rawElapsed = limitSeconds - _remaining;
    final elapsed =
        rawElapsed < 0 ? 0 : (rawElapsed > limitSeconds ? limitSeconds : rawElapsed);
    try {
      final result = await ref.read(examServiceProvider).submit(
            attempt.id,
            submitToken: attempt.submitToken ??
                'client-${DateTime.now().millisecondsSinceEpoch}',
            answers: [
              for (final entry in _answers.entries)
                {'question_id': entry.key, 'user_answer': entry.value},
            ],
            durationMs: elapsed * 1000,
          );
      if (!mounted) return;
      await ref.read(offlineExamStoreProvider).clearForExam(widget.examId);
      if (!mounted) return;
      if (auto) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('考试时间已到，系统已自动交卷')),
        );
      }
      context.pushReplacement('/exam/report/${result.attemptId}');
    } on ApiException catch (error) {
      if (!mounted) return;
      if (error.statusCode == null) {
        // 断网交卷：保留整卷与答案，联网后自动重放交卷
        await ref.read(offlineExamStoreProvider).enqueue(
              OfflineQueueEntry(
                id: '${attempt.id}-submit-${DateTime.now().microsecondsSinceEpoch}',
                type: 'submit',
                attemptId: attempt.id,
                examId: widget.examId,
                createdAt: DateTime.now(),
                answers: [
                  for (final entry in _answers.entries)
                    {'question_id': entry.key, 'user_answer': entry.value},
                ],
                submitToken: attempt.submitToken ??
                    'offline-${DateTime.now().millisecondsSinceEpoch}',
                durationMs: elapsed * 1000,
              ),
            );
        await _cacheSnapshot();
        if (!mounted) return;
        final pending = await _pendingCount(attempt.id);
        if (!mounted) return;
        setState(() {
          _submitting = false;
          _offline = true;
          _offlineSubmitQueued = true;
          _pendingSync = pending;
        });
        _startSyncTicker();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('网络中断，交卷已暂存到本地，联网后将自动提交')),
        );
        return;
      }
      setState(() => _submitting = false);
      await handleApiError(context, ref, error);
    }
  }

  Future<void> _confirmExit() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('退出考试？'),
        content: const Text('退出后计时不会暂停，已作答内容会自动保存，可在考试中心继续作答。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('继续考试'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('退出'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    _saveTimer?.cancel();
    await _flushSave();
    _ticker?.cancel();
    if (mounted) context.pop();
  }

  // ------------------------------------------------------------------
  // 构建
  // ------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final attempt = _attempt;
    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: _loading || _error != null ? () => context.pop() : _confirmExit,
        ),
        title: Text(attempt?.exam.title ?? '考试'),
        actions: [
          if (attempt != null)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: Center(child: _CountdownBadge(remaining: _remaining)),
            ),
        ],
      ),
      body: _buildBody(context),
      bottomNavigationBar: attempt == null ? null : _buildBottomBar(context),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(_error!, textAlign: TextAlign.center),
            ),
            const SizedBox(height: 12),
            FilledButton(onPressed: _load, child: const Text('重试')),
            TextButton(onPressed: () => context.pop(), child: const Text('返回考试中心')),
          ],
        ),
      );
    }
    if (_offlineSubmitQueued) {
      final attempt = _attempt;
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_upload_outlined, size: 56),
              const SizedBox(height: 12),
              Text('交卷已暂存到本地', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 4),
              Text(
                '当前网络不可用，待同步 $_pendingSync 条。联网后将自动提交，也可点击下方重试。',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 16),
              FilledButton(
                key: const ValueKey('offline-submit-retry'),
                onPressed: attempt == null
                    ? null
                    : () => unawaited(_syncPending(attempt.id)),
                child: const Text('立即重试'),
              ),
              TextButton(
                onPressed: () => context.pop(),
                child: const Text('返回考试中心'),
              ),
            ],
          ),
        ),
      );
    }
    final item = _current;
    if (item == null) {
      return const Center(child: Text('试卷暂无题目'));
    }
    final theme = Theme.of(context);
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (_offline || _pendingSync > 0) ...[
            _OfflineBanner(
              pending: _pendingSync,
              onRetry: () {
                final attempt = _attempt;
                if (attempt != null) unawaited(_syncPending(attempt.id));
              },
            ),
            const SizedBox(height: 12),
          ],
          Text(
            '第 ${_index + 1} / ${_questions.length} 题'
            ' · ${_typeLabel(item.question.qType)} · ${item.score.round()} 分',
            style: theme.textTheme.bodySmall,
          ),
          if (item.sectionName != null && item.sectionName!.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(item.sectionName!, style: theme.textTheme.bodySmall),
          ],
          const SizedBox(height: 12),
          Text(item.question.stem, style: theme.textTheme.titleLarge),
          const SizedBox(height: 20),
          _buildAnswerArea(item.question),
          const SizedBox(height: 24),
          _AnswerSheet(
            questions: _questions,
            answers: _answers,
            currentIndex: _index,
            onSelect: (index) => setState(() => _index = index),
          ),
          const SizedBox(height: 12),
          Center(
            child: Text(
              _saving
                  ? '保存中…'
                  : _lastSavedAt == null
                      ? '答案将每 3 秒自动保存'
                      : '已自动保存 ${_timeLabel(_lastSavedAt!)}',
              style: theme.textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }

  Uint8List _decodeImage(String dataUrl) {
    final comma = dataUrl.indexOf(',');
    final payload = comma >= 0 ? dataUrl.substring(comma + 1) : dataUrl;
    return base64Decode(payload);
  }

  Future<void> _addImageAnswer(Question question) async {
    final images =
        (_answers[question.id]?['images'] as List<dynamic>? ?? const [])
            .whereType<String>()
            .toList();
    if (images.length >= 2) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('每道题最多上传 2 张图片')),
      );
      return;
    }
    final dataUrl = await Navigator.of(context).push<String>(
      MaterialPageRoute(
        builder: (routeContext) =>
            SignatureAnswerPage(questionStem: question.stem),
      ),
    );
    if (dataUrl == null || !mounted) return;
    final current = Map<String, dynamic>.from(
      _answers[question.id] ?? const <String, dynamic>{},
    );
    current['images'] = [...images, dataUrl];
    _setAnswer(question.id, current);
  }

  Widget _buildAnswerArea(Question question) {
    final value = _answers[question.id]?['value'];
    switch (question.qType) {
      case 'multiple':
        final selected =
            value is List ? value.map((item) => item.toString()).toSet() : <String>{};
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('（多选题，可选多个答案）', style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 8),
            for (final option in question.options)
              Card(
                child: CheckboxListTile(
                  value: selected.contains(option.key),
                  onChanged: (checked) {
                    final next = {...selected};
                    if (checked == true) {
                      next.add(option.key);
                    } else {
                      next.remove(option.key);
                    }
                    _setAnswer(
                      question.id,
                      next.isEmpty ? null : {'value': next.toList()..sort()},
                    );
                  },
                  secondary: CircleAvatar(child: Text(option.key)),
                  title: Text(option.text),
                ),
              ),
          ],
        );
      case 'fill':
      case 'calc':
      case 'answer':
      case 'listen':
        final subjective = question.qType != 'fill';
        final images = (_answers[question.id]?['images'] as List<dynamic>? ?? const [])
            .whereType<String>()
            .toList();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _controllerFor(question.id),
              minLines: subjective ? 4 : 1,
              maxLines: subjective ? 8 : 1,
              textInputAction:
                  subjective ? TextInputAction.newline : TextInputAction.done,
              onChanged: (text) {
                final current = Map<String, dynamic>.from(
                  _answers[question.id] ?? const <String, dynamic>{},
                );
                if (text.trim().isEmpty) {
                  current.remove('value');
                } else {
                  current['value'] = text.trim();
                }
                _setAnswer(
                  question.id,
                  current.isEmpty ? null : current,
                );
              },
              decoration: InputDecoration(
                labelText: subjective ? '请写出解答过程与答案' : '请在此填写答案',
                helperText:
                    subjective ? '主观题交卷后由老师批改，可先写下思路与结果，也可手写拍照上传。' : null,
                border: const OutlineInputBorder(),
                prefixIcon: const Icon(Icons.edit_outlined),
              ),
            ),
            if (subjective) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  OutlinedButton.icon(
                    key: ValueKey('image-answer-${question.id}'),
                    onPressed: () => _addImageAnswer(question),
                    icon: const Icon(Icons.draw_outlined),
                    label: const Text('手写图片作答'),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    images.isEmpty ? '最多 2 张' : '已添加 ${images.length}/2 张',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
              if (images.isNotEmpty) ...[
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (var index = 0; index < images.length; index++)
                      Stack(
                        children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: Image.memory(
                              _decodeImage(images[index]),
                              width: 120,
                              height: 90,
                              fit: BoxFit.cover,
                            ),
                          ),
                          Positioned(
                            right: 0,
                            top: 0,
                            child: Material(
                              color: Colors.black54,
                              shape: const CircleBorder(),
                              child: InkWell(
                                key: ValueKey('remove-image-${question.id}-$index'),
                                onTap: () {
                                  final next = List<String>.from(images)..removeAt(index);
                                  final current = Map<String, dynamic>.from(
                                    _answers[question.id] ?? const {},
                                  );
                                  if (next.isEmpty) {
                                    current.remove('images');
                                  } else {
                                    current['images'] = next;
                                  }
                                  _setAnswer(
                                    question.id,
                                    current.isEmpty ? null : current,
                                  );
                                },
                                child: const Padding(
                                  padding: EdgeInsets.all(3),
                                  child: Icon(
                                    Icons.close,
                                    size: 14,
                                    color: Colors.white,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                  ],
                ),
              ],
            ],
          ],
        );
      default:
        // choice / judge 均为单选（judge 选项为 正确 / 错误）。
        return Column(
          children: [
            for (final option in question.options)
              Card(
                child: ListTile(
                  selected: value == option.key,
                  leading: CircleAvatar(child: Text(option.key)),
                  title: Text(option.text),
                  onTap: () => _setAnswer(question.id, {'value': option.key}),
                ),
              ),
          ],
        );
    }
  }

  Widget _buildBottomBar(BuildContext context) {
    final isLast = _index + 1 >= _questions.length;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
        child: Row(
          children: [
            OutlinedButton(
              onPressed: _index == 0 ? null : () => setState(() => _index -= 1),
              child: const Text('上一题'),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FilledButton(
                onPressed: _submitting
                    ? null
                    : isLast
                        ? _confirmSubmit
                        : () => setState(() => _index += 1),
                child: _submitting
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(isLast ? '交卷' : '下一题'),
              ),
            ),
            if (!isLast) ...[
              const SizedBox(width: 12),
              TextButton(
                onPressed: _submitting ? null : _confirmSubmit,
                child: const Text('交卷'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _timeLabel(DateTime time) {
    String two(int value) => value.toString().padLeft(2, '0');
    return '${two(time.hour)}:${two(time.minute)}:${two(time.second)}';
  }

  String _typeLabel(String type) {
    switch (type) {
      case 'multiple':
        return '多选题';
      case 'judge':
        return '判断题';
      case 'fill':
        return '填空题';
      case 'calc':
        return '计算题';
      case 'answer':
        return '解答题';
      case 'listen':
        return '听力题';
      default:
        return '单选题';
    }
  }
}

class _OfflineBanner extends StatelessWidget {
  const _OfflineBanner({required this.pending, required this.onRetry});

  final int pending;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.orange.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.orange.withValues(alpha: 0.5)),
      ),
      child: Row(
        children: [
          const Icon(Icons.cloud_off_outlined, color: Colors.orange, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              pending > 0
                  ? '网络不可用，作答已保存到本地（待同步 $pending 条）'
                  : '网络不可用，作答已保存到本地',
              style: theme.textTheme.bodySmall,
            ),
          ),
          TextButton(
            key: const ValueKey('offline-sync-retry'),
            onPressed: onRetry,
            child: const Text('重试'),
          ),
        ],
      ),
    );
  }
}

class _CountdownBadge extends StatelessWidget {
  const _CountdownBadge({required this.remaining});

  final int remaining;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final warning = remaining <= 300;
    final minute = remaining ~/ 60;
    final second = remaining % 60;
    final text = '${minute.toString().padLeft(2, '0')}:'
        '${second.toString().padLeft(2, '0')}';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: (warning ? Colors.red : theme.colorScheme.primary)
            .withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(
            Icons.timer_outlined,
            size: 16,
            color: warning ? Colors.red : theme.colorScheme.primary,
          ),
          const SizedBox(width: 4),
          Text(
            text,
            style: theme.textTheme.titleSmall?.copyWith(
              color: warning ? Colors.red : theme.colorScheme.primary,
            ),
          ),
        ],
      ),
    );
  }
}

class _AnswerSheet extends StatelessWidget {
  const _AnswerSheet({
    required this.questions,
    required this.answers,
    required this.currentIndex,
    required this.onSelect,
  });

  final List<ExamQuestion> questions;
  final Map<int, Map<String, dynamic>> answers;
  final int currentIndex;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final answeredCount = questions
        .where((item) => answers[item.question.id] != null)
        .length;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '答题卡 · 已答 $answeredCount / ${questions.length}',
              style: theme.textTheme.titleSmall,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (var i = 0; i < questions.length; i++)
                  _SheetCell(
                    index: i,
                    answered: answers[questions[i].question.id] != null,
                    current: i == currentIndex,
                    onTap: () => onSelect(i),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SheetCell extends StatelessWidget {
  const _SheetCell({
    required this.index,
    required this.answered,
    required this.current,
    required this.onTap,
  });

  final int index;
  final bool answered;
  final bool current;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final background = current
        ? theme.colorScheme.primary
        : answered
            ? theme.colorScheme.primaryContainer
            : theme.colorScheme.surfaceContainerHighest;
    final foreground = current
        ? theme.colorScheme.onPrimary
        : answered
            ? theme.colorScheme.onPrimaryContainer
            : theme.colorScheme.onSurfaceVariant;
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: Container(
        width: 36,
        height: 36,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          '${index + 1}',
          style: theme.textTheme.labelLarge?.copyWith(color: foreground),
        ),
      ),
    );
  }
}
