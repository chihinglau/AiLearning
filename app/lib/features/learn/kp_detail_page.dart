import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/features/learn/mastery_ring.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 知识点详情（D-04 §6.4）：掌握度/状态、前置跳转、讲解与例题。
class KpDetailPage extends ConsumerStatefulWidget {
  const KpDetailPage({super.key, required this.kpId});

  final int kpId;

  @override
  ConsumerState<KpDetailPage> createState() => _KpDetailPageState();
}

class _KpDetailPageState extends ConsumerState<KpDetailPage> {
  KpDetail? _detail;
  List<KpExample> _examples = const [];
  bool _loading = true;
  bool _marking = false;
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
          await ref.read(learnServiceProvider).kpDetail(widget.kpId);
      final examples =
          await ref.read(learnServiceProvider).kpExamples(widget.kpId);
      if (!mounted) return;
      setState(() {
        _detail = detail;
        _examples = examples;
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

  Future<void> _markRead() async {
    if (_marking || _detail == null) return;
    setState(() => _marking = true);
    try {
      final state = await ref.read(learnServiceProvider).markKpRead(widget.kpId);
      if (!mounted) return;
      setState(() {
        _detail = _copyWithState(state);
        _marking = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('已标记为$state')),
      );
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _marking = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiErrorGuide.from(error).message)),
      );
    }
  }

  KpDetail? _copyWithState(String state) {
    final detail = _detail;
    if (detail == null) return null;
    return KpDetail(
      id: detail.id,
      subject: detail.subject,
      grade: detail.grade,
      name: detail.name,
      nodeType: detail.nodeType,
      explanation: detail.explanation,
      sectionId: detail.sectionId,
      sectionName: detail.sectionName,
      prerequisites: detail.prerequisites,
      masteryScore: detail.masteryScore,
      masteryConfidence: detail.masteryConfidence,
      masteryBand: detail.masteryBand,
      questionCount: detail.questionCount,
      state: state,
      stateEvidence: detail.stateEvidence + 1,
      lastStudiedAt: DateTime.now(),
    );
  }

  void _openPrerequisite(KpBrief prerequisite) {
    context.go('/kp/${prerequisite.id}');
  }

  void _practice() {
    final detail = _detail;
    if (detail == null) return;
    context.go(
      '/session?kp=${detail.id}&title=${Uri.encodeComponent(detail.name)}',
    );
  }

  @override
  Widget build(BuildContext context) {
    final detail = _detail;
    return Scaffold(
      appBar: AppBar(title: Text(detail?.name ?? '知识点')),
      body: _buildBody(context),
      bottomNavigationBar: detail == null
          ? null
          : SafeArea(
              minimum: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              child: Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _markRead,
                      icon: const Icon(Icons.task_alt),
                      label: Text(
                        _marking
                            ? '提交中…'
                            : detail.state == '未学习'
                                ? '我已理解'
                                : '已阅读',
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: _practice,
                      icon: const Icon(Icons.edit_note),
                      label: const Text('练一练'),
                    ),
                  ),
                ],
              ),
            ),
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
            Text(_error ?? '知识点加载失败'),
            const SizedBox(height: 12),
            FilledButton(onPressed: _load, child: const Text('重试')),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  MasteryRing(
                    score: detail.masteryScore,
                    color: detail.bandColor,
                    size: 56,
                    strokeWidth: 6,
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Wrap(
                          spacing: 6,
                          runSpacing: 4,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            _Tag(
                              label: detail.state,
                              color: _stateColor(context, detail.state),
                            ),
                            _Tag(
                              label: detail.bandLabelText,
                              color: detail.bandColor,
                            ),
                            if (detail.sectionName != null)
                              _Tag(
                                label: detail.sectionName!,
                                color: theme.colorScheme.outline,
                              ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          '${detail.questionCount} 道题 · 掌握置信度 '
                          '${detail.masteryConfidence}%',
                          style: theme.textTheme.bodySmall,
                        ),
                        if (detail.lastStudiedAt != null) ...[
                          const SizedBox(height: 2),
                          Text(
                            '最近学习：${_formatTime(detail.lastStudiedAt!)}',
                            style: theme.textTheme.labelSmall,
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (detail.prerequisites.isNotEmpty) ...[
            const SizedBox(height: 20),
            Text('前置知识点', style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final prerequisite in detail.prerequisites)
                  ActionChip(
                    avatar: Icon(
                      Icons.subdirectory_arrow_right,
                      size: 16,
                      color: masteryBandColor(
                        prerequisite.masteryScore >= 85
                            ? 'mastered'
                            : prerequisite.masteryScore >= 65
                                ? 'skilled'
                                : prerequisite.masteryScore >= 40
                                    ? 'growing'
                                    : 'weak',
                      ),
                    ),
                    label: Text(prerequisite.name),
                    onPressed: () => _openPrerequisite(prerequisite),
                  ),
              ],
            ),
          ],
          const SizedBox(height: 20),
          Text('讲解', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Text(
                detail.explanation?.trim().isNotEmpty == true
                    ? detail.explanation!
                    : '该知识点暂无文字讲解，可先通过例题理解核心思路。',
                style: theme.textTheme.bodyMedium,
              ),
            ),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Text('例题', style: theme.textTheme.titleMedium),
              const SizedBox(width: 8),
              Text(
                '${_examples.length} 道',
                style: theme.textTheme.bodySmall,
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (_examples.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(14),
                child: Text('暂无例题，可直接进入练习检测掌握情况。'),
              ),
            )
          else
            for (final example in _examples) ...[
              _ExampleCard(example: example),
              const SizedBox(height: 10),
            ],
        ],
      ),
    );
  }
}

class _ExampleCard extends StatelessWidget {
  const _ExampleCard({required this.example});

  final KpExample example;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _Tag(
                  label: example.typeLabel,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 6),
                Text(
                  '难度 ${example.difficulty}',
                  style: theme.textTheme.labelSmall,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(example.stem, style: theme.textTheme.bodyMedium),
            if (example.options.isNotEmpty) ...[
              const SizedBox(height: 8),
              for (final option in example.options)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(
                    '${option.key}. ${option.text}',
                    style: theme.textTheme.bodySmall,
                  ),
                ),
            ],
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer.withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '答案：${example.correctAnswer}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (example.analysis != null &&
                      example.analysis!.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      '解析：${example.analysis}',
                      style: theme.textTheme.bodySmall,
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Tag extends StatelessWidget {
  const _Tag({required this.label, required this.color});

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

String _formatTime(DateTime value) {
  final local = value.toLocal();
  String two(int number) => number.toString().padLeft(2, '0');
  return '${local.year}-${two(local.month)}-${two(local.day)} '
      '${two(local.hour)}:${two(local.minute)}';
}
