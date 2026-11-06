import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 考试中心：待考 / 进行中 / 已完成，支持开始、继续与查看报告。
class ExamListPage extends ConsumerStatefulWidget {
  const ExamListPage({super.key});

  @override
  ConsumerState<ExamListPage> createState() => _ExamListPageState();
}

class _ExamListPageState extends ConsumerState<ExamListPage> {
  static const _filters = {
    'all': '全部',
    'available': '待考',
    'in_progress': '进行中',
    'completed': '已完成',
  };

  List<ExamSummary> _exams = const [];
  String _filter = 'all';
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
      final exams = await ref.read(examServiceProvider).list();
      if (!mounted) return;
      setState(() {
        _exams = exams;
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

  List<ExamSummary> get _visible {
    if (_filter == 'all') return _exams;
    return _exams.where((exam) => exam.category == _filter).toList();
  }

  int _countOf(String category) {
    if (category == 'all') return _exams.length;
    return _exams.where((exam) => exam.category == category).length;
  }

  void _open(ExamSummary exam) {
    switch (exam.category) {
      case 'available':
      case 'in_progress':
        context.push('/exam/${exam.id}');
      case 'completed':
        final attempt = exam.attempt;
        if (attempt != null) {
          context.push('/exam/report/${attempt.id}');
        }
      default:
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        leading: context.canPop()
            ? null
            : IconButton(
                tooltip: '返回首页',
                icon: const Icon(Icons.home_outlined),
                onPressed: () => context.go('/shell'),
              ),
        title: const Text('考试中心'),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Wrap(
              spacing: 8,
              children: _filters.entries
                  .map(
                    (entry) => ChoiceChip(
                      label: Text('${entry.value} ${_countOf(entry.key)}'),
                      selected: _filter == entry.key,
                      onSelected: (_) => setState(() => _filter = entry.key),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 16),
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
            else if (_visible.isEmpty)
              _EmptyState(filter: _filter)
            else
              for (final exam in _visible) ...[
                _ExamCard(exam: exam, onTap: () => _open(exam)),
                const SizedBox(height: 12),
              ],
          ],
        ),
      ),
    );
  }
}

class _ExamCard extends StatelessWidget {
  const _ExamCard({required this.exam, required this.onTap});

  final ExamSummary exam;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final attempt = exam.attempt;
    final isDone = exam.category == 'completed';
    final isDoing = exam.category == 'in_progress';
    final actionLabel = isDone
        ? '查看报告'
        : isDoing
            ? '继续考试'
            : '开始考试';
    final statusColor = switch (exam.category) {
      'completed' => Colors.green.shade700,
      'in_progress' => Colors.orange.shade700,
      _ => theme.colorScheme.primary,
    };

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      exam.title,
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
                      color: statusColor.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: statusColor.withValues(alpha: 0.4),
                      ),
                    ),
                    child: Text(
                      exam.category == 'completed'
                          ? '已完成'
                          : exam.category == 'in_progress'
                              ? '进行中'
                              : '待考',
                      style: TextStyle(color: statusColor, fontSize: 12),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                '${exam.typeLabel} · ${Subject.fromCode(exam.subject).label}'
                '${exam.year == null ? '' : ' · ${exam.year} 学年'}'
                ' · ${exam.questionCount} 题 · 满分 ${exam.totalScore}',
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: 2),
              Text(
                '限时 ${exam.timeLimitMin} 分钟',
                style: theme.textTheme.bodySmall,
              ),
              if (attempt != null) ...[
                const SizedBox(height: 8),
                Text(
                  isDoing
                      ? '剩余 ${_durationLabel(attempt.remainingSeconds)}，点击继续作答'
                      : '得分 ${_scoreLabel(attempt)} / ${exam.totalScore}'
                          '${attempt.status == 'grading' ? ' · 待批改' : ''}',
                  style: theme.textTheme.bodySmall,
                ),
              ],
              const SizedBox(height: 10),
              Row(
                children: [
                  Text(
                    actionLabel,
                    style: theme.textTheme.labelLarge?.copyWith(
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  const Spacer(),
                  Icon(
                    isDone ? Icons.chevron_right : Icons.play_arrow_rounded,
                    color: theme.colorScheme.primary,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  static String _durationLabel(int seconds) {
    final minute = (seconds / 60).ceil();
    return '$minute 分钟';
  }

  static String _scoreLabel(ExamAttemptBrief attempt) {
    final total = attempt.totalScore;
    if (total == null) return '待批改';
    return total.round().toString();
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.filter});

  final String filter;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
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
            filter == 'all' ? '暂时没有可参加的考试' : '该分类下暂无考试',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 4),
          Text('完成教材学习后，老师会为你安排单元测与期中期末。',
              style: theme.textTheme.bodySmall),
        ],
      ),
    );
  }
}
