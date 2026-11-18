import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 报告历史（D-09 §4.7 / EX-08）：本人历次作答，按时间倒序，可直达报告页。
class ExamHistoryPage extends ConsumerStatefulWidget {
  const ExamHistoryPage({super.key, this.examId});

  final int? examId;

  @override
  ConsumerState<ExamHistoryPage> createState() => _ExamHistoryPageState();
}

class _ExamHistoryPageState extends ConsumerState<ExamHistoryPage> {
  List<ExamAttemptHistory> _items = const [];
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
      final items = await ref
          .read(examServiceProvider)
          .attemptHistory(examId: widget.examId);
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
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('报告历史')),
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
            else if (_items.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 48),
                child: Center(child: Text('暂无历史报告')),
              )
            else
              for (final item in _items) ...[
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.assessment_outlined),
                    title: Text(item.examTitle),
                    subtitle: Text(
                      '${item.status == 'in_progress' ? '进行中' : '已交卷'}'
                      '${item.totalScore == null ? '' : ' · ${item.totalScore!.round()} 分'}'
                      ' · ${_formatDate(item.startedAt)}',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.push(item.route),
                  ),
                ),
                const SizedBox(height: 8),
              ],
          ],
        ),
      ),
    );
  }

  static String _formatDate(DateTime value) {
    final local = value.toLocal();
    String two(int number) => number.toString().padLeft(2, '0');
    return '${local.year}-${two(local.month)}-${two(local.day)} '
        '${two(local.hour)}:${two(local.minute)}';
  }
}
