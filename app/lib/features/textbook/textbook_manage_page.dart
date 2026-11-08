import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/textbook_binding.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/theme/app_accents.dart';
import 'package:ai_learning/widgets/accent_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 教材管理（D-04 §5.2）：按学科/学期切换版本、推荐标识、年级冲突二次确认、解绑。
class TextbookManagePage extends ConsumerStatefulWidget {
  const TextbookManagePage({super.key});

  @override
  ConsumerState<TextbookManagePage> createState() => _TextbookManagePageState();
}

class _TextbookManagePageState extends ConsumerState<TextbookManagePage> {
  List<TextbookBinding> _bindings = const [];
  TextbookRecommendation? _recommendation;
  List<Textbook> _candidates = const [];
  bool _loading = true;
  bool _loadingCandidates = false;
  bool _submitting = false;
  String? _error;
  String _subject = '';
  String _semester = 'first';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final user = ref.read(currentUserProvider);
    if (user?.isStudent != true) {
      setState(() {
        _loading = false;
        _error = '仅学生账号可管理教材绑定';
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final bindings = await ref.read(textbookServiceProvider).listBindings();
      final recommendation = await ref
          .read(textbookServiceProvider)
          .recommend();
      if (!mounted) return;
      setState(() {
        _bindings = bindings;
        _recommendation = recommendation;
        _semester = recommendation.semester;
        final subjects = _subjects;
        if (_subject.isEmpty || !subjects.contains(_subject)) {
          _subject = subjects.isEmpty ? '' : subjects.first;
        }
        _loading = false;
      });
      await _loadCandidates();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loading = false;
      });
    }
  }

  /// 可管理学科：推荐学科在前，已绑定学科补全。
  List<String> get _subjects {
    final list = <String>[];
    for (final item
        in _recommendation?.subjects ?? const <RecommendedSubject>[]) {
      if (!list.contains(item.subject)) list.add(item.subject);
    }
    for (final binding in _bindings) {
      if (!list.contains(binding.subject)) list.add(binding.subject);
    }
    return list;
  }

  Future<void> _loadCandidates() async {
    final subject = _subject;
    if (subject.isEmpty) return;
    setState(() {
      _loadingCandidates = true;
      _error = null;
    });
    try {
      final textbooks = await ref
          .read(contentServiceProvider)
          .textbooks(subject: subject);
      if (!mounted) return;
      setState(() {
        _candidates =
            textbooks.where((item) => item.semester == _semester).toList()
              ..sort((a, b) {
                final byGrade = a.grade.compareTo(b.grade);
                return byGrade != 0 ? byGrade : a.version.compareTo(b.version);
              });
        _loadingCandidates = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loadingCandidates = false;
      });
    }
  }

  Future<void> _reloadBindings() async {
    final bindings = await ref.read(textbookServiceProvider).listBindings();
    if (!mounted) return;
    setState(() => _bindings = bindings);
  }

  void _selectSubject(String subject) {
    if (subject == _subject) return;
    setState(() => _subject = subject);
    _loadCandidates();
  }

  void _selectSemester(String semester) {
    if (semester == _semester) return;
    setState(() => _semester = semester);
    _loadCandidates();
  }

  /// 当前学期生效绑定（兼容旧数据：回退到该学科任一有效绑定）。
  TextbookBinding? get _currentBinding {
    for (final binding in _bindings) {
      if (binding.subject == _subject && binding.semester == _semester) {
        return binding;
      }
    }
    for (final binding in _bindings) {
      if (binding.subject == _subject) return binding;
    }
    return null;
  }

  int? get _recommendedId {
    for (final item
        in _recommendation?.subjects ?? const <RecommendedSubject>[]) {
      if (item.subject == _subject) return item.textbookId;
    }
    return null;
  }

  Future<bool> _confirm({
    required String title,
    required String content,
    required String confirmLabel,
  }) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(title),
        content: Text(content),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: Text(confirmLabel),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  Future<void> _bindTextbook(Textbook textbook) async {
    if (_submitting) return;
    final current = _currentBinding;
    if (current?.textbook.id == textbook.id) return;
    final user = ref.read(currentUserProvider);
    if (user?.grade != null && textbook.grade != user!.grade) {
      final confirmed = await _confirm(
        title: '确认使用该教材？',
        content:
            '所选教材为 ${textbook.grade} 年级，与你的 ${user.grade} 年级不一致，'
            '仅建议在补课或预习场景下使用。',
        confirmLabel: '确认使用',
      );
      if (!confirmed) return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await ref
          .read(textbookServiceProvider)
          .bind(subject: _subject, textbookId: textbook.id);
      await _reloadBindings();
      if (!mounted) return;
      setState(() => _submitting = false);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('已切换为 ${textbook.displayName}')));
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = ApiErrorGuide.from(error).message;
      });
    }
  }

  Future<void> _unbind(TextbookBinding binding) async {
    if (_submitting) return;
    final confirmed = await _confirm(
      title: '解绑该教材？',
      content: '解绑后「${binding.textbook.displayName}」的学习入口将隐藏，历史学习数据保留。',
      confirmLabel: '解绑',
    );
    if (!confirmed) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await ref.read(textbookServiceProvider).unbind(binding.id);
      await _reloadBindings();
      if (!mounted) return;
      setState(() => _submitting = false);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('已解绑该教材')));
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = ApiErrorGuide.from(error).message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final user = ref.watch(currentUserProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('教材管理')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Text(
                    '按学科管理当前使用的教材，切换后首页、练习与考试范围立即生效。',
                    style: theme.textTheme.bodySmall,
                  ),
                  const SizedBox(height: 12),
                  if (_error != null) ...[
                    Card(
                      color: theme.colorScheme.errorContainer,
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Text(
                          _error!,
                          style: TextStyle(color: theme.colorScheme.error),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                  ],
                  if (_subjects.isEmpty)
                    const Card(
                      child: Padding(
                        padding: EdgeInsets.all(16),
                        child: Text('暂无可用学科教材，请先完善年级信息。'),
                      ),
                    )
                  else ...[
                    _SectionTitle('学科'),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: _subjects
                          .map(
                            (subject) => ChoiceChip(
                              label: Text(Subject.fromCode(subject).label),
                              selected: _subject == subject,
                              onSelected: (_) => _selectSubject(subject),
                            ),
                          )
                          .toList(),
                    ),
                    const SizedBox(height: 20),
                    _SectionTitle('学期'),
                    const SizedBox(height: 8),
                    SegmentedButton<String>(
                      segments: const [
                        ButtonSegment(value: 'first', label: Text('上册')),
                        ButtonSegment(value: 'second', label: Text('下册')),
                      ],
                      selected: {_semester},
                      onSelectionChanged: (selection) =>
                          _selectSemester(selection.first),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '上下册不会同时生效，切换学期即切换该学科当前教材。',
                      style: theme.textTheme.bodySmall,
                    ),
                    const SizedBox(height: 20),
                    _SectionTitle('当前教材'),
                    const SizedBox(height: 8),
                    _CurrentBindingCard(
                      binding: _currentBinding,
                      submitting: _submitting,
                      onUnbind: _currentBinding == null
                          ? null
                          : () => _unbind(_currentBinding!),
                    ),
                    const SizedBox(height: 20),
                    _SectionTitle('版本选择'),
                    const SizedBox(height: 4),
                    Text(
                      '推荐版本按深圳本地化规则优先，可切换其他版本。',
                      style: theme.textTheme.bodySmall,
                    ),
                    const SizedBox(height: 8),
                    if (_loadingCandidates)
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 24),
                        child: Center(child: CircularProgressIndicator()),
                      )
                    else if (_candidates.isEmpty)
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Text(
                            '该学科本学期暂无教材，敬请期待；可切换学科或学期查看其他教材。',
                            style: theme.textTheme.bodyMedium,
                          ),
                        ),
                      )
                    else
                      ..._candidates.map(
                        (textbook) => _VersionTile(
                          textbook: textbook,
                          recommendedId: _recommendedId,
                          currentTextbookId: _currentBinding?.textbook.id,
                          userGrade: user?.grade,
                          submitting: _submitting,
                          onUse: () => _bindTextbook(textbook),
                        ),
                      ),
                  ],
                ],
              ),
      ),
    );
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

class _CurrentBindingCard extends StatelessWidget {
  const _CurrentBindingCard({
    required this.binding,
    required this.submitting,
    required this.onUnbind,
  });

  final TextbookBinding? binding;
  final bool submitting;
  final VoidCallback? onUnbind;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final current = binding;
    if (current == null) {
      return AccentCard(
        accent: AppAccents.of(context).learn,
        padding: const EdgeInsets.all(16),
        child: Text(
          '该学科本学期尚未绑定教材，请选择下方版本使用。',
          style: theme.textTheme.bodyMedium,
        ),
      );
    }
    return AccentCard(
      accent: AppAccents.of(context).learn,
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: theme.colorScheme.primaryContainer,
          child: Icon(
            current.source == 'manual' ? Icons.tune : Icons.auto_awesome,
            color: theme.colorScheme.primary,
          ),
        ),
        title: Text(current.textbook.displayName),
        subtitle: Text(
          '来源：${current.source == 'manual' ? '手动选择' : '自动绑定'}'
          ' · ${current.semester == 'second' ? '下册' : '上册'}'
          '${current.mismatch ? ' · 年级不一致' : ''}',
        ),
        trailing: TextButton(
          onPressed: submitting ? null : onUnbind,
          child: const Text('解绑'),
        ),
      ),
    );
  }
}

class _VersionTile extends StatelessWidget {
  const _VersionTile({
    required this.textbook,
    required this.recommendedId,
    required this.currentTextbookId,
    required this.userGrade,
    required this.submitting,
    required this.onUse,
  });

  final Textbook textbook;
  final int? recommendedId;
  final int? currentTextbookId;
  final int? userGrade;
  final bool submitting;
  final VoidCallback onUse;

  bool get _isCurrent => currentTextbookId == textbook.id;

  bool get _isRecommended => recommendedId == textbook.id;

  bool get _gradeMismatch => userGrade != null && textbook.grade != userGrade;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accents = AppAccents.of(context);
    return AccentCard(
      accent: _isCurrent ? accents.learn : accents.practice,
      child: ListTile(
        title: Wrap(
          spacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(textbook.version),
            if (_isRecommended) const _Badge('推荐', tone: _BadgeTone.primary),
            if (_gradeMismatch) const _Badge('年级不一致', tone: _BadgeTone.error),
            if (_isCurrent) const _Badge('使用中', tone: _BadgeTone.success),
          ],
        ),
        subtitle: Text('${textbook.grade} 年级 · ${textbook.semesterLabel}'),
        trailing: _isCurrent
            ? Icon(Icons.check_circle, color: theme.colorScheme.primary)
            : TextButton(
                onPressed: submitting ? null : onUse,
                child: const Text('使用'),
              ),
      ),
    );
  }
}

enum _BadgeTone { primary, error, success }

class _Badge extends StatelessWidget {
  const _Badge(this.text, {required this.tone});

  final String text;
  final _BadgeTone tone;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = switch (tone) {
      _BadgeTone.primary => theme.colorScheme.primary,
      _BadgeTone.error => theme.colorScheme.error,
      _BadgeTone.success => AppAccents.of(context).learn,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        border: Border.all(color: color),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        text,
        style: theme.textTheme.labelSmall?.copyWith(color: color),
      ),
    );
  }
}
