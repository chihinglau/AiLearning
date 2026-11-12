import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/features/learn/widgets/offline_banner.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 知识点讲解独立页：从前置知识点列表点进来第一屏就是讲解本身。
///
/// 与 `/kp/:kpId` 的完整详情页分工：本页只负责「看懂这个知识点」，
/// 掌握度、前置依赖、学习状态等留在完整详情页，前置列表因此保持简洁。
class KpExplainPage extends ConsumerStatefulWidget {
  const KpExplainPage({super.key, required this.kpId});

  final int kpId;

  @override
  ConsumerState<KpExplainPage> createState() => _KpExplainPageState();
}

class _KpExplainPageState extends ConsumerState<KpExplainPage> {
  KpDetail? _detail;
  List<KpExample> _examples = const [];
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
      final detail = await service.kpDetail(widget.kpId);
      final examples = await service.kpExamples(widget.kpId);
      if (!mounted) return;
      setState(() {
        _detail = detail;
        _examples = examples;
        _offline = false;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      final service = ref.read(offlineLearnServiceProvider);
      final localDetail =
          error.statusCode == null ? await service.kpDetail(widget.kpId) : null;
      final localExamples = error.statusCode == null
          ? await service.kpExamples(widget.kpId)
          : const <KpExample>[];
      if (!mounted) return;
      setState(() {
        if (localDetail != null) {
          _detail = localDetail;
          _examples = localExamples;
          _offline = true;
          _error = null;
        } else {
          _error = ApiErrorGuide.from(error).message;
        }
        _loading = false;
      });
    }
  }

  void _openFullDetail() => context.push('/kp/${widget.kpId}');

  void _practice() {
    final name = _detail?.displayName ?? '知识点练习';
    context.push(
      '/practice/config?scope=kp&ids=${widget.kpId}'
      '&mode=special&title=${Uri.encodeComponent(name)}',
    );
  }

  @override
  Widget build(BuildContext context) {
    final detail = _detail;
    return Scaffold(
      appBar: AppBar(
        title: Text(detail == null ? '知识点讲解' : '${detail.displayName} · 讲解'),
      ),
      body: _buildBody(context),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        child: Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _openFullDetail,
                icon: const Icon(Icons.info_outline),
                label: const Text('完整详情'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FilledButton.icon(
                onPressed: detail == null ? null : _practice,
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
    final explanation = detail.explanation?.trim() ?? '';
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
        children: [
          if (_offline) const OfflineBanner(),
          if (detail.sectionName != null)
            Align(
              alignment: Alignment.centerLeft,
              child: Chip(
                label: Text(detail.sectionName!),
                visualDensity: VisualDensity.compact,
              ),
            ),
          const SizedBox(height: 8),
          Text('讲解', style: theme.textTheme.titleLarge),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                explanation.isNotEmpty
                    ? explanation
                    : '该知识点暂无文字讲解，可通过下方例题理解核心思路。',
                style: theme.textTheme.bodyLarge?.copyWith(height: 1.6),
              ),
            ),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Text('典型例题', style: theme.textTheme.titleMedium),
              const SizedBox(width: 8),
              Text('${_examples.length} 道', style: theme.textTheme.bodySmall),
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
            for (final example in _examples) _ExplainExampleCard(example: example),
          const SizedBox(height: 16),
          if (detail.prerequisites.isNotEmpty)
            TextButton.icon(
              onPressed: _openFullDetail,
              icon: const Icon(Icons.account_tree_outlined),
              label: Text('查看 ${detail.prerequisites.length} 个前置知识点与掌握度'),
            ),
        ],
      ),
    );
  }
}

class _ExplainExampleCard extends StatelessWidget {
  const _ExplainExampleCard({required this.example});

  final KpExample example;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${example.typeLabel} · 难度 ${example.difficulty}',
              style: theme.textTheme.labelSmall?.copyWith(
                color: theme.colorScheme.primary,
              ),
            ),
            const SizedBox(height: 8),
            Text(example.stem, style: theme.textTheme.bodyMedium),
            if (example.options.isNotEmpty) ...[
              const SizedBox(height: 8),
              for (final option in example.options)
                Padding(
                  padding: const EdgeInsets.only(bottom: 3),
                  child: Text(
                    '${option.key}. ${option.text}',
                    style: theme.textTheme.bodySmall,
                  ),
                ),
            ],
            const SizedBox(height: 8),
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: const Text('查看答案与解析'),
              children: [
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primaryContainer
                        .withValues(alpha: 0.4),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('答案：${example.correctAnswer}'),
                      if (example.analysis != null &&
                          example.analysis!.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text('解析：${example.analysis}'),
                      ],
                    ],
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
