import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

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
  List<ChapterTree> _tree = const [];
  bool _loading = true;
  String? _error;
  final Map<int, GlobalKey> _chapterKeys = {};

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
      final tree =
          await ref.read(learnServiceProvider).knowledgeTree(widget.textbookId);
      if (!mounted) return;
      setState(() {
        _tree = tree;
        _loading = false;
      });
      if (widget.initialChapterId != null) {
        WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToChapter());
      }
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
    }
  }

  void _scrollToChapter() {
    final key = _chapterKeys[widget.initialChapterId];
    final context = key?.currentContext;
    if (context != null) {
      Scrollable.ensureVisible(
        context,
        duration: const Duration(milliseconds: 300),
        alignment: 0.1,
      );
    }
  }

  void _startPractice(KnowledgeNode node) {
    context.go(
      '/session'
      '?kp=${node.id}'
      '&title=${Uri.encodeComponent(node.name)}',
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.textbookName)),
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
    if (_tree.isEmpty) {
      return const Center(child: Text('该教材暂无知识点内容'));
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            '知识点掌握度',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 4),
          Text(
            '薄弱 → 巩固 → 熟练 → 精通，答对率越高颜色越绿',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 12),
          for (final chapter in _tree) ...[
            _ChapterCard(
              chapterKey: _chapterKeys.putIfAbsent(chapter.id, GlobalKey.new),
              chapter: chapter,
              onPractice: _startPractice,
            ),
            const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }
}

class _ChapterCard extends StatelessWidget {
  const _ChapterCard({
    required this.chapterKey,
    required this.chapter,
    required this.onPractice,
  });

  final GlobalKey chapterKey;
  final ChapterTree chapter;
  final ValueChanged<KnowledgeNode> onPractice;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      key: chapterKey,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.bookmark_outline, size: 20, color: theme.colorScheme.primary),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    chapter.name,
                    style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                  ),
                ),
                Text('${chapter.knowledgePoints.length} 个知识点',
                    style: theme.textTheme.bodySmall),
              ],
            ),
            if (chapter.summary != null) ...[
              const SizedBox(height: 4),
              Text(chapter.summary!, style: theme.textTheme.bodySmall),
            ],
            const Divider(height: 20),
            if (chapter.knowledgePoints.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Text('暂无知识点题目', style: theme.textTheme.bodySmall),
              )
            else
              for (final node in chapter.knowledgePoints)
                _KnowledgeTile(node: node, onPractice: () => onPractice(node)),
          ],
        ),
      ),
    );
  }
}

class _KnowledgeTile extends StatelessWidget {
  const _KnowledgeTile({required this.node, required this.onPractice});

  final KnowledgeNode node;
  final VoidCallback onPractice;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          SizedBox(
            width: 52,
            height: 52,
            child: Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 48,
                  height: 48,
                  child: CircularProgressIndicator(
                    value: (node.masteryScore / 100).clamp(0, 1),
                    strokeWidth: 5,
                    backgroundColor: theme.colorScheme.surfaceContainerHighest,
                    color: node.bandColor,
                  ),
                ),
                Text(
                  node.masteryScore.round().toString(),
                  style: theme.textTheme.labelSmall?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        node.name,
                        style: theme.textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: node.bandColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        node.bandLabel,
                        style: theme.textTheme.labelSmall?.copyWith(color: node.bandColor),
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
                Text('${node.questionCount} 道题', style: theme.textTheme.labelSmall),
              ],
            ),
          ),
          FilledButton.tonal(
            onPressed: onPractice,
            child: const Text('练一练'),
          ),
        ],
      ),
    );
  }
}
