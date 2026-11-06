import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:ai_learning/core/models/textbook_binding.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 3 步年级引导：学段 → 年级 → 教材确认。
class OnboardingPage extends ConsumerStatefulWidget {
  const OnboardingPage({super.key});

  @override
  ConsumerState<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends ConsumerState<OnboardingPage> {
  int _step = 0;
  Stage _stage = Stage.primary;
  int _grade = 1;
  TextbookRecommendation? _recommendation;
  bool _loadingRecommendation = false;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final user = ref.read(currentUserProvider);
    _grade = user?.grade ?? 1;
    _stage = Stage.fromCode(user?.stage) ?? stageForGrade(_grade);
  }

  void _selectStage(Stage stage) {
    setState(() {
      _stage = stage;
      final grades = gradesForStage(stage);
      if (!grades.contains(_grade)) {
        _grade = grades.first;
      }
    });
  }

  Future<bool> _confirmImpact(String? message) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('确认修改年级？'),
        content: Text(message ?? '修改年级将影响教材绑定、练习范围与推荐，历史学情保留。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('确认修改'),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  Future<bool> _applyGradeIfNeeded() async {
    final user = ref.read(currentUserProvider);
    if (user == null || user.grade == _grade) return true;
    try {
      var outcome = await ref.read(userServiceProvider).changeGrade(_grade);
      if (outcome.requiresConfirm) {
        if (!mounted) return false;
        final confirmed = await _confirmImpact(outcome.impactMessage);
        if (!confirmed) return false;
        outcome = await ref.read(userServiceProvider).changeGrade(
          _grade,
          confirmToken: outcome.confirmToken,
        );
      }
      if (!mounted) return false;
      ref.read(currentUserProvider.notifier).state = user.copyWith(
        grade: outcome.grade ?? _grade,
        stage: outcome.stage ?? _stage.code,
      );
      return true;
    } on ApiException catch (error) {
      if (!mounted) return false;
      setState(() => _error = error.message);
      return false;
    }
  }

  Future<void> _loadRecommendation() async {
    setState(() {
      _step = 2;
      _loadingRecommendation = true;
      _error = null;
    });
    try {
      final recommendation =
          await ref.read(textbookServiceProvider).recommend();
      if (!mounted) return;
      setState(() {
        _recommendation = recommendation;
        _loadingRecommendation = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _loadingRecommendation = false;
        _error = error.message;
      });
    }
  }

  Future<void> _next() async {
    setState(() => _error = null);
    if (_step == 0) {
      setState(() => _step = 1);
      return;
    }
    if (_step == 1) {
      setState(() => _submitting = true);
      final applied = await _applyGradeIfNeeded();
      if (!mounted) return;
      if (!applied) {
        setState(() => _submitting = false);
        return;
      }
      setState(() => _submitting = false);
      await _loadRecommendation();
    }
  }

  Future<void> _finish() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await ref.read(textbookServiceProvider).autoBind();
      if (!mounted) return;
      ref.read(onboardingStatusProvider.notifier).state =
          OnboardingStatus.completed;
      context.go('/shell');
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = error.message;
      });
    }
  }

  void _back() {
    if (_step == 0) return;
    setState(() => _step -= 1);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('完善学习信息'),
        automaticallyImplyLeading: false,
      ),
      body: SafeArea(
        child: Column(
          children: [
            LinearProgressIndicator(value: (_step + 1) / 3),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
              child: Row(
                children: [
                  Text(
                    '第 ${_step + 1} 步 / 共 3 步',
                    style: theme.textTheme.bodySmall,
                  ),
                  const Spacer(),
                  Text(
                    switch (_step) {
                      0 => '选择学段',
                      1 => '选择年级',
                      _ => '确认教材',
                    },
                    style: theme.textTheme.titleSmall,
                  ),
                ],
              ),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: switch (_step) {
                  0 => _buildStageStep(theme),
                  1 => _buildGradeStep(theme),
                  _ => _buildTextbookStep(theme),
                },
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Text(
                  _error!,
                  style: TextStyle(color: theme.colorScheme.error),
                ),
              ),
            Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  if (_step > 0)
                    OutlinedButton(
                      onPressed: _submitting ? null : _back,
                      child: const Text('上一步'),
                    ),
                  if (_step > 0) const SizedBox(width: 12),
                  Expanded(
                    child: FilledButton(
                      onPressed: _submitting
                          ? null
                          : (_step == 2 ? _finish : _next),
                      child: _submitting
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : Text(_step == 2 ? '完成并开始学习' : '下一步'),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStageStep(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('你的学段', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        Text(
          '选择后可为你匹配对应年级的教材与练习范围',
          style: theme.textTheme.bodySmall,
        ),
        const SizedBox(height: 16),
        ...Stage.values.map(
          (stage) => Card(
            color: _stage == stage ? theme.colorScheme.primaryContainer : null,
            child: ListTile(
              leading: Icon(
                switch (stage) {
                  Stage.primary => Icons.child_care_outlined,
                  Stage.junior => Icons.school_outlined,
                  Stage.senior => Icons.workspace_premium_outlined,
                },
              ),
              title: Text(stage.label),
              subtitle: Text(
                '${gradesForStage(stage).first} - ${gradesForStage(stage).last} 年级',
              ),
              trailing: _stage == stage
                  ? const Icon(Icons.check_circle)
                  : const Icon(Icons.chevron_right),
              onTap: () => _selectStage(stage),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildGradeStep(ThemeData theme) {
    final grades = gradesForStage(_stage);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('${_stage.label}年级', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        Text(
          '年级将用于教材推荐与学情统计，每学期仅可修改一次',
          style: theme.textTheme.bodySmall,
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: grades
              .map(
                (grade) => ChoiceChip(
                  label: Text('$grade 年级'),
                  selected: _grade == grade,
                  onSelected: (_) => setState(() => _grade = grade),
                ),
              )
              .toList(),
        ),
      ],
    );
  }

  Widget _buildTextbookStep(ThemeData theme) {
    if (_loadingRecommendation) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 48),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    final recommendation = _recommendation;
    if (recommendation == null || recommendation.subjects.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('教材确认', style: theme.textTheme.titleMedium),
          const SizedBox(height: 12),
          const Text('该年级暂无可推荐教材，可先进入学习页，稍后在教材管理中设置。'),
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('以下教材将自动绑定', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        Text(
          '$_grade 年级 · ${recommendation.region == 'shenzhen' ? '深圳本地化' : recommendation.region}',
          style: theme.textTheme.bodySmall,
        ),
        const SizedBox(height: 16),
        ...recommendation.subjects.map(
          (item) => Card(
            child: ListTile(
              leading: const Icon(Icons.menu_book_outlined),
              title: Text(item.subjectLabel),
              subtitle: Text('$_grade 年级 · ${item.version}'),
              trailing: const Icon(Icons.check),
            ),
          ),
        ),
      ],
    );
  }
}
