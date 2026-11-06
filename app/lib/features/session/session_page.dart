import 'dart:async';
import 'dart:convert';

import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/models/practice_session.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/learn_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 自适应练习 / 错题复习 / 断点续答的通用答题页。
///
/// 支持 choice（单选）、multiple（多选）、judge（判断）、fill（填空）四种题型。
class SessionPage extends ConsumerStatefulWidget {
  const SessionPage({
    super.key,
    required this.title,
    this.knowledgePointId,
    this.chapterId,
    this.subject,
    this.reviewMode = false,
    this.sessionId,
    this.scopeType,
    this.scopeIds = const [],
    this.count = 10,
    this.qTypes = const [],
    this.mode = 'special',
    this.seed,
  });

  final String title;
  final int? knowledgePointId;
  final int? chapterId;
  final String? subject;
  final bool reviewMode;

  /// 断点续答会话 ID（/session?session=xx）。
  final int? sessionId;

  /// 新练习范围（/session?scope=kp&ids=..&count=..&qtypes=..&mode=..&seed=..）。
  final String? scopeType;
  final List<int> scopeIds;
  final int count;
  final List<String> qTypes;
  final String mode;
  final int? seed;

  @override
  ConsumerState<SessionPage> createState() => _SessionPageState();
}

class _SessionPageState extends ConsumerState<SessionPage> {
  static const _lastSessionKey = 'practice_last_session';

  final _fillController = TextEditingController();

  List<Question> _questions = const [];
  int _index = 0;
  int _correctCount = 0;
  int _answeredCount = 0;
  int? _sessionId;
  int? _resumeId;
  int? _seed;
  String? _selectedKey;
  final Set<String> _selectedKeys = {};
  LearnSubmitResult? _result;
  PracticeFinish? _finish;
  bool _loading = true;
  bool _submitting = false;
  bool _finished = false;
  String? _error;
  DateTime _startedAt = DateTime.now();

  String get _source => widget.reviewMode ? 'review' : 'practice';

  Question? get _current => _index < _questions.length ? _questions[_index] : null;

  @override
  void initState() {
    super.initState();
    _resumeId = widget.sessionId;
    _seed = widget.seed;
    _load();
  }

  @override
  void dispose() {
    _fillController.dispose();
    super.dispose();
  }

  Future<void> _load({bool newSeed = false}) async {
    setState(() {
      _loading = true;
      _error = null;
      _finished = false;
      _finish = null;
      _index = 0;
      _correctCount = 0;
      _answeredCount = 0;
      _sessionId = null;
      _selectedKey = null;
      _selectedKeys.clear();
      _result = null;
    });
    if (newSeed) {
      _resumeId = null;
      _seed = null;
    }
    final service = ref.read(learnServiceProvider);
    try {
      if (_resumeId != null) {
        await _resume(service, _resumeId!);
      } else if (widget.scopeType != null) {
        await _startScoped(service);
      } else {
        final questions = widget.reviewMode
            ? await service.reviewToday()
            : await service.start(
                knowledgePointId: widget.knowledgePointId,
                chapterId: widget.chapterId,
                subject: widget.subject,
              );
        if (!mounted) return;
        setState(() {
          _questions = questions;
          _loading = false;
          _startedAt = DateTime.now();
        });
      }
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loading = false;
      });
    }
  }

  Future<void> _resume(LearnService service, int sessionId) async {
    final data = await service.sessionDetail(sessionId);
    if (!mounted) return;
    final nextIndex = data.nextIndex.clamp(
      0,
      data.questions.isEmpty ? 0 : data.questions.length - 1,
    );
    setState(() {
      _questions = data.questions;
      _sessionId = data.id;
      _correctCount = data.correctCount;
      _answeredCount = data.answeredCount;
      _index = nextIndex;
      _loading = false;
      _startedAt = DateTime.now();
    });
    if (data.nextIndex >= data.questions.length) {
      await _finishSession();
    } else {
      unawaited(_rememberSession());
    }
  }

  Future<void> _startScoped(LearnService service, {bool confirm = false}) async {
    try {
      final result = await service.startPractice(
        scopeType: widget.scopeType!,
        scopeIds: widget.scopeIds,
        count: widget.count,
        qTypes: widget.qTypes,
        mode: widget.mode,
        seed: _seed,
        confirmMismatch: confirm,
      );
      if (!mounted) return;
      if (result.questions.isEmpty) {
        setState(() {
          _error = '该范围暂无可用题目，请调整范围或题型后重试。';
          _loading = false;
        });
        return;
      }
      setState(() {
        _questions = result.questions;
        _sessionId = result.sessionId;
        _seed = result.seed ?? _seed;
        _loading = false;
        _startedAt = DateTime.now();
      });
      unawaited(_rememberSession());
    } on ApiException catch (error) {
      if (error.code == 'TEXTBOOK_MISMATCH' && !confirm) {
        final accepted = await _confirmMismatch();
        if (accepted) {
          await _startScoped(service, confirm: true);
        } else if (mounted) {
          context.pop();
        }
        return;
      }
      rethrow;
    }
  }

  Future<bool> _confirmMismatch() async {
    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('教材与年级不一致'),
        content: const Text(
          '当前绑定的教材与你的年级不一致，继续将按当前教材范围组卷。'
          '建议先在「教材管理」切换为当前年级教材。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('返回调整'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('继续练习'),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  Future<void> _rememberSession() async {
    final id = _sessionId;
    if (id == null || _questions.isEmpty) return;
    if (_answeredCount >= _questions.length) return;
    try {
      await ref.read(platformPalProvider).storage.write(
            _lastSessionKey,
            jsonEncode({
              'id': id,
              'title': widget.title,
              'total': _questions.length,
              'answered': _answeredCount,
            }),
          );
    } catch (_) {
      // 本地草稿失败不阻断答题。
    }
  }

  Future<void> _clearRememberedSession() async {
    try {
      await ref.read(platformPalProvider).storage.delete(_lastSessionKey);
    } catch (_) {
      // 忽略本地清理失败。
    }
  }

  bool get _canSubmit {
    final question = _current;
    if (question == null || _result != null) return false;
    switch (question.qType) {
      case 'multiple':
        return _selectedKeys.isNotEmpty;
      case 'fill':
        return _fillController.text.trim().isNotEmpty;
      default:
        return _selectedKey != null;
    }
  }

  Future<void> _submit() async {
    final question = _current;
    if (question == null || !_canSubmit) return;

    final Map<String, dynamic> userAnswer;
    switch (question.qType) {
      case 'multiple':
        userAnswer = {'value': _selectedKeys.toList()..sort()};
      case 'fill':
        userAnswer = {'value': _fillController.text.trim()};
      default:
        userAnswer = {'value': _selectedKey};
    }

    setState(() => _submitting = true);
    try {
      final result = await ref.read(learnServiceProvider).submit(
            questionId: question.id,
            userAnswer: userAnswer,
            durationMs: DateTime.now().difference(_startedAt).inMilliseconds,
            sessionId: _sessionId,
            source: _source,
          );
      if (!mounted) return;
      setState(() {
        _result = result;
        _answeredCount += 1;
        if (result.isCorrect) _correctCount += 1;
      });
      unawaited(_rememberSession());
    } on ApiException catch (error) {
      if (!mounted) return;
      await handleApiError(context, ref, error);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _next() async {
    if (_index + 1 >= _questions.length) {
      await _finishSession();
      return;
    }
    setState(() {
      _index += 1;
      _selectedKey = null;
      _selectedKeys.clear();
      _fillController.clear();
      _result = null;
      _startedAt = DateTime.now();
    });
    unawaited(_rememberSession());
  }

  Future<void> _finishSession() async {
    final sessionId = _sessionId;
    if (sessionId == null) {
      setState(() => _finished = true);
      await _clearRememberedSession();
      return;
    }
    try {
      final finish =
          await ref.read(learnServiceProvider).finishSession(sessionId);
      if (!mounted) return;
      setState(() {
        _finish = finish;
        _correctCount = finish.session.correctCount;
        _answeredCount = finish.session.answeredCount;
        _finished = true;
      });
      await _clearRememberedSession();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _finished = true);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiErrorGuide.from(error).message)),
      );
    }
  }

  void _retry() {
    if (widget.scopeType != null || widget.reviewMode) {
      _load(newSeed: true);
    } else {
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: _buildBody(context),
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
          ],
        ),
      );
    }
    if (widget.reviewMode && _questions.isEmpty) {
      return _EmptyReview(onBack: () => context.go('/shell'));
    }
    if (_finished) {
      return _Summary(
        title: widget.title,
        total: _finish?.session.totalCount ?? _questions.length,
        correct: _finish?.session.correctCount ?? _correctCount,
        reviewMode: widget.reviewMode,
        finish: _finish,
        onRetry: _retry,
        onWrongBook: () => context.go('/shell?tab=1'),
      );
    }
    final question = _current;
    if (question == null) {
      return const Center(child: Text('暂无题目'));
    }
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (_resumeId != null && _answeredCount > 0)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                '续答：已完成 $_answeredCount 题，从第 ${_index + 1} 题继续',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
          Text(
            '第 ${_index + 1} / ${_questions.length} 题 · ${_typeLabel(question.qType)}'
            ' · 难度 ${question.difficulty}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 12),
          Text(question.stem, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 20),
          _buildAnswerArea(question),
          const SizedBox(height: 20),
          if (_result == null)
            FilledButton(
              onPressed: _canSubmit && !_submitting ? _submit : null,
              child: _submitting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('提交答案'),
            )
          else
            _FeedbackCard(
              result: _result!,
              question: question,
              onNext: _next,
              isLast: _index + 1 >= _questions.length,
            ),
        ],
      ),
    );
  }

  Widget _buildAnswerArea(Question question) {
    final locked = _result != null;
    switch (question.qType) {
      case 'multiple':
        return Column(
          children: [
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                '（多选题，可选多个答案）',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
            const SizedBox(height: 8),
            for (final option in question.options)
              Card(
                child: CheckboxListTile(
                  value: _selectedKeys.contains(option.key),
                  onChanged: locked
                      ? null
                      : (checked) {
                          setState(() {
                            if (checked == true) {
                              _selectedKeys.add(option.key);
                            } else {
                              _selectedKeys.remove(option.key);
                            }
                          });
                        },
                  secondary: CircleAvatar(child: Text(option.key)),
                  title: Text(option.text),
                ),
              ),
          ],
        );
      case 'fill':
        return TextField(
          controller: _fillController,
          enabled: !locked,
          textInputAction: TextInputAction.done,
          onSubmitted: locked ? null : (_) => _submit(),
          onChanged: locked ? null : (_) => setState(() {}),
          decoration: const InputDecoration(
            labelText: '请在此填写答案',
            border: OutlineInputBorder(),
            prefixIcon: Icon(Icons.edit_outlined),
          ),
        );
      default:
        // choice / judge 都是单选（judge 的选项为 正确 / 错误）。
        return Column(
          children: [
            for (final option in question.options)
              Card(
                child: ListTile(
                  selected: _selectedKey == option.key,
                  leading: CircleAvatar(child: Text(option.key)),
                  title: Text(option.text),
                  onTap: locked
                      ? null
                      : () => setState(() => _selectedKey = option.key),
                ),
              ),
          ],
        );
    }
  }

  String _typeLabel(String type) {
    switch (type) {
      case 'multiple':
        return '多选题';
      case 'judge':
        return '判断题';
      case 'fill':
        return '填空题';
      default:
        return '单选题';
    }
  }
}

class _FeedbackCard extends StatelessWidget {
  const _FeedbackCard({
    required this.result,
    required this.question,
    required this.onNext,
    required this.isLast,
  });

  final LearnSubmitResult result;
  final Question question;
  final VoidCallback onNext;
  final bool isLast;

  String _formatAnswer(dynamic value) {
    String optionText(String key) {
      for (final option in question.options) {
        if (option.key == key) return '$key. ${option.text}';
      }
      return key;
    }

    if (question.qType == 'judge') {
      return value == 'T' ? '正确（T）' : '错误（F）';
    }
    if (value is List) {
      return value.map((e) => optionText(e.toString())).join('；');
    }
    if (question.options.isNotEmpty) {
      return optionText(value?.toString() ?? '-');
    }
    return value?.toString() ?? '-';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final correctColor =
        result.isCorrect ? Colors.green.shade700 : theme.colorScheme.error;
    final rawValue = result.correctAnswer['value'];
    return Card(
      color: theme.colorScheme.surfaceContainerHighest,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  result.isCorrect ? Icons.check_circle : Icons.cancel,
                  color: correctColor,
                ),
                const SizedBox(width: 8),
                Text(
                  result.isCorrect ? '回答正确' : '回答错误',
                  style: theme.textTheme.titleMedium?.copyWith(color: correctColor),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text('正确答案：${_formatAnswer(rawValue)}'),
            if (result.analysis != null && result.analysis!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('解析：${result.analysis!}', style: theme.textTheme.bodyMedium),
            ],
            if (result.masteryScore != null) ...[
              const SizedBox(height: 8),
              Text(
                '当前知识点掌握度：${result.masteryScore!.round()} 分',
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
            if (!result.isCorrect && result.inWrongBook) ...[
              const SizedBox(height: 4),
              Row(
                children: [
                  Icon(
                    Icons.bookmark_added,
                    size: 16,
                    color: theme.colorScheme.error,
                  ),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      '已收入错题本，明天可在「错题本」中复习。',
                      style: theme.textTheme.bodySmall,
                    ),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 12),
            FilledButton(
              onPressed: onNext,
              child: Text(isLast ? '完成练习' : '下一题'),
            ),
          ],
        ),
      ),
    );
  }
}

class _Summary extends StatelessWidget {
  const _Summary({
    required this.title,
    required this.total,
    required this.correct,
    required this.reviewMode,
    required this.finish,
    required this.onRetry,
    required this.onWrongBook,
  });

  final String title;
  final int total;
  final int correct;
  final bool reviewMode;
  final PracticeFinish? finish;
  final VoidCallback onRetry;
  final VoidCallback onWrongBook;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final data = finish;
    final rate = data != null
        ? (data.accuracy * 100).round()
        : (total == 0 ? 0 : (correct * 100 / total).round());
    final durationMinute =
        data == null ? 0 : (data.durationMs / 60000).ceil();
    final actions = data?.nextActions ?? const ['replay', 'wrong_book', 'back'];
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Icon(
            Icons.emoji_events_outlined,
            size: 72,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(height: 16),
          Text(
            reviewMode ? '今日复习完成' : '本次练习完成',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Text(title),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _Stat(label: '正确率', value: '$rate%'),
                  _Stat(label: '答对', value: '$correct/$total'),
                  _Stat(
                    label: '用时',
                    value: durationMinute > 0 ? '$durationMinute 分钟' : '-',
                  ),
                  _Stat(label: '错题', value: '${data?.wrongCount ?? 0}'),
                ],
              ),
            ),
          ),
          if (data != null && data.kpStats.isNotEmpty) ...[
            const SizedBox(height: 16),
            Align(
              alignment: Alignment.centerLeft,
              child: Text('知识点表现', style: theme.textTheme.titleMedium),
            ),
            const SizedBox(height: 8),
            Card(
              child: Column(
                children: [
                  for (final stat in data.kpStats)
                    ListTile(
                      dense: true,
                      title: Text(stat.name.isEmpty ? '未命名知识点' : stat.name),
                      subtitle: Text(
                        '答对 ${stat.correct}/${stat.answered} · '
                        '掌握度 ${stat.masteryScore.round()}',
                      ),
                      trailing: Text(
                        '${(stat.accuracy * 100).round()}%',
                        style: theme.textTheme.titleSmall?.copyWith(
                          color: stat.accuracy >= 0.8
                              ? Colors.green
                              : theme.colorScheme.error,
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
          if (data != null && data.nextActions.isNotEmpty) ...[
            const SizedBox(height: 16),
            Align(
              alignment: Alignment.centerLeft,
              child: Text('下一步', style: theme.textTheme.titleMedium),
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: Wrap(
                spacing: 8,
                children: [
                  for (final action in data.nextActions)
                    Chip(label: Text(_actionLabel(action))),
                ],
              ),
            ),
          ],
          const SizedBox(height: 24),
          if (actions.contains('replay'))
            FilledButton(
              onPressed: onRetry,
              child: Text(reviewMode ? '再复习一轮' : '再练一次'),
            ),
          const SizedBox(height: 8),
          if (actions.contains('wrong_book'))
            OutlinedButton(
              onPressed: onWrongBook,
              child: const Text('去错题本'),
            ),
          TextButton(
            onPressed: () => context.go('/shell'),
            child: const Text('返回主页'),
          ),
        ],
      ),
    );
  }

  String _actionLabel(String action) {
    switch (action) {
      case 'replay':
        return '再练一次';
      case 'wrong_book':
        return '去错题本';
      case 'back':
        return '返回主页';
      default:
        return action;
    }
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      children: [
        Text(
          value,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 2),
        Text(label, style: theme.textTheme.labelSmall),
      ],
    );
  }
}

class _EmptyReview extends StatelessWidget {
  const _EmptyReview({required this.onBack});

  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.celebration_outlined, size: 64, color: theme.colorScheme.primary),
            const SizedBox(height: 12),
            Text('今天没有到期的复习题', style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text('新答错的题目次日到期，坚持天天消灭错题！',
                style: theme.textTheme.bodySmall),
            const SizedBox(height: 20),
            FilledButton(onPressed: onBack, child: const Text('返回')),
          ],
        ),
      ),
    );
  }
}
