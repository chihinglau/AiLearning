import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 真题详情/预览（D-09 §5.5 / EX-08）：只展示溯源与卷面信息，不含答案。
class PastPaperDetailPage extends ConsumerStatefulWidget {
  const PastPaperDetailPage({super.key, required this.paperId});

  final int paperId;

  @override
  ConsumerState<PastPaperDetailPage> createState() =>
      _PastPaperDetailPageState();
}

class _PastPaperDetailPageState extends ConsumerState<PastPaperDetailPage> {
  PastPaperDetail? _detail;
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
      final detail = await ref
          .read(examServiceProvider)
          .pastPaperDetail(widget.paperId);
      if (!mounted) return;
      setState(() {
        _detail = detail;
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('真题来源详情')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
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
            else if (_detail != null)
              _DetailCard(detail: _detail!),
          ],
        ),
      ),
    );
  }
}

class _DetailCard extends StatelessWidget {
  const _DetailCard({required this.detail});

  final PastPaperDetail detail;

  @override
  Widget build(BuildContext context) {
    final summary = detail.summary;
    final rows = <(String, String)>[
      ('试卷标题', summary.title),
      ('年份', summary.year == null ? '未标注' : '${summary.year}'),
      ('地区', summary.region ?? '未标注'),
      ('年级', '${summary.grade} 年级'),
      ('题型', summary.typeLabel),
      ('卷面', '${summary.questionCount} 题 · 满分 ${summary.totalScore} · '
          '限时 ${summary.timeLimitMin} 分钟'),
      ('来源名称', summary.sourceLabel),
      ('授权说明', summary.licenseNote ?? '未登记'),
      ('改编来源', summary.adaptedFrom ?? '无（非改编）'),
      ('来源类型', detail.source),
      ('本人作答次数', '${detail.attemptCount}'),
    ];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '题源与授权留痕（D-08 合规红线 / R-07 台账）',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 12),
            for (final row in rows)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 96,
                      child: Text(
                        row.$1,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                    Expanded(child: Text(row.$2)),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
