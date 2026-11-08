import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/offline_learn_service.dart';
import 'package:ai_learning/features/learn/mastery_ring.dart';
import 'package:ai_learning/features/learn/widgets/offline_banner.dart';
import 'package:ai_learning/widgets/accent_card.dart';
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
  bool _offline = false;
  bool _downloading = false;
  double _downloadProgress = 0;
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
      final units = await ref
          .read(learnServiceProvider)
          .units(widget.textbookId);
      if (!mounted) return;
      setState(() {
        _units = units;
        _offline = false;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      // 断网时回退到整册离线包。
      final local = error.statusCode == null
          ? await ref.read(offlineLearnServiceProvider).units(widget.textbookId)
          : const <UnitSummary>[];
      if (!mounted) return;
      setState(() {
        if (local.isNotEmpty) {
          _units = local;
          _offline = true;
          _error = null;
        } else {
          _error = ApiErrorGuide.from(error).message;
        }
        _loading = false;
      });
    }
  }

  Future<void> _showDownload() async {
    final service = ref.read(offlineLearnServiceProvider);
    final meta = await service.metaFor(widget.textbookId);
    if (!mounted) return;
    final action = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(meta == null ? '离线下载整册' : '整册离线包'),
        content: Text(
          meta == null
              ? '下载后可断网浏览单元、知识点与题目（含答案与解析）。'
              : '已下载 ${meta.units} 单元 · ${meta.questions} 道题\n'
                    '体积 ${meta.sizeText}\n'
                    '下载时间 ${_formatTime(meta.downloadedAt)}',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('取消'),
          ),
          if (meta != null)
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop('delete'),
              child: const Text('删除'),
            ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop('download'),
            child: Text(meta == null ? '开始下载' : '更新'),
          ),
        ],
      ),
    );
    if (!mounted || action == null) return;
    if (action == 'delete') {
      await service.remove(widget.textbookId);
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('已删除整册离线包')));
      return;
    }
    await _download(service);
  }

  Future<void> _download(OfflineLearnService service) async {
    setState(() {
      _downloading = true;
      _downloadProgress = 0;
    });
    try {
      final meta = await service.download(
        widget.textbookId,
        onProgress: (progress) {
          if (mounted) setState(() => _downloadProgress = progress);
        },
      );
      if (!mounted) return;
      setState(() => _downloading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('整册下载完成：${meta.units} 单元 · ${meta.questions} 道题'),
        ),
      );
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _downloading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiErrorGuide.from(error).message)),
      );
    }
  }

  String _formatTime(DateTime value) {
    String two(int number) => number.toString().padLeft(2, '0');
    return '${value.year}-${two(value.month)}-${two(value.day)} '
        '${two(value.hour)}:${two(value.minute)}';
  }

  void _openUnit(UnitSummary unit) {
    context.push(
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
            key: const ValueKey('download-textbook-bundle'),
            tooltip: '离线下载整册',
            icon: _downloading
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.download_for_offline_outlined),
            onPressed: _downloading ? null : _showDownload,
          ),
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
          if (_offline) const OfflineBanner(),
          if (_downloading) ...[
            LinearProgressIndicator(
              value: _downloadProgress <= 0 ? null : _downloadProgress,
            ),
            const SizedBox(height: 12),
          ],
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
    return AccentCard(
      accent: highlighted ? theme.colorScheme.primary : unit.bandColor,
      onTap: onTap,
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
                      color: visited
                          ? unit.bandColor
                          : theme.colorScheme.outline,
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
                    backgroundColor: theme.colorScheme.surfaceContainerHighest,
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
