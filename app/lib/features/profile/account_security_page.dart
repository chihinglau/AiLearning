import 'dart:convert';

import 'package:ai_learning/core/models/usage.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 账号与安全（R-04）：今日学习时长、数据导出、账号注销。
class AccountSecurityPage extends ConsumerStatefulWidget {
  const AccountSecurityPage({super.key});

  @override
  ConsumerState<AccountSecurityPage> createState() => _AccountSecurityPageState();
}

class _AccountSecurityPageState extends ConsumerState<AccountSecurityPage> {
  DailyUsage? _usage;
  bool _exporting = false;
  bool _deleting = false;

  @override
  void initState() {
    super.initState();
    _loadUsage();
  }

  Future<void> _loadUsage() async {
    try {
      final usage = await ref.read(complianceServiceProvider).usage();
      if (mounted) setState(() => _usage = usage);
    } on ApiException {
      // 离线/未登录时静默，页面仍可使用导出与注销入口。
    }
  }

  Future<void> _export() async {
    if (_exporting) return;
    setState(() => _exporting = true);
    try {
      final data = await ref.read(complianceServiceProvider).exportMyData();
      if (!mounted) return;
      final meta = (data['meta'] as Map<String, dynamic>?) ?? const {};
      final counts = (meta['section_counts'] as Map<String, dynamic>?) ?? const {};
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('我的数据已生成'),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('用途：${meta['purpose_label'] ?? '个人查阅'}'),
                const SizedBox(height: 8),
                for (final entry in counts.entries)
                  Text('${entry.key}：${entry.value} 条'),
                if (counts.isEmpty) const Text('暂无可导出的学习数据。'),
                const SizedBox(height: 8),
                const Text('手机号等敏感字段已脱敏。'),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () async {
                await Clipboard.setData(
                  ClipboardData(text: const JsonEncoder.withIndent('  ').convert(data)),
                );
                if (dialogContext.mounted) Navigator.of(dialogContext).pop();
              },
              child: const Text('复制 JSON'),
            ),
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('关闭'),
            ),
          ],
        ),
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('如已复制，可粘贴保存；导出内容仅供本人使用')),
        );
      }
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  Future<void> _deleteAccount() async {
    if (_deleting) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('确认注销账号？'),
        content: const Text(
          '注销后立即停用并匿名化，手机号、昵称、学习记录将不再关联到你；'
          '家长绑定全部解除，登录凭证失效。注销不可恢复，'
          '我们将在 15 个工作日内完成删除或匿名化。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('确认注销'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    setState(() => _deleting = true);
    try {
      final result = await ref.read(complianceServiceProvider).requestDeletion();
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('注销申请已受理'),
          content: Text(result['message'] as String? ?? '我们将在 15 个工作日内完成处理。'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('知道了'),
            ),
          ],
        ),
      );
      await ref.read(authServiceProvider).logout();
      ref.read(currentUserProvider.notifier).state = null;
      if (mounted) context.go('/login');
    } on ApiException catch (error) {
      if (mounted) {
        setState(() => _deleting = false);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final usage = _usage;
    return Scaffold(
      appBar: AppBar(title: const Text('账号与安全')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '今日学习时长',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (usage == null)
                    Text('加载中…', style: theme.textTheme.bodyMedium)
                  else if (usage.dailyLimitMinutes <= 0)
                    Text('未启用每日时长限制', style: theme.textTheme.bodyMedium)
                  else
                    Text(
                      '已用 ${usage.usedMinutes} / ${usage.dailyLimitMinutes} 分钟'
                      '（剩余 ${usage.remainingMinutes ?? 0} 分钟）',
                      style: theme.textTheme.bodyMedium,
                    ),
                  if (usage != null && usage.limited) ...[
                    const SizedBox(height: 6),
                    Text(
                      '今日时长已用完，请明天再来',
                      style: TextStyle(color: theme.colorScheme.error),
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.download_outlined),
                  title: const Text('导出我的数据'),
                  subtitle: const Text('生成脱敏后的学习数据 JSON，可复制保存'),
                  trailing: _exporting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.chevron_right),
                  onTap: _exporting ? null : _export,
                ),
                const Divider(height: 1),
                ListTile(
                  leading: Icon(Icons.delete_forever_outlined, color: theme.colorScheme.error),
                  title: Text('注销账号', style: TextStyle(color: theme.colorScheme.error)),
                  subtitle: const Text('立即停用并匿名化，15 个工作日内完成'),
                  trailing: _deleting
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.chevron_right),
                  onTap: _deleting ? null : _deleteAccount,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(
            '注销与导出均会记录审计日志；如遇问题可通过「我的 → 联系我们」反馈。',
            style: theme.textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
