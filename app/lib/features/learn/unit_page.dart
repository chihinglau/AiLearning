import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/theme/app_accents.dart';
import 'package:ai_learning/features/learn/mastery_ring.dart';
import 'package:ai_learning/features/learn/widgets/offline_banner.dart';
import 'package:ai_learning/widgets/accent_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 单元详情（D-04 §6.3）：节 → 知识点，展示掌握度、学习状态与练习入口。
class UnitPage extends ConsumerStatefulWidget {
  const UnitPage({
    super.key,
    required this.chapterId,
    required this.unitName,
    required this.textbookName,
    this.textbookId,
  });

  final int chapterId;
  final String unitName;
  final String textbookName;
  final int? textbookId;

  @override
  ConsumerState<UnitPage> createState() => _UnitPageState();
}

class _UnitPageState extends ConsumerState<UnitPage> {
  UnitDetail? _detail;
  bool _loading = true;
  bool _offline = false;
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
      final detail = await ref
          .read(learnServiceProvider)
          .unitDetail(widget.chapterId);
      if (!mounted) return;
      setState(() {
        _detail = detail;
        _offline = false;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      final local = error.statusCode == null
          ? await ref
                .read(offlineLearnServiceProvider)
                .unitDetail(widget.chapterId)
          : null;
      if (!mounted) return;
      setState(() {
        if (local != null) {
          _detail = local;
          _offline = true;
          _error = null;
        } else {
          _error = ApiErrorGuide.from(error).message;
        }
        _loading = false;
      });
    }
  }

  void _openKp(KnowledgeNode node) {
    context.push('/kp/${node.id}');
  }

  void _practiceNode(KnowledgeNode node) {
    context.push(
      '/practice/config?scope=kp&ids=${node.id}'
      '&chapter=${widget.chapterId}'
      '${widget.textbookId == null ? '' : '&textbook=${widget.textbookId}'}'
      '&title=${Uri.encodeComponent(node.displayName)}',
    );
  }

  void _practiceUnit() {
    context.push(
      '/practice/config?scope=chapter&ids=${widget.chapterId}'
      '${widget.textbookId == null ? '' : '&textbook=${widget.textbookId}'}'
      '&title=${Uri.encodeComponent('${widget.unitName} · 综合练习')}',
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.unitName)),
      body: _buildBody(context),
    );
  }

  Widget _buildBody(BuildContext context) {
    final theme = Theme.of(context);
    if (_loading) return const Center(child: CircularProgressIndicator());
    final detail = _detail;
    if (_error != null || detail == null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error ?? '单元加载失败'),
            const SizedBox(height: 12),
            FilledButton(onPressed: _load, child: const Text('重试')),
          ],
        ),
      );
    }
    final unit = detail.unit;
    final loose = detail.nodesOfSection(null);
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_offline) const OfflineBanner(),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  MasteryRing(
                    score: unit.avgMastery,
                    color: unit.bandColor,
                    size: 56,
                    strokeWidth: 6,
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.textbookName,
                          style: theme.textTheme.labelSmall,
                        ),
                        const SizedBox(height: 2),
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
                        Text(
                          '${unit.progressText} · ${unit.bandLabelText}',
                          style: theme.textTheme.labelSmall,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: _practiceUnit,
            icon: const Icon(Icons.edit_note),
            label: const Text('单元综合练习'),
          ),
          const SizedBox(height: 20),
          if (detail.sections.isEmpty && loose.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text('本单元内容准备中，教研内容正在补充中。'),
              ),
            ),
          for (final section in detail.sections) ...[
            _SectionCard(
              section: section,
              nodes: detail.visibleNodesOfSection(section),
              folded: detail.foldedNodeOfSection(section),
              onOpen: _openKp,
              onPractice: _practiceNode,
            ),
            const SizedBox(height: 8),
          ],
          if (loose.isNotEmpty) ...[
            Text('其他知识点', style: theme.textTheme.titleSmall),
            const SizedBox(height: 8),
            ..._nodesBlock(detail, null),
          ],
        ],
      ),
    );
  }

  List<Widget> _nodesBlock(UnitDetail detail, int? sectionId) {
    final nodes = detail.nodesOfSection(sectionId);
    if (nodes.isEmpty) {
      return [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Text(
              '本节内容准备中',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        ),
      ];
    }
    return [
      for (final node in nodes)
        _KpTile(
          node: node,
          onOpen: () => _openKp(node),
          onPractice: () => _practiceNode(node),
        ),
    ];
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.section,
    required this.nodes,
    required this.folded,
    required this.onOpen,
    required this.onPractice,
  });

  final UnitSection section;
  final List<KnowledgeNode> nodes;
  final KnowledgeNode? folded;
  final ValueChanged<KnowledgeNode> onOpen;
  final ValueChanged<KnowledgeNode> onPractice;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final total = nodes.length + (folded == null ? 0 : 1);
    return Card(
      margin: EdgeInsets.zero,
      clipBehavior: Clip.antiAlias,
      child: ExpansionTile(
        key: PageStorageKey<String>('unit-section-${section.id}'),
        initiallyExpanded: true,
        shape: const Border(),
        collapsedShape: const Border(),
        tilePadding: const EdgeInsets.symmetric(horizontal: 14),
        childrenPadding: const EdgeInsets.fromLTRB(10, 0, 10, 10),
        leading: Icon(Icons.segment, size: 20, color: section.bandColor),
        title: Text(
          section.name,
          style: theme.textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        subtitle: Text(
          '$total 个知识点 · 掌握 ${section.avgMastery.round()}%',
          style: theme.textTheme.bodySmall,
        ),
        children: [
          if (folded == null && nodes.isEmpty)
            Padding(
              padding: const EdgeInsets.all(6),
              child: Text('本节内容准备中', style: theme.textTheme.bodySmall),
            ),
          if (folded != null)
            _KpTile(
              node: folded!,
              label: '本节要点',
              onOpen: () => onOpen(folded!),
              onPractice: () => onPractice(folded!),
            ),
          for (final node in nodes)
            _KpTile(
              node: node,
              onOpen: () => onOpen(node),
              onPractice: () => onPractice(node),
            ),
        ],
      ),
    );
  }
}

class _KpTile extends StatelessWidget {
  const _KpTile({
    required this.node,
    required this.onOpen,
    required this.onPractice,
    this.label,
  });

  final KnowledgeNode node;
  final VoidCallback onOpen;
  final VoidCallback onPractice;
  final String? label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final stateColor = _stateColor(context, node.state);
    return AccentCard(
      accent: node.bandColor,
      onTap: onOpen,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Row(
        children: [
          MasteryRing(
            score: node.masteryScore,
            color: node.bandColor,
            size: 44,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        label ?? node.displayName,
                        style: theme.textTheme.bodyLarge?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: stateColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        node.state,
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: stateColor,
                        ),
                      ),
                    ),
                  ],
                ),
                if (node.explanation != null && node.explanation!.isNotEmpty)
                  Text(
                    node.explanation!,
                    style: theme.textTheme.bodySmall,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                Text(
                  '${node.questionCount} 道题 · ${node.bandLabel}',
                  style: theme.textTheme.labelSmall,
                ),
              ],
            ),
          ),
          TextButton(onPressed: onPractice, child: const Text('练一练')),
        ],
      ),
    );
  }
}

Color _stateColor(BuildContext context, String state) {
  final accents = AppAccents.of(context);
  switch (state) {
    case '学习中':
      return accents.practice;
    case '待巩固':
      return accents.exam;
    case '已掌握':
      return accents.learn;
    default:
      return Theme.of(context).colorScheme.outline;
  }
}
