import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/family.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 家长中心（P1-05）：切换孩子、查看学情、设置每日时长与青少年模式。
class ParentChildrenPage extends ConsumerStatefulWidget {
  const ParentChildrenPage({super.key});

  @override
  ConsumerState<ParentChildrenPage> createState() => _ParentChildrenPageState();
}

class _ParentChildrenPageState extends ConsumerState<ParentChildrenPage> {
  List<FamilyChild> _children = const [];
  int _selected = 0;
  LearnStats? _stats;
  bool _loading = true;
  bool _saving = false;
  String? _error;
  int _dailyLimit = 120;
  bool _teenMode = false;

  FamilyChild? get _child =>
      _children.isEmpty ? null : _children[_selected.clamp(0, _children.length - 1)];

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
      final children = await ref.read(familyServiceProvider).children();
      if (!mounted) return;
      setState(() {
        _children = List<FamilyChild>.of(children);
        _selected = 0;
        _syncControls();
        _loading = children.isEmpty ? false : true;
      });
      if (children.isNotEmpty) {
        await _loadStats(children.first);
      }
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loading = false;
      });
    }
  }

  void _syncControls() {
    final child = _child;
    _dailyLimit = child?.dailyLimitMinutes ?? 120;
    _teenMode = child?.teenMode ?? false;
  }

  Future<void> _selectChild(int index) async {
    if (index == _selected || _children.isEmpty) return;
    setState(() {
      _selected = index;
      _stats = null;
      _syncControls();
    });
    await _loadStats(_children[index]);
  }

  Future<void> _loadStats(FamilyChild child) async {
    try {
      final stats = await ref
          .read(learnServiceProvider)
          .stats(studentId: child.id);
      if (!mounted || _child?.id != child.id) return;
      setState(() {
        _stats = stats;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _stats = null;
        _error = ApiErrorGuide.from(error).message;
        _loading = false;
      });
    }
  }

  Future<void> _saveControls() async {
    final child = _child;
    if (child == null) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final updated = await ref.read(familyServiceProvider).updateControls(
            child.id,
            dailyLimitMinutes: _dailyLimit,
            teenMode: _teenMode,
          );
      if (!mounted) return;
      setState(() {
        _children[_selected] = updated;
        _saving = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('已保存家长设置')),
      );
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = ApiErrorGuide.from(error).message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final child = _child;
    return Scaffold(
      appBar: AppBar(
        title: const Text('家长中心'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.canPop() ? context.pop() : context.go('/shell'),
        ),
      ),
      body: RefreshIndicator(
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
            if (child == null && !_loading)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(20),
                  child: Text(
                    '还没有已绑定的孩子。请先在孩子账号中发起绑定，并在家长账号中确认，'
                    '完成后即可在这里查看学情与设置时长。',
                  ),
                ),
              ),
            if (_children.length > 1) ...[
              Wrap(
                spacing: 8,
                children: _children
                    .asMap()
                    .entries
                    .map(
                      (entry) => ChoiceChip(
                        label: Text(entry.value.nickname),
                        selected: entry.key == _selected,
                        onSelected: (_) => _selectChild(entry.key),
                      ),
                    )
                    .toList(),
              ),
              const SizedBox(height: 12),
            ],
            if (child != null) ...[
              Card(
                color: theme.colorScheme.primaryContainer,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 24,
                        backgroundColor: theme.colorScheme.primary,
                        child: const Icon(Icons.child_care, color: Colors.white),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(child.nickname, style: theme.textTheme.titleMedium),
                            const SizedBox(height: 2),
                            Text(child.gradeLabel, style: theme.textTheme.bodySmall),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
              if (_loading)
                const Center(child: Padding(
                  padding: EdgeInsets.all(24),
                  child: CircularProgressIndicator(),
                ))
              else if (_stats != null) ...[
                Row(
                  children: [
                    _StatCard(
                      icon: Icons.local_fire_department_outlined,
                      value: '${_stats!.streakDays}',
                      label: '连续学习(天)',
                      color: Colors.deepOrange,
                    ),
                    _StatCard(
                      icon: Icons.edit_note,
                      value: '${_stats!.totalAnswered}',
                      label: '累计答题',
                      color: Colors.blue,
                    ),
                  ],
                ),
                Row(
                  children: [
                    _StatCard(
                      icon: Icons.verified_outlined,
                      value: _stats!.accuracyPercent,
                      label: '正确率',
                      color: Colors.green,
                    ),
                    _StatCard(
                      icon: Icons.bookmark_border,
                      value: '${_stats!.activeWrongCount}',
                      label: '待消灭错题',
                      color: Colors.redAccent,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text('薄弱知识点', style: theme.textTheme.titleMedium),
                const SizedBox(height: 8),
                if (_stats!.weakPoints.isEmpty)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Text('暂无薄弱知识点，继续保持。'),
                    ),
                  )
                else
                  ..._stats!.weakPoints.take(3).map(
                        (node) => Card(
                          child: ListTile(
                            leading: Icon(
                              Icons.circle,
                              size: 12,
                              color: node.bandColor,
                            ),
                            title: Text('${node.subjectLabel} · ${node.name}'),
                            trailing: Text('${node.masteryScore.round()}'),
                          ),
                        ),
                      ),
              ],
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('家长控制', style: theme.textTheme.titleMedium),
                      const SizedBox(height: 8),
                      Text(
                        '每日学习时长：${_dailyLimit == 0 ? '不限' : '$_dailyLimit 分钟'}',
                        style: theme.textTheme.bodyMedium,
                      ),
                      Slider(
                        value: _dailyLimit.toDouble().clamp(0, 240),
                        min: 0,
                        max: 240,
                        divisions: 8,
                        label: _dailyLimit == 0 ? '不限' : '$_dailyLimit 分钟',
                        onChanged: _saving
                            ? null
                            : (value) => setState(
                                  () => _dailyLimit = (value / 30).round() * 30,
                                ),
                      ),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('青少年模式'),
                        subtitle: const Text('限制夜间使用与不适宜内容'),
                        value: _teenMode,
                        onChanged: _saving
                            ? null
                            : (value) => setState(() => _teenMode = value),
                      ),
                      const SizedBox(height: 8),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: _saving ? null : _saveControls,
                          icon: _saving
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.save_outlined),
                          label: const Text('保存设置'),
                        ),
                      ),
                    ],
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
