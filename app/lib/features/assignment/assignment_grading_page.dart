import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/assignment.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 教师批改主观题：逐份作答给分与写评语，提交后重算作业总分。
class AssignmentGradingPage extends ConsumerStatefulWidget {
  const AssignmentGradingPage({super.key, required this.assignmentId});

  final int assignmentId;

  @override
  ConsumerState<AssignmentGradingPage> createState() =>
      _AssignmentGradingPageState();
}

class _AssignmentGradingPageState extends ConsumerState<AssignmentGradingPage> {
  GradingList? _list;
  final Map<String, TextEditingController> _scoreControllers = {};
  final Map<String, TextEditingController> _commentControllers = {};
  bool _loading = true;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final controller in _scoreControllers.values) {
      controller.dispose();
    }
    for (final controller in _commentControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  String _key(GradingItem item) => '${item.attemptId}-${item.questionId}';

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final list = await ref
          .read(assignmentServiceProvider)
          .grading(widget.assignmentId);
      if (!mounted) return;
      _scoreControllers.clear();
      _commentControllers.clear();
      for (final item in list.items) {
        _scoreControllers[_key(item)] = TextEditingController(
          text: item.currentScore == null ? '' : '${item.currentScore!.round()}',
        );
        _commentControllers[_key(item)] = TextEditingController(
          text: item.comment ?? '',
        );
      }
      setState(() {
        _list = list;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loading = false;
      });
    }
  }

  Future<void> _submit() async {
    final list = _list;
    if (list == null || list.items.isEmpty) return;
    final payload = <Map<String, dynamic>>[];
    for (final item in list.items) {
      final key = _key(item);
      final raw = _scoreControllers[key]?.text.trim() ?? '';
      final score = double.tryParse(raw);
      if (score == null) {
        _showMessage('请为 ${item.studentName ?? '学生'} 的题目填写分数');
        return;
      }
      if (score < 0 || score > item.maxScore) {
        _showMessage('分数需在 0~${item.maxScore.round()} 之间');
        return;
      }
      final comment = _commentControllers[key]?.text.trim();
      payload.add({
        'attempt_id': item.attemptId,
        'question_id': item.questionId,
        'score': score,
        if (comment != null && comment.isNotEmpty) 'comment': comment,
      });
    }
    setState(() => _submitting = true);
    try {
      final result = await ref
          .read(assignmentServiceProvider)
          .grade(widget.assignmentId, payload);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '已批改 ${result.graded} 题，完成 ${result.completedAttempts} 人，'
            '待批改 ${result.pendingAttempts} 人',
          ),
        ),
      );
      await _load();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = ApiErrorGuide.from(error).message;
      });
    }
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final list = _list;
    return Scaffold(
      appBar: AppBar(title: const Text('批改主观题')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_error != null)
                  Card(
                    color: theme.colorScheme.errorContainer,
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(_error!, style: theme.textTheme.bodySmall),
                    ),
                  ),
                if (list == null || list.items.isEmpty)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 48),
                    child: Column(
                      children: [
                        const Icon(Icons.task_alt, size: 56),
                        const SizedBox(height: 12),
                        Text('暂无需批改的主观题', style: theme.textTheme.titleMedium),
                      ],
                    ),
                  )
                else ...[
                  Text(
                    '共 ${list.items.length} 份主观题作答待处理',
                    style: theme.textTheme.bodySmall,
                  ),
                  const SizedBox(height: 8),
                  for (final item in list.items) ...[
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    '${item.studentName ?? '学生 ${item.studentId}'} · 第 ${item.questionId} 题',
                                    style: theme.textTheme.titleSmall,
                                  ),
                                ),
                                Text(
                                  '满分 ${item.maxScore.round()}',
                                  style: theme.textTheme.bodySmall,
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(item.stem, style: theme.textTheme.bodyMedium),
                            const SizedBox(height: 12),
                            _LabeledLine(
                              label: '学生作答',
                              value: item.userAnswer ?? '（未作答）',
                            ),
                            _LabeledLine(
                              label: '参考答案',
                              value: item.reference.isEmpty ? '—' : item.reference,
                            ),
                            if (item.analysis != null && item.analysis!.isNotEmpty)
                              _LabeledLine(label: '解析', value: item.analysis!),
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                SizedBox(
                                  width: 96,
                                  child: TextField(
                                    key: ValueKey('score-${_key(item)}'),
                                    controller: _scoreControllers[_key(item)],
                                    keyboardType: const TextInputType.numberWithOptions(
                                      decimal: true,
                                    ),
                                    inputFormatters: [
                                      FilteringTextInputFormatter.allow(
                                        RegExp(r'[0-9.]'),
                                      ),
                                    ],
                                    decoration: const InputDecoration(
                                      labelText: '得分',
                                      border: OutlineInputBorder(),
                                      isDense: true,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: TextField(
                                    controller: _commentControllers[_key(item)],
                                    maxLength: 500,
                                    decoration: const InputDecoration(
                                      labelText: '评语（选填）',
                                      border: OutlineInputBorder(),
                                      isDense: true,
                                      counterText: '',
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                  ],
                  FilledButton.icon(
                    key: const ValueKey('submit-grading'),
                    onPressed: _submitting ? null : _submit,
                    icon: const Icon(Icons.done_all),
                    label: Text(_submitting ? '提交中…' : '提交批改'),
                  ),
                ],
              ],
            ),
    );
  }
}

class _LabeledLine extends StatelessWidget {
  const _LabeledLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: RichText(
        text: TextSpan(
          style: theme.textTheme.bodySmall,
          children: [
            TextSpan(
              text: '$label：',
              style: TextStyle(
                color: theme.colorScheme.primary,
                fontWeight: FontWeight.w600,
              ),
            ),
            TextSpan(text: value),
          ],
        ),
      ),
    );
  }
}
