import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/assignment.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 作业详情：教师查看班级提交与得分，学生查看自己的作答状态。
class AssignmentDetailPage extends ConsumerStatefulWidget {
  const AssignmentDetailPage({super.key, required this.assignmentId});

  final int assignmentId;

  @override
  ConsumerState<AssignmentDetailPage> createState() => _AssignmentDetailPageState();
}

class _AssignmentDetailPageState extends ConsumerState<AssignmentDetailPage> {
  AssignmentInfo? _item;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final item = await ref
          .read(assignmentServiceProvider)
          .detail(widget.assignmentId);
      if (!mounted) return;
      setState(() {
        _item = item;
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

  Future<void> _openGrading() async {
    await context.push('/assignments/${widget.assignmentId}/grading');
    if (!mounted) return;
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final user = ref.watch(currentUserProvider);
    final canGrade = user?.hasPermission('learn:exam:grade') == true &&
        user?.isStudent == false;
    final item = _item;
    return Scaffold(
      appBar: AppBar(title: const Text('作业详情')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Card(
                  margin: const EdgeInsets.all(16),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          _error!,
                          style: TextStyle(color: theme.colorScheme.error),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 12),
                        FilledButton(onPressed: _load, child: const Text('重试')),
                      ],
                    ),
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    if (item != null) ...[
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                item.title,
                                style: theme.textTheme.titleLarge
                                    ?.copyWith(fontWeight: FontWeight.w600),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                '${item.subjectLabel} · ${item.className}'
                                '${item.dueLabel == null ? '' : ' · 截止 ${item.dueLabel}'}',
                                style: theme.textTheme.bodySmall,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '提交 ${item.submittedCount}/${item.studentCount}'
                                ' · 待批改 ${item.pendingGrading}',
                                style: theme.textTheme.bodySmall,
                              ),
                              if (item.myStatus != null) ...[
                                const SizedBox(height: 4),
                                Text(
                                  '我的状态：${item.myStatusLabel}'
                                  '${item.myTotalScore == null ? '' : ' · 得分 ${item.myTotalScore!.round()}'}',
                                  style: theme.textTheme.bodySmall,
                                ),
                              ],
                              if (canGrade) ...[
                                const SizedBox(height: 16),
                                FilledButton.icon(
                                  key: const ValueKey('open-grading'),
                                  onPressed: _openGrading,
                                  icon: const Icon(Icons.rate_review_outlined),
                                  label: Text(
                                    item.pendingGrading > 0
                                        ? '批改主观题（${item.pendingGrading} 人待批）'
                                        : '查看批改清单',
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      if (item.students.isNotEmpty) ...[
                        Text('学生完成情况', style: theme.textTheme.titleMedium),
                        const SizedBox(height: 8),
                        for (final student in item.students)
                          Card(
                            child: ListTile(
                              leading: CircleAvatar(
                                child: Text(
                                  (student.nickname ?? '?').substring(0, 1),
                                ),
                              ),
                              title: Text(student.nickname ?? '学生 ${student.studentId}'),
                              subtitle: Text(
                                student.totalScore == null
                                    ? student.statusLabel
                                    : '${student.statusLabel} · 得分 ${student.totalScore!.round()}',
                              ),
                              trailing: Text(student.statusLabel),
                            ),
                          ),
                        const SizedBox(height: 8),
                      ],
                    ],
                  ],
                ),
    );
  }
}
