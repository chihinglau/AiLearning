import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
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

  Future<void> _logout() async {
    await ref.read(authServiceProvider).logout();
    ref.read(currentUserProvider.notifier).state = null;
    if (!mounted) return;
    context.go('/login');
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
                            child: const Icon(Icons.person, color: Colors.white, size: 32),
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
                                Text(user?.phone ?? '', style: theme.textTheme.bodySmall),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (_error != null)
                    Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
                  if (_stats != null) ...[
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
                          label: '总正确率',
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
                    Text('薄弱知识点 Top3', style: theme.textTheme.titleMedium),
                    const SizedBox(height: 8),
                    if (_stats!.weakPoints.isEmpty)
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Text(
                            _stats!.totalAnswered == 0
                                ? '还没有答题记录，去「学习」里练一练吧。'
                                : '掌握度都在 70 分以上，暂无薄弱知识点，继续保持！',
                            style: theme.textTheme.bodyMedium,
                          ),
                        ),
                      )
                    else
                      ..._stats!.weakPoints.map(
                        (node) => Card(
                          child: ListTile(
                            leading: Icon(Icons.circle, size: 12, color: node.bandColor),
                            title: Text('${node.subjectLabel} · ${node.name}'),
                            subtitle: Text(
                              node.explanation ?? '',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            trailing: Text(
                              '${node.masteryScore.round()}',
                              style: theme.textTheme.titleMedium
                                  ?.copyWith(color: node.bandColor),
                            ),
                          ),
                        ),
                      ),
                  ],
                  const SizedBox(height: 24),
                  if (user?.isStudent == true) ...[
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.menu_book_outlined),
                        title: const Text('教材管理'),
                        subtitle: const Text('切换版本、学期或解绑教材'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.go('/textbooks'),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                  if (user?.hasPermission('learn:stats:child:read') == true) ...[
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.family_restroom),
                        title: const Text('家长中心'),
                        subtitle: const Text('查看孩子学情、设置每日时长与青少年模式'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.go('/family'),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                  if (user?.hasPermission('learn:stats:class:read') == true) ...[
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.co_present_outlined),
                        title: const Text('教师中心'),
                        subtitle: const Text('查看授课班级概览与班级学情（聚合）'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.go('/teacher/classes'),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                  if (user?.hasPermission('learn:assignment:create') == true) ...[
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.edit_document),
                        title: const Text('班级作业'),
                        subtitle: const Text('为班级布置统一卷并批改主观题'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.go('/assignments'),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                  if (user?.hasPermission('system:config:write') == true) ...[
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.admin_panel_settings_outlined),
                        title: const Text('权限配置'),
                        subtitle: const Text('按角色查看与调整权限点（超级管理员）'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.go('/admin/rbac'),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
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
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
          child: Column(
            children: [
              Icon(icon, color: color),
              const SizedBox(height: 6),
              Text(value, style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
              Text(label, style: theme.textTheme.labelSmall),
            ],
          ),
        ),
      ),
    );
  }
}
