import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 自适应练习 / 错题复习的通用答题页。
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
  });

  final String title;
  final int? knowledgePointId;
  final int? chapterId;
  final String? subject;
  final bool reviewMode;

  @override
  ConsumerState<SessionPage> createState() => _SessionPageState();
}

class _SessionPageState extends ConsumerState<SessionPage> {
  final _fillController = TextEditingController();

  List<Question> _questions = const [];
  int _index = 0;
  int _correctCount = 0;
  String? _selectedKey;
  final Set<String> _selectedKeys = {};
  LearnSubmitResult? _result;
  bool _loading = true;
  bool _submitting = false;
  bool _finished = false;
  String? _error;
  DateTime _startedAt = DateTime.now();

  Question? get _current => _index < _questions.length ? _questions[_index] : null;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _fillController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _finished = false;
      _index = 0;
      _correctCount = 0;
    });
    try {
      final service = ref.read(learnServiceProvider);
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
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
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
          );
      if (!mounted) return;
      setState(() {
        _result = result;
        if (result.isCorrect) _correctCount += 1;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  void _next() {
    if (_index + 1 >= _questions.length) {
      setState(() => _finished = true);
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
        total: _questions.length,
        correct: _correctCount,
        reviewMode: widget.reviewMode,
        onRetry: _load,
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
            _FeedbackCard(result: _result!, question: question, onNext: _next,
                isLast: _index + 1 >= _questions.length),
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
              child: Text('（多选题，可选多个答案）',
                  style: Theme.of(context).textTheme.bodySmall),
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
                  onTap: locked ? null : () => setState(() => _selectedKey = option.key),
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
                Icon(result.isCorrect ? Icons.check_circle : Icons.cancel, color: correctColor),
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
                style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
            ],
            if (!result.isCorrect && result.inWrongBook) ...[
              const SizedBox(height: 4),
              Row(
                children: [
                  Icon(Icons.bookmark_added, size: 16, color: theme.colorScheme.error),
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
    required this.onRetry,
  });

  final String title;
  final int total;
  final int correct;
  final bool reviewMode;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final rate = total == 0 ? 0 : (correct * 100 / total).round();
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.emoji_events_outlined, size: 72, color: theme.colorScheme.primary),
            const SizedBox(height: 16),
            Text(
              reviewMode ? '今日复习完成' : '本次练习完成',
              style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(title),
            const SizedBox(height: 4),
            Text('答对 $correct / $total 题，正确率 $rate%'),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () => context.go('/shell'),
              child: const Text('返回主页'),
            ),
            TextButton(
              onPressed: onRetry,
              child: Text(reviewMode ? '再复习一轮' : '再练一次'),
            ),
          ],
        ),
      ),
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
