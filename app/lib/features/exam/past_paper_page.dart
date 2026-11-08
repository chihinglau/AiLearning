import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/theme/app_accents.dart';
import 'package:ai_learning/widgets/accent_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// P2-07 真题库：按学科/年份浏览历年真题与模考卷，窗口内可直接开考。
class PastPaperPage extends ConsumerStatefulWidget {
  const PastPaperPage({super.key});

  @override
  ConsumerState<PastPaperPage> createState() => _PastPaperPageState();
}

class _PastPaperPageState extends ConsumerState<PastPaperPage> {
  static const _subjects = {
    'all': '全部学科',
    'chinese': '语文',
    'math': '数学',
    'english': '英语',
  };

  List<ExamSummary> _items = const [];
  String _subject = 'all';
  int? _year;
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
      final items = await ref
          .read(examServiceProvider)
          .pastPapers(subject: _subject == 'all' ? null : _subject);
      if (!mounted) return;
      setState(() {
        _items = items;
        if (_year != null && !items.any((item) => item.year == _year)) {
          _year = null;
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

  List<int> get _years {
    final years = <int>{};
    for (final item in _items) {
      if (item.year != null) years.add(item.year!);
    }
    return years.toList()..sort((a, b) => b.compareTo(a));
  }

  List<ExamSummary> get _visible {
    if (_year == null) return _items;
    return _items.where((item) => item.year == _year).toList();
  }

  void _start(ExamSummary paper) {
    if (!paper.windowOpen) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('${paper.windowLabel}，暂不可进入真题')));
      return;
    }
    context.push('/exam/${paper.id}');
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
              children: _subjects.entries
                  .map(
                    (entry) => ChoiceChip(
                      label: Text(entry.value),
                      selected: _subject == entry.key,
                      onSelected: (_) {
                        if (_subject == entry.key) return;
                        setState(() => _subject = entry.key);
                        _load();
                      },
                    ),
                  )
                  .toList(),
            ),
            if (!_loading && _years.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  ChoiceChip(
                    label: const Text('全部年份'),
                    selected: _year == null,
                    onSelected: (_) => setState(() => _year = null),
                  ),
                  for (final year in _years)
                    ChoiceChip(
                      label: Text('$year'),
                      selected: _year == year,
                      onSelected: (_) => setState(() => _year = year),
                    ),
                ],
              ),
            ],
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
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 48),
                child: Column(
                  children: [
                    Icon(
                      Icons.library_books_outlined,
                      size: 56,
                      color: theme.colorScheme.primary,
                    ),
                    const SizedBox(height: 12),
                    Text('暂无匹配的真题', style: theme.textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Text('切换学科或年份试试', style: theme.textTheme.bodySmall),
                  ],
                ),
              )
            else
              for (final paper in _visible) ...[
                _PastPaperCard(paper: paper, onTap: () => _start(paper)),
                const SizedBox(height: 12),
              ],
          ],
        ),
      ),
    );
  }
}

class _PastPaperCard extends StatelessWidget {
  const _PastPaperCard({required this.paper, required this.onTap});

  static const _subjectLabels = {
    'chinese': '语文',
    'math': '数学',
    'english': '英语',
  };

  final ExamSummary paper;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final blocked = !paper.windowOpen;
    final meta = <String>[
      _subjectLabels[paper.subject] ?? paper.subject,
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
          Text(
            paper.title,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          Text(meta.join(' · '), style: theme.textTheme.bodySmall),
          const SizedBox(height: 2),
          Text(
            '${paper.questionCount} 题 · 满分 ${paper.totalScore}'
            ' · 限时 ${paper.timeLimitMin} 分钟',
            style: theme.textTheme.bodySmall,
          ),
          if (paper.windowRange != null) ...[
            const SizedBox(height: 2),
            Text(
              '开放时间 ${paper.windowRange}'
              '${paper.windowState == 'open' ? '（开放中）' : ''}',
              style: theme.textTheme.bodySmall,
            ),
          ],
          const SizedBox(height: 10),
          Row(
            children: [
              Text(
                blocked ? paper.windowLabel : '开始模考',
                style: theme.textTheme.labelLarge?.copyWith(
                  color: blocked
                      ? theme.disabledColor
                      : theme.colorScheme.primary,
                ),
              ),
              const Spacer(),
              Icon(
                Icons.play_arrow_rounded,
                color: blocked
                    ? theme.disabledColor
                    : theme.colorScheme.primary,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
