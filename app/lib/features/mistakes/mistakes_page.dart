import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class MistakesPage extends ConsumerStatefulWidget {
  const MistakesPage({super.key});

  @override
  ConsumerState<MistakesPage> createState() => _MistakesPageState();
}

class _MistakesPageState extends ConsumerState<MistakesPage> {
  List<WrongQuestionItem> _items = const [];
  int _dueCount = 0;
  bool _loading = true;
  String? _error;
  bool _showMastered = false;

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
      final results = await (
        service.wrongQuestions(status: _showMastered ? 'mastered' : 'active'),
        service.stats(),
      ).wait;
      if (!mounted) return;
      setState(() {
        _items = results.$1;
        _dueCount = results.$2.dueReviewCount;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
    }
  }

  Future<void> _tagReason(WrongQuestionItem item, String reason) async {
    try {
      await ref.read(learnServiceProvider).tagReason(item.id, reason);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('错因已标注为「${WrongReason.labelOf(reason)}」')),
      );
      await _load();
    } on ApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
    }
  }

  void _startReview() {
    context.go('/session?title=${Uri.encodeComponent('今日复习')}&review=1');
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('错题本')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Card(
                    color: theme.colorScheme.primaryContainer,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: [
                          Icon(Icons.repeat, size: 36, color: theme.colorScheme.primary),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('今日到期复习 $_dueCount 题',
                                    style: theme.textTheme.titleMedium),
                                const SizedBox(height: 2),
                                Text(
                                  '按记忆曲线安排，连续答对 3 次即可消灭错题',
                                  style: theme.textTheme.bodySmall,
                                ),
                              ],
                            ),
                          ),
                          FilledButton(
                            onPressed: _dueCount > 0 ? _startReview : null,
                            child: const Text('去复习'),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  SegmentedButton<bool>(
                    segments: const [
                      ButtonSegment(value: false, label: Text('待消灭')),
                      ButtonSegment(value: true, label: Text('已消灭')),
                    ],
                    selected: {_showMastered},
                    onSelectionChanged: (value) {
                      setState(() => _showMastered = value.first);
                      _load();
                    },
                  ),
                  const SizedBox(height: 12),
                  if (_error != null)
                    Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
                  if (!_loading && _items.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 48),
                      child: Center(
                        child: Text(
                          _showMastered ? '还没有已消灭的错题' : '太棒了，当前没有错题',
                          style: theme.textTheme.bodyMedium,
                        ),
                      ),
                    )
                  else
                    ..._items.map((item) => _WrongCard(
                          item: item,
                          onTagReason: (reason) => _tagReason(item, reason),
                        )),
                ],
              ),
            ),
    );
  }
}

class _WrongCard extends StatelessWidget {
  const _WrongCard({required this.item, required this.onTagReason});

  final WrongQuestionItem item;
  final ValueChanged<String> onTagReason;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dueText = item.nextReviewAt == null
        ? '已消灭'
        : '下次复习：${item.nextReviewAt!.month}-${item.nextReviewAt!.day}';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Chip(
                  label: Text(item.subjectLabel),
                  visualDensity: VisualDensity.compact,
                ),
                const SizedBox(width: 6),
                Text('错 ${item.wrongCount} 次', style: theme.textTheme.labelSmall),
                const Spacer(),
                Text(dueText, style: theme.textTheme.labelSmall),
              ],
            ),
            const SizedBox(height: 4),
            Text(item.stem.isEmpty ? '（题目内容缺失）' : item.stem,
                style: theme.textTheme.bodyLarge, maxLines: 3, overflow: TextOverflow.ellipsis),
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(Icons.label_outline, size: 16, color: theme.colorScheme.outline),
                const SizedBox(width: 4),
                Text('错因：${WrongReason.labelOf(item.wrongReason)}',
                    style: theme.textTheme.bodySmall),
                const Spacer(),
                PopupMenuButton<String>(
                  tooltip: '标注错因',
                  onSelected: onTagReason,
                  itemBuilder: (context) => [
                    for (final reason in WrongReason.all)
                      PopupMenuItem(value: reason.code, child: Text(reason.label)),
                  ],
                  child: Text(
                    '标注错因',
                    style: TextStyle(color: theme.colorScheme.primary, fontSize: 13),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
