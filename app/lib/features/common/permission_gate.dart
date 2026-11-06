import 'package:ai_learning/core/providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 路由级权限守卫：anyOf 任一命中即放行，超管 `*` 直接放行。
class PermissionGate extends ConsumerWidget {
  const PermissionGate({
    super.key,
    required this.anyOf,
    required this.child,
    this.fallback,
  });

  final List<String> anyOf;
  final Widget child;
  final Widget? fallback;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    if (user == null) {
      return fallback ?? const SizedBox.shrink();
    }
    if (anyOf.isEmpty || user.hasAnyPermission(anyOf)) {
      return child;
    }
    return fallback ?? const ForbiddenPage();
  }
}

class ForbiddenPage extends StatelessWidget {
  const ForbiddenPage({super.key, this.message});

  final String? message;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('无法访问')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.lock_outline,
                size: 56,
                color: theme.colorScheme.error,
              ),
              const SizedBox(height: 16),
              Text('无权限访问', style: theme.textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(
                message ?? '当前账号无权访问该页面，如需开通请联系管理员。',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (context.canPop())
                    OutlinedButton(
                      onPressed: context.pop,
                      child: const Text('返回'),
                    ),
                  if (context.canPop()) const SizedBox(width: 12),
                  FilledButton(
                    onPressed: () => context.go('/shell'),
                    child: const Text('回到学习首页'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
