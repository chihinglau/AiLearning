import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/assignment.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/theme/app_accents.dart';
import 'package:ai_learning/widgets/accent_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 班级作业：学生查看待做/已完成作业，教师查看布置与批改进度。
class AssignmentListPage extends ConsumerStatefulWidget {
  const AssignmentListPage({super.key});

  @override
  ConsumerState<AssignmentListPage> createState() => _AssignmentListPageState();
}

class _AssignmentListPageState extends ConsumerState<AssignmentListPage> {
  List<AssignmentInfo> _items = const [];
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
      final items = await ref.read(assignmentServiceProvider).list();
      if (!mounted) return;
      setState(() {
        _items = items;
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

  Future<void> _create() async {
    await context.push('/assignments/create');
    if (!mounted) return;
    _load();
  }

  void _open(AssignmentInfo item) {
    final user = ref.read(currentUserProvider);
    if (user?.hasPermission('learn:assignment:create') == true &&
        item.myStatus == null) {
      context.push('/assignments/${item.id}');
      return;
    }
    switch (item.myStatus) {
      case 'in_progress':
        context.push('/exam/${item.examId}');
      case 'grading':
      case 'completed':
        final attemptId = item.myAttemptId;
        if (attemptId != null) {
          context.push('/exam/report/$attemptId');
        }
      default:
        context.push('/exam/${item.examId}');
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final user = ref.watch(currentUserProvider);
    final teacherView =
        user?.hasPermission('learn:assignment:create') == true &&
        user?.isStudent == false;
    return Scaffold(
      appBar: AppBar(
        leading: Navigator.of(context).canPop()
            ? null
            : IconButton(
                tooltip: '返回首页',
                icon: const Icon(Icons.home_outlined),
                onPressed: () => context.go('/shell'),
              ),
        title: const Text('班级作业'),
      ),
      floatingActionButton: teacherView
          ? FloatingActionButton.extended(
              key: const ValueKey('create-assignment-fab'),
              onPressed: _create,
              icon: const Icon(Icons.add),
              label: const Text('布置作业'),
            )
          : null,
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (_loading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 48),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
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
            else if (_items.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 48),
                child: Column(
                  children: [
                    Icon(
                      Icons.assignment_outlined,
                      size: 56,
                      color: theme.colorScheme.primary,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      teacherView ? '还没有布置过作业' : '暂时没有班级作业',
                      style: theme.textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      teacherView ? '点击右下角「布置作业」为班级统一组卷。' : '老师布置作业后会显示在这里。',
                      style: theme.textTheme.bodySmall,
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              )
            else
              for (final item in _items) ...[
                _AssignmentCard(
                  item: item,
                  teacherView: teacherView,
                  onTap: () => _open(item),
                ),
                const SizedBox(height: 12),
              ],
          ],
        ),
      ),
    );
  }
}

class _AssignmentCard extends StatelessWidget {
  const _AssignmentCard({
    required this.item,
    required this.teacherView,
    required this.onTap,
  });

  final AssignmentInfo item;
  final bool teacherView;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accents = AppAccents.of(context);
    final accent = item.completed
        ? accents.learn
        : item.grading
        ? accents.exam
        : accents.assignment;
    final progress = item.studentCount == 0
        ? '0%'
        : '${(item.submittedCount * 100 / item.studentCount).round()}%';
    return AccentCard(
      key: ValueKey('assignment-card-${item.id}'),
      accent: accent,
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  item.title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: accent.withValues(alpha: 0.4)),
                ),
                child: Text(
                  teacherView
                      ? (item.pendingGrading > 0
                            ? '待批改 ${item.pendingGrading}'
                            : '已批改')
                      : item.myStatusLabel,
                  style: TextStyle(color: accent, fontSize: 12),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            '${item.subjectLabel} · ${item.className}'
            '${item.dueLabel == null ? '' : ' · 截止 ${item.dueLabel}'}',
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: 6),
          if (teacherView)
            Text(
              '提交 ${item.submittedCount}/${item.studentCount} · 完成率 $progress',
              style: theme.textTheme.bodySmall,
            )
          else
            Text(
              item.completed || item.grading
                  ? '得分 ${item.myTotalScore == null ? '待批改' : item.myTotalScore!.round()}'
                  : '满分待定 · 点击进入作答',
              style: theme.textTheme.bodySmall,
            ),
          const SizedBox(height: 10),
          Row(
            children: [
              Text(
                teacherView
                    ? (item.pendingGrading > 0 ? '去批改' : '查看详情')
                    : (item.completed
                          ? '查看报告'
                          : item.grading
                          ? '查看作答'
                          : '进入作业'),
                style: theme.textTheme.labelLarge?.copyWith(color: accent),
              ),
              const Spacer(),
              Icon(Icons.chevron_right, color: accent),
            ],
          ),
        ],
      ),
    );
  }
}
