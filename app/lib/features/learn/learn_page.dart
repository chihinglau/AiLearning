import 'dart:async';
import 'dart:convert';

import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/exam_entry.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/models/practice_mode.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/theme/app_accents.dart';
import 'package:ai_learning/features/learn/widgets/offline_banner.dart';
import 'package:ai_learning/widgets/accent_card.dart';
import 'package:ai_learning/widgets/feature_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 学习首页：学生走首页聚合（教材 / 今日计划 / 继续学习 / 学科入口 / 考试入口），
/// 家长等非学生账号降级为教材章节浏览。
class LearnPage extends ConsumerWidget {
  const LearnPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    if (user?.isStudent == true) {
      return const _StudentHomeView();
    }
    return const _TextbookBrowseView();
  }
}

class _StudentHomeView extends ConsumerStatefulWidget {
  const _StudentHomeView();

  @override
  ConsumerState<_StudentHomeView> createState() => _StudentHomeViewState();
}

class _StudentHomeViewState extends ConsumerState<_StudentHomeView> {
  HomeData? _home;
  _LastPractice? _lastPractice;
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
      final home = await ref.read(learnServiceProvider).home();
      final lastPractice = await _loadLastPractice();
      if (!mounted) return;
      setState(() {
        _home = home;
        _lastPractice = lastPractice;
        _offline = false;
        _loading = false;
      });
      // 联网后顺带同步离线答题队列。
      unawaited(ref.read(offlineLearnSyncProvider).sync());
    } on ApiException catch (error) {
      if (!mounted) return;
      // 断网时使用上次缓存的首页，保证可进入已下载教材。
      final cached = error.statusCode == null
          ? await ref.read(offlineLearnServiceProvider).cachedHome()
          : null;
      if (!mounted) return;
      setState(() {
        if (cached != null) {
          _home = cached;
          _lastPractice = null;
          _offline = true;
          _error = null;
        } else {
          _error = ApiErrorGuide.from(error).message;
        }
        _loading = false;
      });
    }
  }

  Future<_LastPractice?> _loadLastPractice() async {
    try {
      final raw = await ref
          .read(platformPalProvider)
          .storage
          .read('practice_last_session');
      if (raw == null || raw.isEmpty) return null;
      final data = jsonDecode(raw) as Map<String, dynamic>;
      final total = data['total'] as int? ?? 0;
      final answered = data['answered'] as int? ?? 0;
      if (total <= 0 || answered >= total) return null;
      return _LastPractice(
        id: data['id'] as int? ?? 0,
        title: data['title'] as String? ?? '上次练习',
        total: total,
        answered: answered,
      );
    } catch (_) {
      return null;
    }
  }

  void _openTextbook(HomeTextbook textbook) {
    context.push(
      '/knowledge/${textbook.textbookId}'
      '?name=${Uri.encodeComponent(textbook.subjectLabel)}',
    );
  }

  void _openContinue(HomeData home) {
    final item = home.continueLearning;
    if (item == null) {
      _startDaily();
      return;
    }
    final textbook = home.textbookOf(item.subject);
    if (textbook != null) {
      final chapter = item.chapterId == null
          ? ''
          : '&chapter=${item.chapterId}';
      context.push(
        '/knowledge/${textbook.textbookId}'
        '?name=${Uri.encodeComponent(textbook.subjectLabel)}$chapter',
      );
      return;
    }
    if (item.chapterId != null) {
      context.push(
        '/session?chapter=${item.chapterId}'
        '&title=${Uri.encodeComponent(item.title)}',
      );
      return;
    }
    _startDaily();
  }

  void _startDaily() {
    context.push('/session?title=${Uri.encodeComponent('每日一练')}');
  }

  /// 首页三个练习模式入口：把 mode 传进配置页，由配置页套用各自的默认范围、
  /// 题量与题型，进入后组卷策略也按 mode 区分。
  void _openPracticeMode(String mode) {
    final textbooks = _home?.textbooks ?? const <HomeTextbook>[];
    if (textbooks.isEmpty) return;
    final spec = practiceModeOf(mode);
    context.push(
      '/practice/config?scope=textbook&ids=${textbooks.first.textbookId}'
      '&mode=${spec.key}&title=${Uri.encodeComponent(spec.label)}',
    );
  }

  void _openRecommendation(HomeData home) {
    final rec = home.recommendation;
    switch (rec.action) {
      case 'review':
        context.push('/session?review=1&title=${Uri.encodeComponent('今日复习')}');
      case 'practice':
        if (rec.knowledgePointId != null) {
          context.push(
            '/session?kp=${rec.knowledgePointId}'
            '&title=${Uri.encodeComponent('专项练习')}',
          );
        } else {
          _startDaily();
        }
      case 'continue':
        if (home.continueLearning == null && rec.chapterId != null) {
          context.push(
            '/session?chapter=${rec.chapterId}'
            '&title=${Uri.encodeComponent(rec.chapterName ?? '继续学习')}',
          );
        } else {
          _openContinue(home);
        }
      case 'unit_test':
        if (rec.examId != null) {
          context.push('/exam/${rec.examId}');
        } else {
          context.push('/exams');
        }
      case 'learn_kp':
        final textbook = home.continueLearning == null
            ? (home.textbooks.isEmpty ? null : home.textbooks.first)
            : home.textbookOf(home.continueLearning!.subject) ??
                  (home.textbooks.isEmpty ? null : home.textbooks.first);
        if (textbook != null) {
          _openTextbook(textbook);
        } else {
          _startDaily();
        }
      default:
        _startDaily();
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    final theme = Theme.of(context);
    final accents = AppAccents.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('深爱学 · 学习')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (_offline) const OfflineBanner(),
            _WelcomeHeader(
              nickname: user?.nickname ?? '',
              grade: _home?.grade ?? user?.grade,
              stage: _home?.stageEnum?.label,
              semester: _home?.semester,
            ),
            const SizedBox(height: 16),
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
                      ),
                      const SizedBox(height: 12),
                      FilledButton(onPressed: _load, child: const Text('重试')),
                    ],
                  ),
                ),
              )
            else if (_home != null) ...[
              _RecommendationCard(
                recommendation: _home!.recommendation,
                onTap: () => _openRecommendation(_home!),
              ),
              if (_lastPractice != null) ...[
                const SizedBox(height: 12),
                FeatureCard(
                  icon: Icons.pause_circle_outline,
                  accent: accents.practice,
                  title: '继续「${_lastPractice!.title}」',
                  subtitle:
                      '已完成 ${_lastPractice!.answered}/${_lastPractice!.total} 题',
                  progress: _lastPractice!.total > 0
                      ? _lastPractice!.answered / _lastPractice!.total
                      : null,
                  onTap: () => context.push(
                    '/session?session=${_lastPractice!.id}'
                    '&title=${Uri.encodeComponent(_lastPractice!.title)}',
                  ),
                ),
              ],
              const SizedBox(height: 20),
              _SectionTitle('今日计划'),
              const SizedBox(height: 8),
              _TodayPlanCard(
                plan: _home!.todayPlan,
                onReview: () => context.push(
                  '/session?review=1&title=${Uri.encodeComponent('今日复习')}',
                ),
                onPractice: _startDaily,
              ),
              const SizedBox(height: 20),
              _SectionTitle('练习模式'),
              const SizedBox(height: 4),
              Text(
                '三种模式的组卷策略不同，进入后可再调整范围与题量',
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: 8),
              if (_home!.textbooks.isEmpty)
                const Card(
                  child: ListTile(title: Text('绑定教材后即可开始分模式练习')),
                )
              else
                Row(
                  children: [
                    for (final key in kPracticeModeOrder) ...[
                      Expanded(
                        child: _PracticeModeEntry(
                          spec: practiceModeOf(key),
                          onTap: () => _openPracticeMode(key),
                        ),
                      ),
                      if (key != kPracticeModeOrder.last)
                        const SizedBox(width: 8),
                    ],
                  ],
                ),
              const SizedBox(height: 20),
              if (_home!.continueLearning != null) ...[
                _SectionTitle('继续学习'),
                const SizedBox(height: 8),
                FeatureCard(
                  icon: Icons.play_arrow_rounded,
                  accent: accents.learn,
                  title: _home!.continueLearning!.title,
                  subtitle:
                      '${_home!.continueLearning!.subjectLabel}'
                      '${_home!.continueLearning!.chapterName == null ? '' : ' · ${_home!.continueLearning!.chapterName}'}',
                  onTap: () => _openContinue(_home!),
                ),
                const SizedBox(height: 20),
              ],
              if (_home!.needsBinding) ...[
                _SectionTitle('教材推荐'),
                const SizedBox(height: 4),
                Text('还没有绑定教材，先完成教材选择再开始学习', style: theme.textTheme.bodySmall),
                const SizedBox(height: 8),
                if (_home!.recommended.isEmpty)
                  const Card(child: ListTile(title: Text('暂无推荐教材')))
                else
                  for (final textbook in _home!.recommended)
                    _TextbookTile(
                      textbook: textbook,
                      onTap: () => context.push('/gate'),
                    ),
                const SizedBox(height: 8),
                FilledButton.icon(
                  onPressed: () => context.push('/gate'),
                  icon: const Icon(Icons.link),
                  label: const Text('去绑定教材'),
                ),
                const SizedBox(height: 20),
              ] else ...[
                _SectionTitle('学科入口'),
                const SizedBox(height: 8),
                for (final textbook in _home!.textbooks)
                  _TextbookTile(
                    textbook: textbook,
                    onTap: () => _openTextbook(textbook),
                  ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () => context.push('/textbooks'),
                    icon: const Icon(Icons.tune),
                    label: const Text('管理教材'),
                  ),
                ),
                const SizedBox(height: 20),
              ],
              _SectionTitle('待办考试'),
              const SizedBox(height: 8),
              if (_home!.pendingExams.isEmpty)
                const Card(
                  child: ListTile(
                    leading: Icon(Icons.event_available_outlined),
                    title: Text('暂无待考考试'),
                    subtitle: Text('新发布的考试会出现在这里'),
                  ),
                )
              else
                for (final item in _home!.pendingExams.take(3))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: FeatureCard(
                      icon: Icons.event_note_outlined,
                      accent: accents.exam,
                      title: item['title']?.toString() ?? '待办考试',
                      subtitle: pendingExamSubtitle(item),
                      onTap: () {
                        final route = pendingExamRoute(item);
                        if (route == null) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('考试窗口已关闭，暂无法进入'),
                            ),
                          );
                          return;
                        }
                        if (item['window_state'] == 'scheduled') {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('考试尚未开始，可先查看试卷信息'),
                            ),
                          );
                        }
                        context.push(route);
                      },
                    ),
                  ),
              const SizedBox(height: 20),
              _SectionTitle('考试入口'),
              const SizedBox(height: 8),
              FeatureCard(
                icon: Icons.assignment_outlined,
                accent: accents.exam,
                title: '考试中心',
                subtitle: _home!.pendingExams.isEmpty
                    ? '暂无待考考试，可查看全部考试'
                    : '${_home!.pendingExams.length} 场考试待完成',
                onTap: () => context.push('/exams'),
              ),
              const SizedBox(height: 8),
              FeatureCard(
                icon: Icons.history_edu_outlined,
                accent: accents.exam,
                title: '真题库',
                subtitle: '按学科、年份与地区查看历年真题',
                onTap: () => context.push('/past-papers'),
              ),
              const SizedBox(height: 8),
              FeatureCard(
                icon: Icons.edit_document,
                accent: accents.assignment,
                title: '班级作业',
                subtitle: '查看老师布置的统一作业与批改结果',
                onTap: () => context.push('/assignments'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _PracticeModeEntry extends StatelessWidget {
  const _PracticeModeEntry({required this.spec, required this.onTap});

  final PracticeModeSpec spec;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final icon = switch (spec.key) {
      'sync' => Icons.menu_book_outlined,
      'pre_exam' => Icons.timer_outlined,
      _ => Icons.gps_fixed_outlined,
    };
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 6),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 24, color: theme.colorScheme.primary),
              const SizedBox(height: 8),
              Text(
                spec.label,
                textAlign: TextAlign.center,
                style: theme.textTheme.labelLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                spec.tagline,
                textAlign: TextAlign.center,
                style: theme.textTheme.labelSmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _WelcomeHeader extends StatelessWidget {
  const _WelcomeHeader({
    required this.nickname,
    required this.grade,
    required this.stage,
    required this.semester,
  });

  final String nickname;
  final int? grade;
  final String? stage;
  final String? semester;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final gradeText = [
      if (stage != null && stage!.isNotEmpty) stage!,
      if (grade != null) '$grade 年级',
    ].join(' · ');
    return Card(
      color: theme.colorScheme.primaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: theme.colorScheme.primary,
              child: const Icon(Icons.person, color: Colors.white),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    nickname.isEmpty ? '同学你好' : '你好，$nickname',
                    style: theme.textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${gradeText.isEmpty ? '深圳本地化教材已就绪' : gradeText}'
                    '${semester == null ? '' : ' · ${_semesterLabel(semester!)}'}',
                    style: theme.textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({
    required this.recommendation,
    required this.onTap,
  });

  final HomeRecommendation recommendation;
  final VoidCallback onTap;

  IconData get _icon {
    switch (recommendation.action) {
      case 'review':
        return Icons.replay_circle_filled_outlined;
      case 'learn_kp':
        return Icons.lightbulb_outline;
      case 'practice':
        return Icons.fitness_center;
      case 'continue':
        return Icons.play_circle_outline;
      case 'unit_test':
        return Icons.assignment_outlined;
      default:
        return Icons.bolt_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      color: theme.colorScheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(_icon, size: 32, color: theme.colorScheme.secondary),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('下一步', style: theme.textTheme.labelSmall),
                  Text(
                    recommendation.reason,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            FilledButton(onPressed: onTap, child: Text(recommendation.label)),
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

class _TodayPlanCard extends StatelessWidget {
  const _TodayPlanCard({
    required this.plan,
    required this.onReview,
    required this.onPractice,
  });

  final HomeTodayPlan plan;
  final VoidCallback onReview;
  final VoidCallback onPractice;

  @override
  Widget build(BuildContext context) {
    final accents = AppAccents.of(context);
    return AccentCard(
      accent: accents.learn,
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      child: Row(
        children: [
          Expanded(
            child: _PlanStat(
              icon: Icons.replay,
              value: '${plan.dueReview}',
              label: '到期复习',
              onTap: onReview,
            ),
          ),
          Expanded(
            child: _PlanStat(
              icon: Icons.edit_note,
              value: '${plan.practiceQuestions} 题',
              label: '建议练习 · ${plan.practiceMinutes} 分钟',
              onTap: onPractice,
            ),
          ),
          Expanded(
            child: _PlanStat(
              icon: Icons.auto_awesome,
              value: '${plan.newKpTarget} 个',
              label: '新知识点',
              onTap: null,
            ),
          ),
        ],
      ),
    );
  }
}

class _PlanStat extends StatelessWidget {
  const _PlanStat({
    required this.icon,
    required this.value,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String value;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
        child: Column(
          children: [
            Icon(icon, size: 20, color: theme.colorScheme.primary),
            const SizedBox(height: 4),
            Text(
              value,
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              textAlign: TextAlign.center,
              style: theme.textTheme.labelSmall,
            ),
          ],
        ),
      ),
    );
  }
}

class _TextbookTile extends StatelessWidget {
  const _TextbookTile({required this.textbook, required this.onTap});

  final HomeTextbook textbook;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accents = AppAccents.of(context);
    return AccentCard(
      accent: accents.learn,
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: theme.colorScheme.primaryContainer,
          child: Icon(
            _subjectIcon(textbook.subject),
            color: theme.colorScheme.primary,
          ),
        ),
        title: Row(
          children: [
            Text(textbook.subjectLabel),
            const SizedBox(width: 6),
            if (textbook.mismatch)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: theme.colorScheme.errorContainer,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '年级不一致',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: theme.colorScheme.error,
                  ),
                ),
              ),
          ],
        ),
        subtitle: Text(
          '${textbook.version} · ${textbook.grade} 年级'
          ' · ${_semesterLabel(textbook.semester)}',
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}

/// 非学生账号：保留教材 / 章节浏览能力。
class _TextbookBrowseView extends ConsumerStatefulWidget {
  const _TextbookBrowseView();

  @override
  ConsumerState<_TextbookBrowseView> createState() =>
      _TextbookBrowseViewState();
}

class _TextbookBrowseViewState extends ConsumerState<_TextbookBrowseView> {
  List<Textbook> _textbooks = const [];
  List<Chapter> _chapters = const [];
  Textbook? _selectedTextbook;
  bool _loadingTextbooks = true;
  bool _loadingChapters = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadTextbooks();
  }

  Future<void> _loadTextbooks() async {
    setState(() {
      _loadingTextbooks = true;
      _error = null;
    });
    try {
      final grade = ref.read(currentUserProvider)?.grade;
      final textbooks = await ref
          .read(contentServiceProvider)
          .textbooks(grade: grade);
      if (!mounted) return;
      setState(() {
        _textbooks = textbooks;
        _loadingTextbooks = false;
      });
      if (textbooks.isNotEmpty) {
        await _loadChapters(textbooks.first);
      }
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loadingTextbooks = false;
      });
    }
  }

  Future<void> _loadChapters(Textbook textbook) async {
    setState(() {
      _selectedTextbook = textbook;
      _chapters = const [];
      _loadingChapters = true;
      _error = null;
    });
    try {
      final chapters = await ref
          .read(contentServiceProvider)
          .chapters(textbook.id);
      if (!mounted) return;
      setState(() {
        _chapters = chapters;
        _loadingChapters = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loadingChapters = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    final accents = AppAccents.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('深爱学 · 学习')),
      body: RefreshIndicator(
        onRefresh: _loadTextbooks,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _WelcomeHeader(
              nickname: user?.nickname ?? '',
              grade: user?.grade,
              stage: null,
              semester: null,
            ),
            const SizedBox(height: 16),
            Text('我的教材', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            if (_loadingTextbooks)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(child: CircularProgressIndicator()),
              )
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _textbooks
                    .map(
                      (textbook) => ChoiceChip(
                        label: Text(textbook.displayName),
                        selected: _selectedTextbook?.id == textbook.id,
                        onSelected: (_) => _loadChapters(textbook),
                      ),
                    )
                    .toList(),
              ),
            const SizedBox(height: 20),
            Text('章节与知识点', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              '按章节查看知识点掌握度，开始自适应练习',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            if (_loadingChapters)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_chapters.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(child: Text('暂无章节内容')),
              )
            else
              ..._chapters.map(
                (chapter) => AccentCard(
                  accent: accents.learn,
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: const Icon(Icons.menu_book_outlined),
                    title: Text(chapter.name),
                    subtitle: chapter.summary == null
                        ? null
                        : Text(chapter.summary!),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () {
                      final textbook = _selectedTextbook;
                      if (textbook == null) return;
                      context.push(
                        '/knowledge/${textbook.id}'
                        '?name=${Uri.encodeComponent(textbook.displayName)}'
                        '&chapter=${chapter.id}',
                      );
                    },
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _LastPractice {
  const _LastPractice({
    required this.id,
    required this.title,
    required this.total,
    required this.answered,
  });

  final int id;
  final String title;
  final int total;
  final int answered;
}

String _semesterLabel(String semester) {
  switch (semester) {
    case 'first':
      return '上学期';
    case 'second':
      return '下学期';
    default:
      return semester;
  }
}

IconData _subjectIcon(String subject) {
  switch (subject) {
    case 'chinese':
      return Icons.menu_book_outlined;
    case 'english':
      return Icons.translate;
    case 'physics':
      return Icons.science_outlined;
    case 'chemistry':
      return Icons.bubble_chart_outlined;
    case 'biology':
      return Icons.eco_outlined;
    case 'history':
      return Icons.history_edu_outlined;
    case 'geography':
      return Icons.public;
    case 'politics':
      return Icons.balance_outlined;
    default:
      return Icons.calculate_outlined;
  }
}
