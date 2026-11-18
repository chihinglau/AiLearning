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

/// 真题库（D-09 §5）：筛选项由服务端下发、年份/地区/状态全部服务端过滤，
/// 真题不进通用考试列表与首页待办（D-04 §8.7.1 口径不变）。
class PastPaperPage extends ConsumerStatefulWidget {
  const PastPaperPage({super.key});

  @override
  ConsumerState<PastPaperPage> createState() => _PastPaperPageState();
}

class _PastPaperPageState extends ConsumerState<PastPaperPage> {
  static const _attemptFilters = {
    'all': '全部状态',
    'none': '未考',
    'in_progress': '进行中',
    'completed': '已考',
  };

  PastPaperFilters _filters = const PastPaperFilters();
  List<ExamSummary> _items = const [];
  String _subject = 'all';
  int? _year;
  String _region = 'all';
  String _attemptStatus = 'all';
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  bool get _hasFilters =>
      _subject != 'all' ||
      _year != null ||
      _region != 'all' ||
      _attemptStatus != 'all';

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final service = ref.read(examServiceProvider);
      // 筛选项独立于当前结果，避免「只看得到已加载的 60 条」截断历史年份（L23）
      final filters = await service.pastPaperFilters();
      final items = await service.pastPapers(
        subject: _subject == 'all' ? null : _subject,
        year: _year,
        region: _region == 'all' ? null : _region,
        attemptStatus: _attemptStatus == 'all' ? null : _attemptStatus,
      );
      if (!mounted) return;
      setState(() {
        _filters = filters;
        _items = items;
        if (_year != null && !filters.years.contains(_year)) _year = null;
        if (_subject != 'all' && !filters.subjects.contains(_subject)) {
          _subject = 'all';
        }
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
      _subject = 'all';
      _year = null;
      _region = 'all';
      _attemptStatus = 'all';
    });
    _load();
  }

  void _reloadWith(void Function() update) {
    setState(update);
    _load();
  }

  /// 按年份分组（数据已由服务端按 year desc 排序）
  Map<String, List<ExamSummary>> get _groups {
    final groups = <String, List<ExamSummary>>{};
    for (final paper in _items) {
      final key = paper.year == null ? '未标注年份' : '${paper.year} 年';
      groups.putIfAbsent(key, () => <ExamSummary>[]).add(paper);
    }
    return groups;
  }

  void _open(ExamSummary paper) {
    final decision = examCardDecision(paper);
    final route = decision.route;
    if (route == null && decision.message != null) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(decision.message!)));
      return;
    }
    if (route == null) return;
    context.push(route);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        leading: Navigator.of(context).canPop()
            ? null
            : IconButton(
                tooltip: '返回首页',
                icon: const Icon(Icons.home_outlined),
                onPressed: () => context.go('/shell'),
              ),
        title: const Text('真题库'),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Wrap(
              spacing: 8,
              children: [
                ChoiceChip(
                  label: const Text('全部学科'),
                  selected: _subject == 'all',
                  onSelected: (_) => _reloadWith(() => _subject = 'all'),
                ),
                for (final code in _filters.subjects)
                  ChoiceChip(
                    label: Text(_subjectLabelOf(code)),
                    selected: _subject == code,
                    onSelected: (_) => _reloadWith(() => _subject = code),
                  ),
              ],
            ),
            if (_filters.years.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  ChoiceChip(
                    label: const Text('全部年份'),
                    selected: _year == null,
                    onSelected: (_) => _reloadWith(() => _year = null),
                  ),
                  for (final year in _filters.years)
                    ChoiceChip(
                      label: Text('$year'),
                      selected: _year == year,
                      onSelected: (_) => _reloadWith(() => _year = year),
                    ),
                ],
              ),
            ],
            if (_filters.regions.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  ChoiceChip(
                    label: const Text('全部地区'),
                    selected: _region == 'all',
                    onSelected: (_) => _reloadWith(() => _region = 'all'),
                  ),
                  for (final region in _filters.regions)
                    ChoiceChip(
                      label: Text(region),
                      selected: _region == region,
                      onSelected: (_) => _reloadWith(() => _region = region),
                    ),
                ],
              ),
            ],
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: _attemptFilters.entries
                  .map(
                    (entry) => ChoiceChip(
                      label: Text(entry.value),
                      selected: _attemptStatus == entry.key,
                      onSelected: (_) =>
                          _reloadWith(() => _attemptStatus = entry.key),
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
            else if (_items.isEmpty)
              _EmptyState(filtered: _hasFilters, onClear: _clearFilters)
            else
              for (final group in _groups.entries) ...[
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    group.key,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                for (final paper in group.value) ...[
                  _PastPaperCard(
                    paper: paper,
                    onTap: () => _open(paper),
                    onDetail: () => context.push('/past-papers/${paper.id}'),
                  ),
                  const SizedBox(height: 12),
                ],
              ],
          ],
        ),
      ),
    );
  }
}

String _subjectLabelOf(String code) {
  for (final subject in Subject.values) {
    if (subject.code == code) return subject.label;
  }
  return code;
}

class _PastPaperCard extends StatelessWidget {
  const _PastPaperCard({
    required this.paper,
    required this.onTap,
    required this.onDetail,
  });

  final ExamSummary paper;
  final VoidCallback onTap;
  final VoidCallback onDetail;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final decision = examCardDecision(paper);
    final label = switch (decision.action) {
      ExamCardAction.start => '开始模考',
      ExamCardAction.resume => '继续模考',
      _ => decision.label,
    };
    final actionColor = decision.enabled
        ? theme.colorScheme.primary
        : theme.disabledColor;
    final meta = <String>[
      _subjectLabelOf(paper.subject),
      if (paper.year != null) '${paper.year} 年',
      if (paper.region != null && paper.region!.isNotEmpty) paper.region!,
    ];
    return AccentCard(
      accent: AppAccents.of(context).exam,
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  paper.title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Text(
                switch (paper.category) {
                  'in_progress' => '进行中',
                  'completed' => '已考',
                  _ => '未考',
                },
                style: theme.textTheme.labelSmall,
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(meta.join(' · '), style: theme.textTheme.bodySmall),
          const SizedBox(height: 2),
          Text(
            '${paper.questionCount} 题 · 满分 ${paper.totalScore}'
            ' · 限时 ${paper.timeLimitMin} 分钟',
            style: theme.textTheme.bodySmall,
          ),
          // L24：来源必须可见；缺来源显示「来源待补录」，不伪造、不空白
          const SizedBox(height: 2),
          Text('来源：${paper.sourceLabel}', style: theme.textTheme.bodySmall),
          if (paper.windowRange != null) ...[
            const SizedBox(height: 2),
            Text(
              '开放时间 ${paper.windowRange}'
              '${paper.windowState == 'open' ? '（开放中）' : ''}',
              style: theme.textTheme.bodySmall,
            ),
          ],
          const SizedBox(height: 6),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: onDetail,
              icon: const Icon(Icons.source_outlined, size: 16),
              label: const Text('查看来源详情'),
            ),
          ),
          Row(
            children: [
              Text(
                label,
                style: theme.textTheme.labelLarge?.copyWith(color: actionColor),
              ),
              const Spacer(),
              Icon(Icons.play_arrow_rounded, color: actionColor),
            ],
          ),
        ],
      ),
    );
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
            Icons.library_books_outlined,
            size: 56,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(height: 12),
          Text(
            filtered ? '没有符合条件的真题' : '当前年级暂未收录真题',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 4),
          Text(
            filtered ? '试试放宽筛选条件' : '可返回考试中心查看普通考试',
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
