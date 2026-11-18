import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/models/exam_action.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/theme/app_accents.dart';
import 'package:ai_learning/widgets/accent_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 考试中心（D-09 §4）：状态/类型/学科/窗口/搜索均由服务端过滤，
/// 结果集始终是 D-04 §8.7.1 学生可见性谓词的子集（L21）。
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

  static const _windowFilters = {
    'all': '全部窗口',
    'open': '开放中',
    'scheduled': '未开始',
    'closed': '已结束',
    'unscheduled': '不限时',
  };

  final _query = TextEditingController();
  List<ExamSummary> _exams = const [];
  String _filter = 'all';
  String _type = 'all';
  String? _subject;
  String _windowState = 'all';
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  bool get _hasFilters =>
      _filter != 'all' ||
      _type != 'all' ||
      _subject != null ||
      _windowState != 'all' ||
      _query.text.trim().isNotEmpty;

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final exams = await ref.read(examServiceProvider).list(
            type: _type == 'all' ? null : _type,
            status: _filter == 'all' ? null : _filter,
            subject: _subject,
            windowState: _windowState == 'all' ? null : _windowState,
            query: _query.text.trim().isEmpty ? null : _query.text.trim(),
          );
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

  void _clearFilters() {
    setState(() {
      _filter = 'all';
      _type = 'all';
      _subject = null;
      _windowState = 'all';
      _query.clear();
    });
    _load();
  }

  /// 六态唯一决策表（D-09 §4.4）：任何非可进入状态都给明确提示，禁止静默。
  void _open(ExamSummary exam) {
    final decision = examCardDecision(exam);
    final route = decision.route;
    // 窗口已关/未开但已有报告时仍可直接看报告，不显示「暂不可进入」误导提示
    if (route == null && decision.message != null) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(decision.message!)));
      return;
    }
    if (route == null) return;
    context.push(route);
  }

  List<ExamSummary> get _visible {
    const rank = {'in_progress': 0, 'available': 1, 'completed': 2};
    final sorted = [..._exams];
    sorted.sort((a, b) {
      final byCategory =
          (rank[a.category] ?? 3).compareTo(rank[b.category] ?? 3);
      return byCategory != 0 ? byCategory : b.id.compareTo(a.id);
    });
    return sorted;
  }

  void _reloadWith(void Function() update) {
    setState(update);
    _load();
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
            key: const ValueKey('open-exam-history'),
            tooltip: '报告历史',
            icon: const Icon(Icons.history_outlined),
            onPressed: () => context.push('/exams/history'),
          ),
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
                      label: Text(entry.value),
                      selected: _filter == entry.key,
                      onSelected: (_) =>
                          _reloadWith(() => _filter = entry.key),
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
                      onSelected: (_) => _reloadWith(() => _type = entry.key),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                FilterChip(
                  label: const Text('全部学科'),
                  selected: _subject == null,
                  onSelected: (_) => _reloadWith(() => _subject = null),
                ),
                for (final subject in Subject.values)
                  FilterChip(
                    label: Text(subject.label),
                    selected: _subject == subject.code,
                    onSelected: (_) => _reloadWith(
                      () => _subject = _subject == subject.code
                          ? null
                          : subject.code,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: _windowFilters.entries
                  .map(
                    (entry) => ChoiceChip(
                      label: Text(entry.value),
                      selected: _windowState == entry.key,
                      onSelected: (_) =>
                          _reloadWith(() => _windowState = entry.key),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _query,
              textInputAction: TextInputAction.search,
              onChanged: (_) => setState(() {}),
              onSubmitted: (_) => _load(),
              decoration: InputDecoration(
                hintText: '搜索试卷标题',
                prefixIcon: const Icon(Icons.search_outlined),
                border: const OutlineInputBorder(),
                suffixIcon: _query.text.isEmpty
                    ? null
                    : IconButton(
                        tooltip: '清除搜索',
                        icon: const Icon(Icons.clear),
                        onPressed: () => _reloadWith(_query.clear),
                      ),
              ),
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
              _EmptyState(filtered: _hasFilters, onClear: _clearFilters)
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
    final decision = examCardDecision(exam);
    final isDone = exam.category == 'completed';
    final isDoing = exam.category == 'in_progress';
    final actionColor = decision.enabled
        ? theme.colorScheme.primary
        : theme.disabledColor;
    final accents = AppAccents.of(context);
    final statusColor = isDone ? accents.learn : accents.exam;

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
                  isDone
                      ? '已完成'
                      : isDoing
                      ? '进行中'
                      : exam.windowState == 'scheduled'
                      ? '未开始'
                      : exam.windowState == 'closed'
                      ? '已结束'
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
          if (exam.isPastPaper || exam.sourceName != null) ...[
            const SizedBox(height: 2),
            Text('来源：${exam.sourceLabel}', style: theme.textTheme.bodySmall),
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
          if (exam.attemptCount > 1) ...[
            const SizedBox(height: 2),
            Text('共 ${exam.attemptCount} 次作答', style: theme.textTheme.bodySmall),
          ],
          const SizedBox(height: 10),
          Row(
            children: [
              Text(
                decision.label,
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
  const _EmptyState({required this.filtered, required this.onClear});

  final bool filtered;
  final VoidCallback onClear;

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
            filtered ? '没有符合条件的考试' : '暂时没有可参加的考试',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 4),
          Text(
            filtered
                ? '试试放宽筛选条件'
                : '完成教材学习后，老师会为你安排单元测与期中期末。',
            style: theme.textTheme.bodySmall,
          ),
          if (filtered) ...[
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onClear, child: const Text('清除筛选')),
          ],
        ],
      ),
    );
  }
}
