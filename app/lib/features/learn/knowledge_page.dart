import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/features/learn/mastery_ring.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 教材单元目录（D-04 §6.2）：单元 → 节 → 知识点逐层下钻。
class KnowledgePage extends ConsumerStatefulWidget {
  const KnowledgePage({
    super.key,
    required this.textbookId,
    required this.textbookName,
    this.initialChapterId,
  });

  final int textbookId;
  final String textbookName;
  final int? initialChapterId;

  @override
  ConsumerState<KnowledgePage> createState() => _KnowledgePageState();
}

class _KnowledgePageState extends ConsumerState<KnowledgePage> {
  List<UnitSummary> _units = const [];
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
      final units =
          await ref.read(learnServiceProvider).units(widget.textbookId);
      if (!mounted) return;
      setState(() {
        _units = units;
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

  void _openUnit(UnitSummary unit) {
    context.go(
      '/unit/${unit.id}'
      '?name=${Uri.encodeComponent(unit.name)}'
      '&textbook=${Uri.encodeComponent(widget.textbookName)}'
      '&tid=${widget.textbookId}',
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.textbookName),
        actions: [
          IconButton(
            key: const ValueKey('open-knowledge-graph'),
            tooltip: '知识图谱',
            icon: const Icon(Icons.account_tree_outlined),
            onPressed: () => context.push(
              '/knowledge/${widget.textbookId}/graph'
              '?name=${Uri.encodeComponent(widget.textbookName)}',
            ),
          ),
        ],
      ),
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
            Text(_error!),
            const SizedBox(height: 12),
            FilledButton(onPressed: _load, child: const Text('重试')),
          ],
        ),
      );
    }
    if (_units.isEmpty) {
      return const Center(child: Text('该教材暂无单元内容'));
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('单元掌握度', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(
            '薄弱 → 巩固 → 熟练 → 精通，点击单元查看节与知识点',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 12),
          for (final unit in _units) ...[
            _UnitCard(
              unit: unit,
              highlighted: unit.id == widget.initialChapterId,
              onTap: () => _openUnit(unit),
            ),
            const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }
}

class _UnitCard extends StatelessWidget {
  const _UnitCard({
    required this.unit,
    required this.highlighted,
    required this.onTap,
  });

  final UnitSummary unit;
  final bool highlighted;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final visited = unit.learnedKpCount > 0;
    return Card(
      color: highlighted ? theme.colorScheme.primaryContainer : null,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              MasteryRing(score: unit.avgMastery, color: unit.bandColor),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            unit.name,
                            style: theme.textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        _BandTag(
                          label: visited ? unit.bandLabelText : '未学习',
                          color: visited ? unit.bandColor : theme.colorScheme.outline,
                        ),
                      ],
                    ),
                    if (unit.summary != null && unit.summary!.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        unit.summary!,
                        style: theme.textTheme.bodySmall,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    const SizedBox(height: 6),
                    Text(
                      '${unit.sectionCount} 节 · ${unit.kpCount} 知识点 · '
                      '${unit.questionCount} 道题',
                      style: theme.textTheme.bodySmall,
                    ),
                    const SizedBox(height: 6),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: unit.progress.clamp(0, 1),
                        minHeight: 5,
                        backgroundColor:
                            theme.colorScheme.surfaceContainerHighest,
                        color: unit.bandColor,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(unit.progressText, style: theme.textTheme.labelSmall),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, color: theme.colorScheme.outline),
            ],
          ),
        ),
      ),
    );
  }
}

class _BandTag extends StatelessWidget {
  const _BandTag({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(color: color),
      ),
    );
  }
}
