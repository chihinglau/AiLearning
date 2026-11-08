import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/ai.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/theme/app_accents.dart';
import 'package:ai_learning/features/learn/widgets/offline_banner.dart';
import 'package:ai_learning/widgets/accent_card.dart';
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
  bool _offline = false;
  bool _showMastered = false;
  int? _diagnosingId;

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
    final status = _showMastered ? 'mastered' : 'active';
    final service = ref.read(learnServiceProvider);
    try {
      final items = await service.wrongQuestions(status: status);
      final stats = await service.stats();
      if (!mounted) return;
      setState(() {
        _items = items;
        _dueCount = stats.dueReviewCount;
        _offline = false;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      // 断网时回退到最近一次同步缓存。
      final offline = ref.read(offlineLearnServiceProvider);
      final cachedItems = error.statusCode == null
          ? await offline.cachedWrongQuestions(status)
          : null;
      final cachedStats = error.statusCode == null
          ? await offline.cachedStats()
          : null;
      if (!mounted) return;
      setState(() {
        if (cachedItems != null && cachedStats != null) {
          _items = cachedItems;
          _dueCount = cachedStats.dueReviewCount;
          _offline = true;
          _error = null;
        } else {
          _error = ApiErrorGuide.from(error).message;
        }
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
      await handleApiError(context, ref, error);
    }
  }

  void _startReview() {
    context.push('/session?title=${Uri.encodeComponent('今日复习')}&review=1');
  }

  /// AI 错因归因：服务端基于题型与错误历史给出候选错因与改进建议。
  Future<void> _diagnose(WrongQuestionItem item) async {
    if (_diagnosingId != null) return;
    setState(() => _diagnosingId = item.id);
    try {
      final diagnosis = await ref.read(aiServiceProvider).diagnose(item.id);
      if (!mounted) return;
      setState(() => _diagnosingId = null);
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        showDragHandle: true,
        builder: (sheetContext) => _DiagnosisSheet(
          item: item,
          diagnosis: diagnosis,
          onApply: () async {
            Navigator.of(sheetContext).pop();
            await _tagReason(item, diagnosis.reason);
          },
        ),
      );
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _diagnosingId = null);
      await handleApiError(context, ref, error);
    }
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
                  if (_offline)
                    const OfflineBanner(message: '离线模式，显示最近一次同步的错题与统计'),
                  AccentCard(
                    accent: AppAccents.of(context).exam,
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Icon(
                          Icons.repeat,
                          size: 36,
                          color: AppAccents.of(context).exam,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '今日到期复习 $_dueCount 题',
                                style: theme.textTheme.titleMedium,
                              ),
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
                    Text(
                      _error!,
                      style: TextStyle(color: theme.colorScheme.error),
                    ),
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
                    ..._items.map(
                      (item) => _WrongCard(
                        item: item,
                        diagnosing: _diagnosingId == item.id,
                        onTagReason: (reason) => _tagReason(item, reason),
                        onDiagnose: () => _diagnose(item),
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}

class _WrongCard extends StatelessWidget {
  const _WrongCard({
    required this.item,
    required this.diagnosing,
    required this.onTagReason,
    required this.onDiagnose,
  });

  final WrongQuestionItem item;
  final bool diagnosing;
  final ValueChanged<String> onTagReason;
  final VoidCallback onDiagnose;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dueText = item.nextReviewAt == null
        ? '已消灭'
        : '下次复习：${item.nextReviewAt!.month}-${item.nextReviewAt!.day}';
    // 待消灭用警示色、已消灭用掌握色，一眼区分两类错题。
    final accent = item.nextReviewAt == null
        ? AppAccents.of(context).learn
        : AppAccents.of(context).exam;
    return AccentCard(
      accent: accent,
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Chip(
                label: Text(item.subjectLabel),
                visualDensity: VisualDensity.compact,
                side: BorderSide(color: accent.withValues(alpha: 0.4)),
                backgroundColor: accent.withValues(alpha: 0.06),
                labelStyle: theme.textTheme.labelSmall?.copyWith(
                  color: accent,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(width: 6),
              Text('错 ${item.wrongCount} 次', style: theme.textTheme.labelSmall),
              const Spacer(),
              Text(dueText, style: theme.textTheme.labelSmall),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            item.stem.isEmpty ? '（题目内容缺失）' : item.stem,
            style: theme.textTheme.bodyLarge,
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Icon(
                Icons.label_outline,
                size: 16,
                color: theme.colorScheme.outline,
              ),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  '错因：${WrongReason.labelOf(item.wrongReason)}',
                  style: theme.textTheme.bodySmall,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              TextButton(
                key: ValueKey('ai-diagnose-${item.id}'),
                onPressed: diagnosing ? null : onDiagnose,
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  minimumSize: Size.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                child: diagnosing
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('AI 归因'),
              ),
              PopupMenuButton<String>(
                tooltip: '标注错因',
                onSelected: onTagReason,
                itemBuilder: (context) => [
                  for (final reason in WrongReason.all)
                    PopupMenuItem(
                      value: reason.code,
                      child: Text(reason.label),
                    ),
                ],
                child: Text(
                  '标注错因',
                  style: TextStyle(
                    color: theme.colorScheme.primary,
                    fontSize: 13,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DiagnosisSheet extends StatelessWidget {
  const _DiagnosisSheet({
    required this.item,
    required this.diagnosis,
    required this.onApply,
  });

  final WrongQuestionItem item;
  final AIDiagnosis diagnosis;
  final VoidCallback onApply;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.8,
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('AI 错因分析', style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              Text(
                item.stem.isEmpty ? '（题目内容缺失）' : item.stem,
                style: theme.textTheme.bodyMedium,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                children: [
                  Chip(
                    label: Text('候选错因：${diagnosis.reasonLabel}'),
                    visualDensity: VisualDensity.compact,
                  ),
                  Chip(
                    label: Text(diagnosis.confidenceLabel),
                    visualDensity: VisualDensity.compact,
                    backgroundColor: theme.colorScheme.secondaryContainer,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(diagnosis.explanation, style: theme.textTheme.bodyMedium),
              if (diagnosis.suggestions.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text('改进建议', style: theme.textTheme.titleSmall),
                const SizedBox(height: 4),
                for (final tip in diagnosis.suggestions)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text('· $tip', style: theme.textTheme.bodySmall),
                  ),
              ],
              const SizedBox(height: 8),
              Text(
                'AI 归因仅供参考，请结合老师讲解确认',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: FilledButton(
                      key: const ValueKey('apply-ai-reason'),
                      onPressed: onApply,
                      child: Text('采用该错因（${diagnosis.reasonLabel}）'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  OutlinedButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('关闭'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
