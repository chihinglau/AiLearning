import 'package:ai_learning/core/models/app_info.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 关于（R-06）：应用名称/版本、ICP 与 APP 备案号、软著登记号、法务入口。
class AboutPage extends ConsumerStatefulWidget {
  const AboutPage({super.key});

  @override
  ConsumerState<AboutPage> createState() => _AboutPageState();
}

class _AboutPageState extends ConsumerState<AboutPage> {
  AppInfo _info = AppInfo.fallback();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final info = await ref.read(appInfoServiceProvider).fetch();
    if (mounted) setState(() => _info = info);
  }

  void _showContact() {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('联系我们'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('客服与个人信息保护负责人邮箱'),
            const SizedBox(height: 8),
            SelectableText(_info.supportEmail),
            const SizedBox(height: 12),
            const Text('我们将在收到问题后 15 个工作日内回复。'),
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

  String _recordValue(String value) => value.trim().isEmpty ? '待补充' : value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('关于')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  CircleAvatar(
                    radius: 32,
                    backgroundColor: theme.colorScheme.primaryContainer,
                    child: Icon(
                      Icons.school_outlined,
                      size: 36,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _info.name,
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text('版本 ${_info.version}', style: theme.textTheme.bodyMedium),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.language_outlined),
                  title: const Text('ICP 备案号'),
                  subtitle: Text(_recordValue(_info.icpRecordNo)),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.phone_android_outlined),
                  title: const Text('APP 备案号'),
                  subtitle: Text(_recordValue(_info.appRecordNo)),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.workspace_premium_outlined),
                  title: const Text('软件著作权登记号'),
                  subtitle: Text(_recordValue(_info.softwareCopyrightNo)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.privacy_tip_outlined),
                  title: const Text('隐私政策'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.go('/legal/privacy'),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.description_outlined),
                  title: const Text('用户协议'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.go('/legal/terms'),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.support_agent_outlined),
                  title: const Text('联系我们'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: _showContact,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(
            '备案号与登记号以主管部门最终下发为准，如有更新请以本页展示为准。',
            style: theme.textTheme.bodySmall,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
