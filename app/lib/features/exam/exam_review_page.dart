import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 真题审核队列（EX-10 / D-09 §5.7 P2）：通过并发布、退回草稿、下线。
///
/// 仅 `content:review:decide` 可进入；列表由服务端按状态下发，前端不本地猜状态。
const kExamReviewStatuses = <String, String>{
  'pending_review': '待复核',
  'draft': '草稿',
  'published': '已发布',
  'offline': '已下线',
};

class ExamReviewPage extends ConsumerStatefulWidget {
  const ExamReviewPage({super.key});

  @override
  ConsumerState<ExamReviewPage> createState() => _ExamReviewPageState();
}

class _ExamReviewPageState extends ConsumerState<ExamReviewPage> {
  String _status = 'pending_review';
  List<ExamReviewItem> _items = [];
  bool _loading = true;
  bool _busy = false;
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
          .listReviews(status: _status);
      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = '$error';
        _loading = false;
      });
    }
  }

  /// 退回必须带复核意见（后端 EXAM_REVIEW_NOTE_REQUIRED）；其余决策意见可选。
  Future<String?> _askRejectNote() async {
    var text = '';
    String? emptyError;
    final result = await showDialog<String?>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) {
          void submit() {
            if (text.trim().isEmpty) {
              setDialogState(() => emptyError = '退回必须填写复核意见');
              return;
            }
            Navigator.of(dialogContext).pop(text.trim());
          }

          return AlertDialog(
            title: const Text('退回草稿并说明原因'),
            content: TextField(
              autofocus: true,
              maxLength: 500,
              minLines: 2,
              maxLines: 4,
              onChanged: (value) => setDialogState(() {
                text = value;
                if (emptyError != null) emptyError = null;
              }),
              decoration: InputDecoration(
                hintText: '例：授权凭证未登记 R-07 台账，请补齐来源后重新提交',
                errorText: emptyError,
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(null),
                child: const Text('取消'),
              ),
              FilledButton(
                onPressed: submit,
                child: const Text('确认退回'),
              ),
            ],
          );
        },
      ),
    );
    return result;
  }

  Future<void> _decide(ExamReviewItem item, String decision) async {
    String? note;
    if (decision == 'reject') {
      note = await _askRejectNote();
      if (note == null || note.isEmpty) return;
    }
    if (!mounted) return;
    setState(() => _busy = true);
    try {
      await ref.read(examServiceProvider).reviewExam(item.id, decision, note: note);
      if (!mounted) return;
      setState(() => _busy = false);
      const decisionLabels = {
        'approve': '已发布',
        'reject': '已退回草稿',
        'offline': '已下线',
        'restore': '已回到草稿（需重新提交复核）',
      };
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${decisionLabels[decision] ?? decision}：${item.title}'),
        ),
      );
      await _load();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _busy = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiErrorGuide.from(error).message)),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() => _busy = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('操作失败：$error')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('试卷复核')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Wrap(
              spacing: 8,
              children: [
                for (final entry in kExamReviewStatuses.entries)
                  ChoiceChip(
                    label: Text(entry.value),
                    selected: _status == entry.key,
                    onSelected: (_) {
                      setState(() => _status = entry.key);
                      _load();
                    },
                  ),
              ],
            ),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 12),
            child: Text(
              '真题缺来源时不能提交复核或发布；请按 R-07 台账核验授权凭证。',
              style: TextStyle(fontSize: 12),
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text('加载失败：$_error'),
                            const SizedBox(height: 8),
                            OutlinedButton(
                              onPressed: _load,
                              child: const Text('重试'),
                            ),
                          ],
                        ),
                      )
                    : _items.isEmpty
                        ? const Center(child: Text('当前状态暂无试卷'))
                        : RefreshIndicator(
                            onRefresh: _load,
                            child: ListView(
                              padding: const EdgeInsets.all(12),
                              children: [
                                for (final item in _items)
                                  _ReviewCard(
                                    item: item,
                                    busy: _busy,
                                    onDecide: (decision) =>
                                        _decide(item, decision),
                                  ),
                              ],
                            ),
                          ),
          ),
        ],
      ),
    );
  }
}

class _ReviewCard extends StatelessWidget {
  const _ReviewCard({
    required this.item,
    required this.busy,
    required this.onDecide,
  });

  final ExamReviewItem item;
  final bool busy;
  final ValueChanged<String> onDecide;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              item.title,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            Text(
              '${item.year ?? '—'} · ${item.region ?? '—'} · ${item.subject} · '
              '${item.grade} 年级 · 来源：${item.sourceLabel} · ${item.statusLabel}',
            ),
            if (item.licenseNote != null && item.licenseNote!.isNotEmpty)
              Text('授权说明：${item.licenseNote}'),
            if (item.reviewNote != null && item.reviewNote!.isNotEmpty)
              Text('审核备注：${item.reviewNote}'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                if (item.status == 'pending_review') ...[
                  FilledButton.icon(
                    onPressed: busy ? null : () => onDecide('approve'),
                    icon: const Icon(Icons.check_outlined),
                    label: const Text('通过并发布'),
                  ),
                  OutlinedButton.icon(
                    onPressed: busy ? null : () => onDecide('reject'),
                    icon: const Icon(Icons.undo_outlined),
                    label: const Text('退回草稿'),
                  ),
                ],
                if (item.status == 'published')
                  OutlinedButton.icon(
                    onPressed: busy ? null : () => onDecide('offline'),
                    icon: const Icon(Icons.archive_outlined),
                    label: const Text('下线'),
                  ),
                // 误下线可回草稿（评审 R2-05），但不直接还原为已发布
                if (item.status == 'offline')
                  OutlinedButton.icon(
                    onPressed: busy ? null : () => onDecide('restore'),
                    icon: const Icon(Icons.restore_outlined),
                    label: const Text('回草稿重审'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
