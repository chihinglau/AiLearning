import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 考试报告：总分、题型/知识点得分、错题清单与下一步建议。
class ExamReportPage extends ConsumerStatefulWidget {
  const ExamReportPage({super.key, required this.attemptId});

  final int attemptId;

  @override
  ConsumerState<ExamReportPage> createState() => _ExamReportPageState();
}

class _ExamReportPageState extends ConsumerState<ExamReportPage> {
  ExamReport? _report;
  bool _loading = true;
  String? _error;
  bool _submitting = false;
  final Map<int, double> _scores = {};

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
      final report = await ref.read(examServiceProvider).report(widget.attemptId);
      if (!mounted) return;
      setState(() {
        _report = report;
        _scores
          ..clear()
          ..addEntries(
            report.pendingSubjective.map(
              (item) => MapEntry(item.questionId, item.selfScore ?? 0.0),
            ),
          );
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

  void _onAction(ExamNextAction action) {
    switch (action.action) {
      case 'weak_practice':
        final ids = action.knowledgePointIds.join(',');
        if (ids.isEmpty) return;
        context.push(
          '/practice/config?scope=kp&ids=$ids'
          '&title=${Uri.encodeComponent('薄弱点专项练习')}',
        );
      case 'wrong_review':
        context.go('/shell?tab=1');
      case 'retake':
        final report = _report;
        if (report != null) {
          context.push('/exam/${report.examId}');
        }
      default:
        break;
    }
  }

  Future<void> _submitSelfAssess() async {
    final report = _report;
    if (report == null || report.pendingSubjective.isEmpty || _submitting) {
      return;
    }
    setState(() => _submitting = true);
    try {
      await ref.read(examServiceProvider).selfAssess(
        widget.attemptId,
        Map<int, double>.of(_scores),
      );
      if (!mounted) return;
      setState(() => _submitting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('自评已提交，成绩与学情已更新')),
      );
      await _load();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _submitting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(ApiErrorGuide.from(error).message)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('考试报告')),
      body: _buildBody(context),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    final theme = Theme.of(context);
    final report = _report;
    if (_error != null || report == null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(
                _error ?? '报告加载失败',
                textAlign: TextAlign.center,
                style: TextStyle(color: theme.colorScheme.error),
              ),
            ),
            const SizedBox(height: 12),
            FilledButton(onPressed: _load, child: const Text('重试')),
          ],
        ),
      );
    }

    final score = report.totalScore ?? report.objectiveScore;
    final rate = report.fullScore == 0 ? 0.0 : score / report.fullScore;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Text(report.examTitle, style: theme.textTheme.titleMedium),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      score.round().toString(),
                      style: theme.textTheme.displaySmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: theme.colorScheme.primary,
                      ),
                    ),
                    Text(
                      ' / ${report.fullScore.round()} 分',
                      style: theme.textTheme.titleMedium,
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  '得分率 ${(rate * 100).round()}%'
                  '${report.status == 'grading' ? ' · 主观题待批改' : ''}',
                  style: theme.textTheme.bodySmall,
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _Stat(label: '正确率', value: '${(report.accuracy * 100).round()}%'),
                    _Stat(
                      label: '答对',
                      value: '${report.correctCount}/${report.questionCount}',
                    ),
                    _Stat(label: '已答', value: '${report.answeredCount}'),
                    _Stat(label: '用时', value: _durationLabel(report.durationMs)),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        if (report.pendingSubjective.isNotEmpty) ...[
          _SectionTitle('主观题自评（${report.pendingSubjective.length}）'),
          const SizedBox(height: 4),
          Text(
            '对照参考答案与评分点给自己打分，提交后计入总分并回写学情',
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: 8),
          for (final item in report.pendingSubjective)
            _subjectiveCard(theme, item),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: _submitting ? null : _submitSelfAssess,
            child: _submitting
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('提交自评'),
          ),
          const SizedBox(height: 16),
        ],
        _SectionTitle('题型得分'),
        const SizedBox(height: 8),
        Card(
          child: Column(
            children: [
              for (final stat in report.typeStats)
                ListTile(
                  dense: true,
                  title: Text(_typeLabel(stat.qType)),
                  subtitle: LinearProgressIndicator(
                    value: stat.scoreRate,
                    minHeight: 6,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  trailing: Text(
                    '${stat.score.round()}/${stat.fullScore.round()}',
                    style: theme.textTheme.titleSmall,
                  ),
                ),
            ],
          ),
        ),
        if (report.kpStats.isNotEmpty) ...[
          const SizedBox(height: 16),
          _SectionTitle('知识点表现'),
          const SizedBox(height: 8),
          Card(
            child: Column(
              children: [
                for (final stat in report.kpStats)
                  ListTile(
                    dense: true,
                    title: Text(
                      stat.name,
                      style: stat.knowledgePointId == null
                          ? null
                          : const TextStyle(decoration: TextDecoration.underline),
                    ),
                    subtitle: Text(
                      '答对 ${stat.correct}/${stat.questionCount}'
                      ' · 得分 ${stat.score.round()}/${stat.fullScore.round()}',
                    ),
                    trailing: Text(
                      '${(stat.scoreRate * 100).round()}%',
                      style: theme.textTheme.titleSmall?.copyWith(
                        color: stat.scoreRate >= 0.6
                            ? Colors.green.shade700
                            : theme.colorScheme.error,
                      ),
                    ),
                    onTap: stat.knowledgePointId == null
                        ? null
                        : () => context.push('/kp/${stat.knowledgePointId}'),
                  ),
              ],
            ),
          ),
        ],
        if (report.wrongQuestions.isNotEmpty) ...[
          const SizedBox(height: 16),
          _SectionTitle('错题清单（${report.wrongQuestions.length}）'),
          const SizedBox(height: 8),
          for (final item in report.wrongQuestions)
            Card(
              child: ExpansionTile(
                title: Text(item.stem, maxLines: 2, overflow: TextOverflow.ellipsis),
                subtitle: Text(
                  '${_typeLabel(item.qType)} · 得分 ${item.score.round()}/${item.fullScore.round()}',
                ),
                childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text('你的答案：${_answerText(item.userAnswer)}'),
                  ),
                  const SizedBox(height: 4),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Text('正确答案：${_answerText(item.correctAnswer)}'),
                  ),
                  if (item.analysis != null && item.analysis!.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        '解析：${item.analysis!}',
                        style: theme.textTheme.bodySmall,
                      ),
                    ),
                  ],
                ],
              ),
            ),
        ],
        if (report.nextActions.isNotEmpty) ...[
          const SizedBox(height: 20),
          _SectionTitle('下一步'),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final action in report.nextActions)
                FilledButton.tonal(
                  onPressed: () => _onAction(action),
                  child: Text(action.label),
                ),
            ],
          ),
        ],
        const SizedBox(height: 20),
        OutlinedButton(
          onPressed: () => context.go('/exams'),
          child: const Text('返回考试中心'),
        ),
        TextButton(
          onPressed: () => context.go('/shell'),
          child: const Text('返回主页'),
        ),
      ],
    );
  }

  Widget _subjectiveCard(ThemeData theme, ExamSubjectiveQuestion item) {
    final max = item.fullScore > 0 ? item.fullScore : 1.0;
    final value = (_scores[item.questionId] ?? 0.0).clamp(0.0, max).toDouble();
    final divisions = max > 1 ? max.round() : 1;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(item.stem, style: theme.textTheme.titleSmall),
            const SizedBox(height: 8),
            Text('你的答案：${item.userAnswerText}'),
            const SizedBox(height: 2),
            Text('参考答案：${item.referenceAnswerText}'),
            if (item.scoringPoints.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('评分点', style: theme.textTheme.labelLarge),
              for (final point in item.scoringPoints)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text('· $point', style: theme.textTheme.bodySmall),
                ),
            ],
            if (item.analysis != null && item.analysis!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('解析：${item.analysis!}', style: theme.textTheme.bodySmall),
            ],
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Slider(
                    value: value,
                    max: max,
                    divisions: divisions,
                    label: '${value.round()} 分',
                    onChanged: _submitting
                        ? null
                        : (next) => setState(
                            () => _scores[item.questionId] = next,
                          ),
                  ),
                ),
                Text('${value.round()} / ${item.fullScore.round()}'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _durationLabel(int durationMs) {
    if (durationMs <= 0) return '-';
    final minute = (durationMs / 60000).ceil();
    return '$minute 分钟';
  }

  String _answerText(Map<String, dynamic>? answer) {
    final value = answer?['value'];
    if (value == null) return '未作答';
    if (value is List) return value.map((item) => item.toString()).join('、');
    return value.toString();
  }

  String _typeLabel(String type) {
    switch (type) {
      case 'multiple':
        return '多选题';
      case 'judge':
        return '判断题';
      case 'fill':
        return '填空题';
      case 'calc':
        return '计算题';
      case 'answer':
        return '解答题';
      case 'listen':
        return '听力题';
      default:
        return '单选题';
    }
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(text, style: Theme.of(context).textTheme.titleMedium);
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      children: [
        Text(
          value,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 2),
        Text(label, style: theme.textTheme.labelSmall),
      ],
    );
  }
}
