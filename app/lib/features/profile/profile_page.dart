import 'package:ai_learning/core/constants/legal_constants.dart';
import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/models/user.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/theme/app_accents.dart';
import 'package:ai_learning/features/learn/widgets/offline_banner.dart';
import 'package:ai_learning/widgets/accent_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class ProfilePage extends ConsumerStatefulWidget {
  const ProfilePage({super.key});

  @override
  ConsumerState<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends ConsumerState<ProfilePage> {
  LearnStats? _stats;
  bool _loading = true;
  bool _offline = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final user = ref.read(currentUserProvider);
    if (user == null || !user.isStudent) {
      setState(() {
        _stats = null;
        _loading = false;
        _error = null;
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final stats = await ref.read(learnServiceProvider).stats();
      if (!mounted) return;
      setState(() {
        _stats = stats;
        _offline = false;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      // 断网时回退到最近一次同步的学情统计。
      final cached = error.statusCode == null
          ? await ref.read(offlineLearnServiceProvider).cachedStats()
          : null;
      if (!mounted) return;
      setState(() {
        if (cached != null) {
          _stats = cached;
          _offline = true;
          _error = null;
        } else {
          _error = ApiErrorGuide.from(error).message;
        }
        _loading = false;
      });
    }
  }

  Future<void> _logout() async {
    await ref.read(authServiceProvider).logout();
    ref.read(currentUserProvider.notifier).state = null;
    if (!mounted) return;
    context.go('/login');
  }

  void _showContact(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('联系我们'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('客服与个人信息保护负责人邮箱'),
            SizedBox(height: 8),
            SelectableText(kLegalSupportEmail),
            SizedBox(height: 12),
            Text('我们将在收到问题后 15 个工作日内回复。'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('我的')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Card(
                    color: theme.colorScheme.primaryContainer,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 28,
                            backgroundColor: theme.colorScheme.primary,
                            child: const Icon(
                              Icons.person,
                              color: Colors.white,
                              size: 32,
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  user?.nickname ?? '同学',
                                  style: theme.textTheme.titleMedium,
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  user?.isStudent == true
                                      ? (user?.grade != null
                                            ? '${user!.grade} 年级在读'
                                            : '深圳学生')
                                      : _roleLabel(user?.role),
                                  style: theme.textTheme.bodySmall,
                                ),
                                Text(
                                  user?.phone ?? '',
                                  style: theme.textTheme.bodySmall,
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (_offline)
                    const OfflineBanner(message: '离线模式，显示最近一次同步的学情统计'),
                  if (_error != null)
                    Text(
                      _error!,
                      style: TextStyle(color: theme.colorScheme.error),
                    ),
                  if (_stats != null) ...[
                    Row(
                      children: [
                        _StatCard(
                          icon: Icons.local_fire_department_outlined,
                          value: '${_stats!.streakDays}',
                          label: '连续学习(天)',
                          color: AppAccents.of(context).exam,
                        ),
                        _StatCard(
                          icon: Icons.edit_note,
                          value: '${_stats!.totalAnswered}',
                          label: '累计答题',
                          color: AppAccents.of(context).practice,
                        ),
                      ],
                    ),
                    Row(
                      children: [
                        _StatCard(
                          icon: Icons.verified_outlined,
                          value: _stats!.accuracyPercent,
                          label: '总正确率',
                          color: AppAccents.of(context).learn,
                        ),
                        _StatCard(
                          icon: Icons.bookmark_border,
                          value: '${_stats!.activeWrongCount}',
                          label: '待消灭错题',
                          color: AppAccents.of(context).assignment,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text('薄弱知识点 Top3', style: theme.textTheme.titleMedium),
                    const SizedBox(height: 8),
                    if (_stats!.weakPoints.isEmpty)
                      AccentCard(
                        accent: AppAccents.of(context).learn,
                        padding: const EdgeInsets.all(16),
                        child: Text(
                          _stats!.totalAnswered == 0
                              ? '还没有答题记录，去「学习」里练一练吧。'
                              : '掌握度都在 70 分以上，暂无薄弱知识点，继续保持！',
                          style: theme.textTheme.bodyMedium,
                        ),
                      )
                    else
                      ..._stats!.weakPoints.map(
                        (node) => AccentCard(
                          accent: node.bandColor,
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: EdgeInsets.zero,
                          child: ListTile(
                            leading: Icon(
                              Icons.circle,
                              size: 12,
                              color: node.bandColor,
                            ),
                            title: Text('${node.subjectLabel} · ${node.name}'),
                            subtitle: Text(
                              node.explanation ?? '',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            trailing: Text(
                              '${node.masteryScore.round()}',
                              style: theme.textTheme.titleMedium?.copyWith(
                                color: node.bandColor,
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                  const SizedBox(height: 24),
                  if (user?.isStudent == true) ...[
                    AccentCard(
                      accent: AppAccents.of(context).practice,
                      padding: EdgeInsets.zero,
                      child: ListTile(
                        leading: const Icon(Icons.school_outlined),
                        title: const Text('年级设置'),
                        subtitle: Text(
                          user?.grade != null
                              ? '当前 ${user!.grade} 年级 · 每学期可修改 1 次'
                              : '设置当前年级',
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/onboarding?edit=1'),
                      ),
                    ),
                    const SizedBox(height: 16),
                    AccentCard(
                      accent: AppAccents.of(context).learn,
                      padding: EdgeInsets.zero,
                      child: ListTile(
                        leading: const Icon(Icons.menu_book_outlined),
                        title: const Text('教材管理'),
                        subtitle: const Text('切换版本、学期或解绑教材'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/textbooks'),
                      ),
                    ),
                    const SizedBox(height: 16),
                    if (user?.grade case final grade?
                        when grade >= 1 && grade <= 3) ...[
                      AccentCard(
                        accent: AppAccents.of(context).practice,
                        padding: EdgeInsets.zero,
                        child: ListTile(
                          leading: const Icon(Icons.record_voice_over_outlined),
                          title: const Text('学习设置'),
                          subtitle: const Text('自动读题与读题语速'),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () => context.push('/settings/learning'),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                  ],
                  if (user?.hasPermission('learn:stats:child:read') ==
                      true) ...[
                    AccentCard(
                      accent: AppAccents.of(context).assignment,
                      padding: EdgeInsets.zero,
                      child: ListTile(
                        leading: const Icon(Icons.family_restroom),
                        title: const Text('家长中心'),
                        subtitle: const Text('查看孩子学情、设置每日时长与青少年模式'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/family'),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                  if (user?.hasPermission('learn:stats:class:read') ==
                      true) ...[
                    AccentCard(
                      accent: AppAccents.of(context).practice,
                      padding: EdgeInsets.zero,
                      child: ListTile(
                        leading: const Icon(Icons.co_present_outlined),
                        title: const Text('教师中心'),
                        subtitle: const Text('查看授课班级概览与班级学情（聚合）'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/teacher/classes'),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                  if (user?.hasPermission('learn:assignment:create') ==
                      true) ...[
                    AccentCard(
                      accent: AppAccents.of(context).exam,
                      padding: EdgeInsets.zero,
                      child: ListTile(
                        leading: const Icon(Icons.edit_document),
                        title: const Text('班级作业'),
                        subtitle: const Text('为班级布置统一卷并批改主观题'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/assignments'),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                  if (_canReviewContent(user)) ...[
                    AccentCard(
                      accent: AppAccents.of(context).assignment,
                      padding: EdgeInsets.zero,
                      child: ListTile(
                        leading: const Icon(Icons.fact_check_outlined),
                        title: const Text('内容审核'),
                        subtitle: const Text('复核题目/试卷并发布（双人复核）'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/content/reviews'),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                  if (user?.hasPermission('system:config:write') == true) ...[
                    AccentCard(
                      accent: AppAccents.of(context).practice,
                      padding: EdgeInsets.zero,
                      child: ListTile(
                        leading: const Icon(
                          Icons.admin_panel_settings_outlined,
                        ),
                        title: const Text('权限配置'),
                        subtitle: const Text('按角色查看与调整权限点（超级管理员）'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/admin/rbac'),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                  const SizedBox(height: 16),
                  // R-04：账号与安全（时长状态、数据导出、账号注销）。
                  AccentCard(
                    accent: AppAccents.of(context).exam,
                    padding: EdgeInsets.zero,
                    child: ListTile(
                      leading: const Icon(Icons.security_outlined),
                      title: const Text('账号与安全'),
                      subtitle: const Text('今日学习时长、数据导出、注销账号'),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => context.push('/account/security'),
                    ),
                  ),
                  const SizedBox(height: 16),
                  // R-03：法务入口（隐私政策 / 用户协议 / 联系我们）。
                  Card(
                    child: Column(
                      children: [
                        ListTile(
                          leading: const Icon(Icons.privacy_tip_outlined),
                          title: const Text('隐私政策'),
                          subtitle: const Text('我们如何收集、使用与保护个人信息'),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () => context.push('/legal/privacy'),
                        ),
                        const Divider(height: 1),
                        ListTile(
                          leading: const Icon(Icons.description_outlined),
                          title: const Text('用户协议'),
                          subtitle: const Text('服务内容、使用规范与未成年人保护'),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () => context.push('/legal/terms'),
                        ),
                        const Divider(height: 1),
                        ListTile(
                          leading: const Icon(Icons.support_agent_outlined),
                          title: const Text('联系我们'),
                          subtitle: const Text(kLegalSupportEmail),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () => _showContact(context),
                        ),
                        const Divider(height: 1),
                        ListTile(
                          leading: const Icon(Icons.flag_outlined),
                          title: const Text('内容举报'),
                          subtitle: const Text('题目/教材内容问题反馈，24 小时内处理'),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () => context.push('/content/report'),
                        ),
                        const Divider(height: 1),
                        ListTile(
                          leading: const Icon(Icons.troubleshoot_outlined),
                          title: const Text('环境诊断'),
                          subtitle: const Text('服务地址、连通性与读题能力'),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () => context.push('/settings/diagnostics'),
                        ),
                        const Divider(height: 1),
                        ListTile(
                          leading: const Icon(Icons.info_outline),
                          title: const Text('关于'),
                          subtitle: const Text('版本信息、备案号与软著登记号'),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () => context.push('/about'),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  OutlinedButton.icon(
                    onPressed: _logout,
                    icon: const Icon(Icons.logout),
                    label: const Text('退出登录'),
                  ),
                ],
              ),
            ),
    );
  }
}

bool _canReviewContent(AppUser? user) {
  if (user == null) return false;
  return user.hasPermission('content:review:decide') ||
      user.hasPermission('content:publish') ||
      user.hasPermission('content:question:write') ||
      user.hasPermission('content:exam:write');
}

String _roleLabel(String? role) {
  switch (role) {
    case 'parent':
      return '家长账号';
    case 'teacher':
      return '教师账号';
    case 'head_teacher':
      return '班主任';
    case 'school_admin':
      return '校级管理员';
    case 'content_operator':
      return '内容运营';
    case 'auditor':
      return '审核员';
    case 'customer_service':
      return '客服';
    case 'super_admin':
    case 'admin':
      return '超级管理员';
    default:
      return '用户';
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
      child: AccentCard(
        accent: color,
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
        child: Column(
          children: [
            Icon(icon, color: color),
            const SizedBox(height: 6),
            Text(
              value,
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            Text(label, style: theme.textTheme.labelSmall),
          ],
        ),
      ),
    );
  }
}
