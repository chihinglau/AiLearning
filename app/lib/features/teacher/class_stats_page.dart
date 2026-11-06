import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/org.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 班级学情（P1-06）：仅展示聚合值，不含学生个人信息。
class ClassStatsPage extends ConsumerStatefulWidget {
  const ClassStatsPage({
    super.key,
    required this.classId,
    this.className = '班级',
    this.grade,
  });

  final int classId;
  final String className;
  final int? grade;

  @override
  ConsumerState<ClassStatsPage> createState() => _ClassStatsPageState();
}

class _ClassStatsPageState extends ConsumerState<ClassStatsPage> {
  ClassStats? _stats;
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
      final stats = await ref
          .read(orgServiceProvider)
          .classStats(widget.classId);
      if (!mounted) return;
      setState(() {
        _stats = stats;
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
    final stats = _stats;
    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.className} · 班级学情'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () {
            if (context.canPop()) {
              context.pop();
            } else {
              context.go('/teacher/classes');
            }
          },
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (_error != null)
                    Card(
                      color: theme.colorScheme.errorContainer,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Text(_error!, style: theme.textTheme.bodyMedium),
                      ),
                    ),
                  if (stats != null) ...[
                    Card(
                      color: theme.colorScheme.primaryContainer,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(stats.label, style: theme.textTheme.titleMedium),
                            const SizedBox(height: 4),
                            Text(
                              '${stats.subjectLabel} · 仅展示班级聚合数据，不含学生个人信息',
                              style: theme.textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        _StatCard(
                          icon: Icons.groups_outlined,
                          value: '${stats.studentCount}',
                          label: '学生数',
                          color: Colors.blue,
                        ),
                        _StatCard(
                          icon: Icons.online_prediction,
                          value: '${stats.activeStudentCount}',
                          label: '近7日活跃',
                          color: Colors.teal,
                        ),
                      ],
                    ),
                    Row(
                      children: [
                        _StatCard(
                          icon: Icons.verified_outlined,
                          value: stats.accuracyPercent,
                          label: '正确率',
                          color: Colors.green,
                        ),
                        _StatCard(
                          icon: Icons.insights,
                          value: stats.avgMasteryText,
                          label: '平均掌握度',
                          color: Colors.deepOrange,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text('近 7 日提交率', style: theme.textTheme.titleSmall),
                                Text(
                                  stats.submissionRatePercent,
                                  style: theme.textTheme.titleSmall?.copyWith(
                                    color: theme.colorScheme.primary,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: stats.submissionRate.clamp(0, 1),
                                minHeight: 8,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              '累计答题 ${stats.totalAnswered} 道',
                              style: theme.textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text('薄弱知识点 Top5', style: theme.textTheme.titleMedium),
                    const SizedBox(height: 8),
                    if (stats.weakPoints.isEmpty)
                      const Card(
                        child: Padding(
                          padding: EdgeInsets.all(16),
                          child: Text('暂无薄弱知识点，班级掌握度良好。'),
                        ),
                      )
                    else
                      ...stats.weakPoints.map(
                        (point) => Card(
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: theme.colorScheme.errorContainer,
                              child: Text(
                                '${point.avgMastery.round()}',
                                style: theme.textTheme.labelMedium,
                              ),
                            ),
                            title: Text('${point.subjectLabel} · ${point.name}'),
                            subtitle: Text(
                              '班级平均掌握度 ${point.avgMastery}',
                            ),
                          ),
                        ),
                      ),
                  ],
                ],
              ),
            ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.icon,
    required this.value,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String value;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
          child: Column(
            children: [
              Icon(icon, color: color),
              const SizedBox(height: 6),
              Text(
                value,
                style: theme.textTheme.titleLarge
                    ?.copyWith(fontWeight: FontWeight.bold),
              ),
              Text(label, style: theme.textTheme.labelSmall),
            ],
          ),
        ),
      ),
    );
  }
}
