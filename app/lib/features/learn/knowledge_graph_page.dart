import 'dart:math' as math;

import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/features/learn/widgets/offline_banner.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 知识图谱（D-04 §6.2）：前置依赖连线 + 薄弱知识点高亮。
class KnowledgeGraphPage extends ConsumerStatefulWidget {
  const KnowledgeGraphPage({
    super.key,
    required this.textbookId,
    required this.textbookName,
  });

  final int textbookId;
  final String textbookName;

  @override
  ConsumerState<KnowledgeGraphPage> createState() => _KnowledgeGraphPageState();
}

class _KnowledgeGraphPageState extends ConsumerState<KnowledgeGraphPage> {
  List<UnitDetail> _units = const [];
  int? _unitFilter;
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
      final service = ref.read(learnServiceProvider);
      final units = await service.units(widget.textbookId);
      final details = await Future.wait(
        units.map((unit) => service.unitDetail(unit.id)),
      );
      if (!mounted) return;
      setState(() {
        _units = details;
        _unitFilter = null;
        _offline = false;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      List<UnitDetail> local = const [];
      if (error.statusCode == null) {
        final offline = ref.read(offlineLearnServiceProvider);
        final offlineUnits = await offline.units(widget.textbookId);
        final details = await Future.wait(
          offlineUnits.map((unit) => offline.unitDetail(unit.id)),
        );
        local = details.whereType<UnitDetail>().toList();
      }
      if (!mounted) return;
      setState(() {
        if (local.isNotEmpty) {
          _units = local;
          _unitFilter = null;
          _offline = true;
          _error = null;
        } else {
          _error = ApiErrorGuide.from(error).message;
        }
        _loading = false;
      });
    }
  }

  List<UnitDetail> get _visibleUnits {
    final filter = _unitFilter;
    if (filter == null) return _units;
    return _units.where((detail) => detail.unit.id == filter).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('知识图谱 · ${widget.textbookName}')),
      body: _buildBody(context),
    );
  }

  Widget _buildBody(BuildContext context) {
    final theme = Theme.of(context);
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
    final visible = _visibleUnits;
    final nodes = <KnowledgeNode>[];
    for (final detail in visible) {
      for (final node in detail.knowledgePoints) {
        if (node.nodeType == 'point') nodes.add(node);
      }
    }
    if (nodes.isEmpty) {
      return const Center(child: Text('该教材暂无知识点图谱'));
    }
    return Column(
      children: [
        if (_offline)
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: OfflineBanner(),
          ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                FilterChip(
                  key: const ValueKey('graph-unit-all'),
                  label: const Text('全部单元'),
                  selected: _unitFilter == null,
                  onSelected: (_) => setState(() => _unitFilter = null),
                ),
                for (final unit in _units)
                  Padding(
                    padding: const EdgeInsets.only(left: 8),
                    child: FilterChip(
                      key: ValueKey('graph-unit-${unit.unit.id}'),
                      label: Text(unit.unit.name),
                      selected: _unitFilter == unit.unit.id,
                      onSelected: (_) => setState(() => _unitFilter = unit.unit.id),
                    ),
                  ),
              ],
            ),
          ),
        ),
        const Padding(
          padding: EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: _Legend(),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
          child: Align(
            alignment: Alignment.centerLeft,
            child: Text(
              '箭头从「前置知识」指向后续知识点，点击节点查看详情',
              style: theme.textTheme.bodySmall,
            ),
          ),
        ),
        Expanded(
          child: ColoredBox(
            color: theme.colorScheme.surfaceContainerLow,
            child: _GraphCanvas(
              nodes: nodes,
              onTap: (node) => context.push('/kp/${node.id}'),
            ),
          ),
        ),
      ],
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    const entries = [
      ('weak', '薄弱', Color(0xFFE53935)),
      ('growing', '巩固中', Colors.orange),
      ('skilled', '较熟练', Colors.blue),
      ('mastered', '已精通', Colors.green),
    ];
    return Wrap(
      spacing: 12,
      runSpacing: 4,
      children: [
        for (final entry in entries)
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: entry.$3,
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
              const SizedBox(width: 4),
              Text(entry.$2, style: theme.textTheme.bodySmall),
            ],
          ),
      ],
    );
  }
}

class _GraphCanvas extends StatelessWidget {
  const _GraphCanvas({required this.nodes, required this.onTap});

  static const nodeWidth = 180.0;
  static const nodeHeight = 64.0;
  static const columnGap = 224.0;
  static const rowGap = 84.0;
  static const padding = 24.0;

  final List<KnowledgeNode> nodes;
  final ValueChanged<KnowledgeNode> onTap;

  @override
  Widget build(BuildContext context) {
    final layout = _Layout.build(nodes);
    final theme = Theme.of(context);
    final edges = <_Edge>[];
    for (final node in layout.nodes) {
      final target = layout.positions[node.node.id];
      if (target == null) continue;
      for (final prerequisite in node.node.prerequisites) {
        final source = layout.positions[prerequisite];
        if (source == null) continue;
        edges.add(
          _Edge(
            from: source + const Offset(nodeWidth, nodeHeight / 2),
            to: target + const Offset(0, nodeHeight / 2),
            weak: node.node.masteryBand == 'weak',
          ),
        );
      }
    }
    return InteractiveViewer(
      constrained: false,
      minScale: 0.6,
      maxScale: 2.2,
      boundaryMargin: const EdgeInsets.all(80),
      child: SizedBox(
        width: layout.width,
        height: layout.height,
        child: Stack(
          children: [
            Positioned.fill(
              child: CustomPaint(
                painter: _EdgePainter(
                  edges: edges,
                  normalColor: theme.colorScheme.outlineVariant,
                  weakColor: theme.colorScheme.error,
                ),
              ),
            ),
            for (final item in layout.nodes)
              Positioned(
                left: layout.positions[item.node.id]!.dx,
                top: layout.positions[item.node.id]!.dy,
                width: nodeWidth,
                height: nodeHeight,
                child: _GraphNodeCard(
                  node: item.node,
                  onTap: () => onTap(item.node),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _GraphNodeCard extends StatelessWidget {
  const _GraphNodeCard({
    required this.node,
    required this.onTap,
  });

  final KnowledgeNode node;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final weak = node.masteryBand == 'weak';
    return Material(
      color: node.bandColor.withValues(alpha: 0.08),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(
          color: weak ? node.bandColor : node.bandColor.withValues(alpha: 0.45),
          width: weak ? 2 : 1,
        ),
      ),
      child: InkWell(
        key: ValueKey('graph-node-${node.id}'),
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      node.displayName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelLarge?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  if (weak)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                      decoration: BoxDecoration(
                        color: node.bandColor.withValues(alpha: 0.16),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        '薄弱',
                        style: TextStyle(
                          color: node.bandColor,
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 2),
              Text(
                '掌握 ${node.masteryScore.round()}% · ${node.state}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: node.bandColor,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Edge {
  const _Edge({required this.from, required this.to, required this.weak});

  final Offset from;
  final Offset to;
  final bool weak;
}

class _EdgePainter extends CustomPainter {
  _EdgePainter({
    required this.edges,
    required this.normalColor,
    required this.weakColor,
  });

  final List<_Edge> edges;
  final Color normalColor;
  final Color weakColor;

  @override
  void paint(Canvas canvas, Size size) {
    for (final edge in edges) {
      final paint = Paint()
        ..color = edge.weak ? weakColor.withValues(alpha: 0.75) : normalColor
        ..strokeWidth = edge.weak ? 1.8 : 1.2
        ..style = PaintingStyle.stroke;
      final midX = (edge.from.dx + edge.to.dx) / 2;
      final path = Path()
        ..moveTo(edge.from.dx, edge.from.dy)
        ..cubicTo(
          midX,
          edge.from.dy,
          midX,
          edge.to.dy,
          edge.to.dx,
          edge.to.dy,
        );
      canvas.drawPath(path, paint);

      final angle = math.atan2(
        edge.to.dy - edge.from.dy,
        edge.to.dx - edge.from.dx,
      );
      const arrow = 6.0;
      final arrowPaint = Paint()
        ..color = edge.weak ? weakColor.withValues(alpha: 0.75) : normalColor
        ..style = PaintingStyle.fill;
      final arrowPath = Path()
        ..moveTo(edge.to.dx, edge.to.dy)
        ..lineTo(
          edge.to.dx - arrow * math.cos(angle - 0.5),
          edge.to.dy - arrow * math.sin(angle - 0.5),
        )
        ..lineTo(
          edge.to.dx - arrow * math.cos(angle + 0.5),
          edge.to.dy - arrow * math.sin(angle + 0.5),
        )
        ..close();
      canvas.drawPath(arrowPath, arrowPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _EdgePainter oldDelegate) {
    return oldDelegate.edges != edges ||
        oldDelegate.normalColor != normalColor ||
        oldDelegate.weakColor != weakColor;
  }
}

class _GraphNode {
  const _GraphNode({required this.node, required this.order});

  final KnowledgeNode node;
  final int order;
}

class _Layout {
  const _Layout({
    required this.nodes,
    required this.positions,
    required this.width,
    required this.height,
  });

  final List<_GraphNode> nodes;
  final Map<int, Offset> positions;
  final double width;
  final double height;

  static _Layout build(List<KnowledgeNode> source) {
    final byId = {for (final node in source) node.id: node};
    final orderIndex = {for (var i = 0; i < source.length; i++) source[i].id: i};
    int depthOf(int id, Set<int> visiting, Map<int, int> memo) {
      final cached = memo[id];
      if (cached != null) return cached;
      if (!visiting.add(id)) return 0;
      final node = byId[id];
      var depth = 0;
      if (node != null) {
        for (final prerequisite in node.prerequisites) {
          if (!byId.containsKey(prerequisite)) continue;
          depth = math.max(depth, depthOf(prerequisite, visiting, memo) + 1);
        }
      }
      visiting.remove(id);
      memo[id] = depth;
      return depth;
    }

    final memo = <int, int>{};
    final columns = <int, List<_GraphNode>>{};
    final nodes = <_GraphNode>[];
    for (var i = 0; i < source.length; i++) {
      final node = source[i];
      final depth = depthOf(node.id, <int>{}, memo);
      final ordered = _GraphNode(node: node, order: orderIndex[node.id]!);
      nodes.add(ordered);
      columns.putIfAbsent(depth, () => []).add(ordered);
    }
    final positions = <int, Offset>{};
    var maxColumnCount = 0;
    for (final entry in columns.entries) {
      entry.value.sort((a, b) => a.order.compareTo(b.order));
      maxColumnCount = math.max(maxColumnCount, entry.value.length);
      for (var row = 0; row < entry.value.length; row++) {
        positions[entry.value[row].node.id] = Offset(
          _GraphCanvas.padding + entry.key * _GraphCanvas.columnGap,
          _GraphCanvas.padding + row * _GraphCanvas.rowGap,
        );
      }
    }
    final columnsCount = columns.isEmpty ? 1 : columns.keys.reduce(math.max) + 1;
    return _Layout(
      nodes: nodes,
      positions: positions,
      width: _GraphCanvas.padding * 2 +
          (columnsCount - 1) * _GraphCanvas.columnGap +
          _GraphCanvas.nodeWidth,
      height: _GraphCanvas.padding * 2 +
          math.max(1, maxColumnCount) * _GraphCanvas.rowGap,
    );
  }
}
