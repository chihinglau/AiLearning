import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/theme/app_accents.dart';
import 'package:ai_learning/widgets/accent_card.dart';
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

  static const _typeFilters = {
    'all': '全部类型',
    'unit': '单元测',
    'midterm': '期中',
    'final': '期末',
    'mock': '模考',
  };

  List<ExamSummary> _exams = const [];
  String _filter = 'all';
  String _type = 'all';
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
    return _exams.where((exam) {
      if (_filter != 'all' && exam.category != _filter) return false;
      if (_type != 'all' && exam.examType != _type) return false;
      return true;
    }).toList();
  }

  int _countOf(String category) {
    if (category == 'all') return _exams.length;
    return _exams.where((exam) => exam.category == category).length;
  }

  void _open(ExamSummary exam) {
    if (exam.category != 'completed' && !exam.windowOpen) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('${exam.windowLabel}，暂不可进入考试')));
      return;
    }
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
        actions: [
          IconButton(
            key: const ValueKey('open-past-papers'),
            tooltip: '真题库',
            icon: const Icon(Icons.library_books_outlined),
            onPressed: () => context.push('/past-papers'),
          ),
        ],
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
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: _typeFilters.entries
                  .map(
                    (entry) => FilterChip(
                      label: Text(entry.value),
                      selected: _type == entry.key,
                      onSelected: (_) => setState(() => _type = entry.key),
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
    final blocked = !isDone && !exam.windowOpen;
    final actionLabel = isDone
        ? '查看报告'
        : blocked
        ? exam.windowLabel
        : isDoing
        ? '继续考试'
        : '开始考试';
    final actionColor = blocked
        ? theme.disabledColor
        : theme.colorScheme.primary;
    final accents = AppAccents.of(context);
    final statusColor = switch (exam.category) {
      'completed' => accents.learn,
      'in_progress' => accents.exam,
      _ => accents.exam,
    };

    return AccentCard(
      accent: isDone ? accents.learn : accents.exam,
      onTap: onTap,
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
                  border: Border.all(color: statusColor.withValues(alpha: 0.4)),
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
          Text('限时 ${exam.timeLimitMin} 分钟', style: theme.textTheme.bodySmall),
          if (exam.windowRange != null) ...[
            const SizedBox(height: 2),
            Text(
              '考试窗口 ${exam.windowRange}'
              '${exam.windowState == 'open' ? '（开放中）' : ''}',
              style: theme.textTheme.bodySmall,
            ),
          ],
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
                style: theme.textTheme.labelLarge?.copyWith(color: actionColor),
              ),
              const Spacer(),
              Icon(
                isDone ? Icons.chevron_right : Icons.play_arrow_rounded,
                color: actionColor,
              ),
            ],
          ),
        ],
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
          Text('完成教材学习后，老师会为你安排单元测与期中期末。', style: theme.textTheme.bodySmall),
        ],
      ),
    );
  }
}
