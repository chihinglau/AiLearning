import 'dart:async';

import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/practice_session.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 智能练习配置（D-04 §7.2）：模式/范围/题量/题型 + 组卷预览 + 开始练习。
class PracticeConfigPage extends ConsumerStatefulWidget {
  const PracticeConfigPage({
    super.key,
    required this.scopeType,
    required this.scopeIds,
    required this.title,
    this.chapterId,
    this.textbookId,
    this.initialMode = 'special',
  });

  final String scopeType;
  final List<int> scopeIds;
  final String title;
  final int? chapterId;
  final int? textbookId;
  final String initialMode;

  @override
  ConsumerState<PracticeConfigPage> createState() => _PracticeConfigPageState();
}

class _PracticeConfigPageState extends ConsumerState<PracticeConfigPage> {
  static const _qTypeLabels = {
    'choice': '单选题',
    'multiple': '多选题',
    'fill': '填空题',
    'judge': '判断题',
  };

  late String _scopeType = widget.scopeType;
  late List<int> _scopeIds = widget.scopeIds;
  late String _mode = widget.initialMode;
  int _count = 10;
  final Set<String> _qTypes = {'choice', 'multiple', 'fill', 'judge'};

  PracticePreview? _preview;
  bool _loadingPreview = false;
  String? _error;
  int? _seed;

  @override
  void initState() {
    super.initState();
    _loadPreview();
  }

  List<_ScopeOption> get _scopeOptions {
    final options = <_ScopeOption>[
      _ScopeOption(widget.scopeType, widget.scopeIds, _scopeDefaultLabel),
    ];
    if (widget.scopeType == 'kp' && widget.chapterId != null) {
      options.add(
        _ScopeOption('chapter', [widget.chapterId!], '本单元'),
      );
    }
    if (widget.scopeType != 'textbook' && widget.textbookId != null) {
      options.add(
        _ScopeOption('textbook', [widget.textbookId!], '整册教材'),
      );
    }
    return options;
  }

  String get _scopeDefaultLabel {
    switch (widget.scopeType) {
      case 'kp':
        return '当前知识点';
      case 'chapter':
        return '本单元';
      case 'textbook':
        return '整册教材';
      default:
        return '错题重练';
    }
  }

  Future<void> _loadPreview() async {
    setState(() {
      _loadingPreview = true;
      _error = null;
    });
    try {
      final preview = await ref.read(learnServiceProvider).practicePreview(
            scopeType: _scopeType,
            scopeIds: _scopeIds,
            count: _count,
            qTypes: _qTypes.toList(),
            mode: _mode,
            seed: _seed,
          );
      if (!mounted) return;
      setState(() {
        _preview = preview;
        _seed = preview.seed;
        _loadingPreview = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loadingPreview = false;
      });
    }
  }

  void _reloadPreviewSoon() {
    unawaited(_loadPreview());
  }

  void _start() {
    final preview = _preview;
    if (preview == null || preview.count == 0) return;
    final query = [
      'scope=$_scopeType',
      'ids=${_scopeIds.join(',')}',
      'count=$_count',
      'qtypes=${_qTypes.join(',')}',
      'mode=$_mode',
      'seed=${_seed ?? preview.seed}',
      'title=${Uri.encodeComponent(widget.title)}',
    ].join('&');
    context.push('/session?$query');
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('练习配置')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(widget.title, style: theme.textTheme.titleLarge),
          const SizedBox(height: 4),
          Text(
            '先预览组卷结果，再开始练习；预览与实际题目一致。',
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: 20),
          _sectionTitle('练习模式'),
          const SizedBox(height: 8),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'special', label: Text('专项突破')),
              ButtonSegment(value: 'sync', label: Text('同步巩固')),
              ButtonSegment(value: 'pre_exam', label: Text('考前速练')),
            ],
            selected: {_mode},
            onSelectionChanged: (selection) {
              setState(() => _mode = selection.first);
              _reloadPreviewSoon();
            },
          ),
          if (_scopeOptions.length > 1) ...[
            const SizedBox(height: 20),
            _sectionTitle('练习范围'),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: _scopeOptions
                  .map(
                    (option) => ChoiceChip(
                      label: Text(option.label),
                      selected: _scopeType == option.type,
                      onSelected: (_) {
                        setState(() {
                          _scopeType = option.type;
                          _scopeIds = option.ids;
                          _seed = null;
                        });
                        _reloadPreviewSoon();
                      },
                    ),
                  )
                  .toList(),
            ),
          ],
          const SizedBox(height: 20),
          _sectionTitle('题量'),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [10, 15, 20]
                .map(
                  (count) => ChoiceChip(
                    label: Text('$count 题'),
                    selected: _count == count,
                    onSelected: (_) {
                      setState(() => _count = count);
                      _reloadPreviewSoon();
                    },
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: 20),
          _sectionTitle('题型'),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _qTypeLabels.entries
                .map(
                  (entry) => FilterChip(
                    label: Text(entry.value),
                    selected: _qTypes.contains(entry.key),
                    onSelected: (selected) {
                      if (!selected && _qTypes.length == 1) return;
                      setState(() {
                        if (selected) {
                          _qTypes.add(entry.key);
                        } else {
                          _qTypes.remove(entry.key);
                        }
                        _seed = null;
                      });
                      _reloadPreviewSoon();
                    },
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: 20),
          _sectionTitle('组卷预览'),
          const SizedBox(height: 8),
          _PreviewCard(
            preview: _preview,
            loading: _loadingPreview,
            error: _error,
            onRetry: _loadPreview,
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: const Icon(Icons.flash_on_outlined),
              title: const Text('解题反馈：每题即时'),
              subtitle: const Text('提交后立刻显示对错与解析；统一解析模式后续开放。'),
              trailing: Text(
                '固定',
                style: theme.textTheme.labelSmall,
              ),
            ),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: (_preview == null || _preview!.count == 0)
                ? null
                : _start,
            icon: const Icon(Icons.play_arrow),
            label: const Text('开始练习'),
          ),
        ],
      ),
    );
  }

  Widget _sectionTitle(String text) {
    return Text(text, style: Theme.of(context).textTheme.titleMedium);
  }
}

class _ScopeOption {
  const _ScopeOption(this.type, this.ids, this.label);

  final String type;
  final List<int> ids;
  final String label;
}

class _PreviewCard extends StatelessWidget {
  const _PreviewCard({
    required this.preview,
    required this.loading,
    required this.error,
    required this.onRetry,
  });

  final PracticePreview? preview;
  final bool loading;
  final String? error;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (loading) {
      return const Card(
        child: SizedBox(
          height: 96,
          child: Center(child: CircularProgressIndicator()),
        ),
      );
    }
    if (error != null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(error!, style: TextStyle(color: theme.colorScheme.error)),
              const SizedBox(height: 8),
              TextButton(onPressed: onRetry, child: const Text('重新预览')),
            ],
          ),
        ),
      );
    }
    final data = preview;
    if (data == null) return const SizedBox.shrink();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  '${data.count} 题',
                  style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: theme.colorScheme.primary,
                  ),
                ),
                const SizedBox(width: 12),
                Text(
                  '预计 ${data.estimatedMinutes} 分钟',
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '知识点覆盖 ${data.coveredKpCount}/${data.rangeKpCount}'
              '（${(data.kpCoverage * 100).round()}%）'
              ' · 到期错题 ${data.dueReviewCount} 道',
              style: theme.textTheme.bodySmall,
            ),
            if (data.insufficient) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.orange.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '该范围可用题目仅 ${data.available} 道，实际将出 ${data.count} 道。',
                  style: theme.textTheme.bodySmall?.copyWith(color: Colors.orange),
                ),
              ),
            ],
            if (data.qTypeMix.isNotEmpty) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: data.qTypeMix.entries
                    .map(
                      (entry) => Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 3,
                        ),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Text(
                          '${_typeLabel(entry.key)} ${entry.value}',
                          style: theme.textTheme.labelSmall,
                        ),
                      ),
                    )
                    .toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _typeLabel(String type) {
    switch (type) {
      case 'multiple':
        return '多选';
      case 'fill':
        return '填空';
      case 'judge':
        return '判断';
      default:
        return '单选';
    }
  }
}
