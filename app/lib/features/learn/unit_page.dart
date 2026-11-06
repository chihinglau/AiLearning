import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/features/learn/mastery_ring.dart';
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
      final detail =
          await ref.read(learnServiceProvider).unitDetail(widget.chapterId);
      if (!mounted) return;
      setState(() {
        _detail = detail;
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

  void _openKp(KnowledgeNode node) {
    context.go('/kp/${node.id}');
  }

  void _practiceNode(KnowledgeNode node) {
    context.go(
      '/practice/config?scope=kp&ids=${node.id}'
      '&chapter=${widget.chapterId}'
      '${widget.textbookId == null ? '' : '&textbook=${widget.textbookId}'}'
      '&title=${Uri.encodeComponent(node.name)}',
    );
  }

  void _practiceUnit() {
    context.go(
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
                child: Text('该单元暂无知识点内容，敬请期待。'),
              ),
            ),
          for (final section in detail.sections) ...[
            _SectionHeader(section: section, count: detail.nodesOfSection(section.id).length),
            const SizedBox(height: 8),
            ..._nodesBlock(detail, section.id),
            const SizedBox(height: 16),
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
              '本节暂无知识点',
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

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.section, required this.count});

  final UnitSection section;
  final int count;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Icon(Icons.segment, size: 18, color: section.bandColor),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            section.name,
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        Text('$count 个知识点', style: theme.textTheme.bodySmall),
      ],
    );
  }
}

class _KpTile extends StatelessWidget {
  const _KpTile({
    required this.node,
    required this.onOpen,
    required this.onPractice,
  });

  final KnowledgeNode node;
  final VoidCallback onOpen;
  final VoidCallback onPractice;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final stateColor = _stateColor(context, node.state);
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onOpen,
        child: Padding(
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
                            node.name,
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
                            style: theme.textTheme.labelSmall
                                ?.copyWith(color: stateColor),
                          ),
                        ),
                      ],
                    ),
                    if (node.explanation != null &&
                        node.explanation!.isNotEmpty)
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
              TextButton(
                onPressed: onPractice,
                child: const Text('练一练'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

Color _stateColor(BuildContext context, String state) {
  switch (state) {
    case '学习中':
      return Colors.blue;
    case '待巩固':
      return Colors.orange;
    case '已掌握':
      return Colors.green;
    default:
      return Theme.of(context).colorScheme.outline;
  }
}
