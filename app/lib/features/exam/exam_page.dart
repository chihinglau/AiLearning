import 'dart:async';

import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
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

  bool _loading = true;
  String? _error;
  bool _saving = false;
  bool _submitting = false;
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
      final attempt = await ref.read(examServiceProvider).startAttempt(widget.examId);
      if (!mounted) return;
      if (attempt.status != 'in_progress') {
        context.go('/exam/report/${attempt.id}');
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
      });
      _startTicker();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loading = false;
      });
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
        context.go('/exam/report/${attempt.id}');
        return;
      }
      _deadline = DateTime.now().add(Duration(seconds: result.remainingSeconds));
      setState(() {
        _saving = false;
        _lastSavedAt = DateTime.now();
      });
    } on ApiException catch (error) {
      _dirty.addAll(ids);
      if (!mounted) return;
      setState(() => _saving = false);
      await handleApiError(context, ref, error);
    }
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
      context.go('/exam/report/${attempt.id}');
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
      if (auto) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('考试时间已到，系统已自动交卷')),
        );
      }
      context.go('/exam/report/${result.attemptId}');
    } on ApiException catch (error) {
      if (!mounted) return;
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
        return TextField(
          controller: _controllerFor(question.id),
          minLines: subjective ? 4 : 1,
          maxLines: subjective ? 8 : 1,
          textInputAction: subjective ? TextInputAction.newline : TextInputAction.done,
          onChanged: (text) => _setAnswer(
            question.id,
            text.trim().isEmpty ? null : {'value': text.trim()},
          ),
          decoration: InputDecoration(
            labelText: subjective ? '请写出解答过程与答案' : '请在此填写答案',
            helperText: subjective ? '主观题交卷后由老师批改，可先写下思路与结果。' : null,
            border: const OutlineInputBorder(),
            prefixIcon: const Icon(Icons.edit_outlined),
          ),
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
