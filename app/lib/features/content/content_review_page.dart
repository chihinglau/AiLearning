import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/content_review.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// P2-09 内容审核：审核员复核、运营发布（提交人不得自审、复核人不得自发布）。
class ContentReviewPage extends ConsumerStatefulWidget {
  const ContentReviewPage({super.key});

  @override
  ConsumerState<ContentReviewPage> createState() => _ContentReviewPageState();
}

class _ContentReviewPageState extends ConsumerState<ContentReviewPage> {
  static const _filters = {
    'all': '全部',
    'pending': '待复核',
    'approved': '已通过',
    'rejected': '已驳回',
    'published': '已发布',
  };

  List<ContentReview> _reviews = const [];
  String _filter = 'pending';
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
      final service = ref.read(contentReviewServiceProvider);
      final items = await service.list(
        status: _filter == 'all' ? null : _filter,
      );
      if (!mounted) return;
      setState(() {
        _reviews = items;
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

  Future<void> _decide(ContentReview review, {required bool approve}) async {
    String? comment;
    if (!approve) {
      comment = await _askRejectComment();
      if (comment == null) return;
    }
    try {
      await ref
          .read(contentReviewServiceProvider)
          .decide(review.id, approve: approve, comment: comment);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(approve ? '已通过复核' : '已驳回并记录原因')),
      );
      await _load();
    } on ApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiErrorGuide.from(error).message)),
      );
    }
  }

  Future<void> _publish(ContentReview review) async {
    try {
      await ref.read(contentReviewServiceProvider).publish(review.id);
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('内容已发布')));
      await _load();
    } on ApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiErrorGuide.from(error).message)),
      );
    }
  }

  Future<String?> _askRejectComment() async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('驳回原因'),
        content: TextField(
          controller: controller,
          maxLength: 200,
          maxLines: 3,
          decoration: const InputDecoration(hintText: '请说明需要修改的问题'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () {
              final text = controller.text.trim();
              Navigator.of(dialogContext).pop(text.isEmpty ? null : text);
            },
            child: const Text('提交'),
          ),
        ],
      ),
    );
    controller.dispose();
    return result;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final user = ref.watch(currentUserProvider);
    final canDecide = user?.hasPermission('content:review:decide') ?? false;
    final canPublish = user?.hasPermission('content:publish') ?? false;
    return Scaffold(
      appBar: AppBar(
        leading: Navigator.of(context).canPop()
            ? null
            : IconButton(
                tooltip: '返回首页',
                icon: const Icon(Icons.home_outlined),
                onPressed: () => context.go('/shell'),
              ),
        title: const Text('内容审核'),
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
                      onSelected: (_) {
                        if (_filter == entry.key) return;
                        setState(() => _filter = entry.key);
                        _load();
                      },
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
            else if (_reviews.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 48),
                child: Column(
                  children: [
                    Icon(
                      Icons.fact_check_outlined,
                      size: 56,
                      color: theme.colorScheme.primary,
                    ),
                    const SizedBox(height: 12),
                    Text('暂无复核单', style: theme.textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Text('运营提交内容后将在此显示', style: theme.textTheme.bodySmall),
                  ],
                ),
              )
            else
              for (final review in _reviews) ...[
                _ReviewCard(
                  review: review,
                  canDecide: canDecide,
                  canPublish: canPublish,
                  onApprove: () => _decide(review, approve: true),
                  onReject: () => _decide(review, approve: false),
                  onPublish: () => _publish(review),
                ),
                const SizedBox(height: 12),
              ],
          ],
        ),
      ),
    );
  }
}

class _ReviewCard extends StatelessWidget {
  const _ReviewCard({
    required this.review,
    required this.canDecide,
    required this.canPublish,
    required this.onApprove,
    required this.onReject,
    required this.onPublish,
  });

  final ContentReview review;
  final bool canDecide;
  final bool canPublish;
  final VoidCallback onApprove;
  final VoidCallback onReject;
  final VoidCallback onPublish;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = switch (review.status) {
      'pending' => theme.colorScheme.primary,
      'approved' => Colors.teal,
      'rejected' => theme.colorScheme.error,
      'published' => Colors.green,
      _ => theme.colorScheme.outline,
    };
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    review.title,
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.w600),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    review.statusLabel,
                    style: theme.textTheme.labelSmall?.copyWith(color: color),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              '${review.typeLabel} #${review.contentId} · 提交人 ${review.submittedBy}',
              style: theme.textTheme.bodySmall,
            ),
            if (review.note != null && review.note!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text('说明：${review.note}', style: theme.textTheme.bodySmall),
            ],
            if (review.comment != null && review.comment!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text('复核意见：${review.comment}', style: theme.textTheme.bodySmall),
            ],
            if (review.canApprove && canDecide) ...[
              const SizedBox(height: 10),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  OutlinedButton(
                    key: ValueKey('reject-${review.id}'),
                    onPressed: onReject,
                    child: const Text('驳回'),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    key: ValueKey('approve-${review.id}'),
                    onPressed: onApprove,
                    child: const Text('通过'),
                  ),
                ],
              ),
            ],
            if (review.canPublish && canPublish) ...[
              const SizedBox(height: 10),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.icon(
                  key: ValueKey('publish-${review.id}'),
                  onPressed: onPublish,
                  icon: const Icon(Icons.publish_outlined),
                  label: const Text('发布'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
