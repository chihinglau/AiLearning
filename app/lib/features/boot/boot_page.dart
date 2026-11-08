import 'dart:async';

import 'package:ai_learning/core/providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 启动引导：恢复本地双 Token 登录态，断网时允许进入离线可用界面。
class BootPage extends ConsumerStatefulWidget {
  const BootPage({super.key});

  @override
  ConsumerState<BootPage> createState() => _BootPageState();
}

class _BootPageState extends ConsumerState<BootPage> {
  bool _error = false;

  @override
  void initState() {
    super.initState();
    Future<void>.microtask(_boot);
  }

  Future<void> _boot() async {
    if (mounted) setState(() => _error = false);
    try {
      final auth = ref.read(authServiceProvider);
      final user = await auth.restoreSession();
      if (!mounted) return;
      if (user == null) {
        context.go('/login');
        return;
      }
      ref.read(currentUserProvider.notifier).state = user;
      // 启动联网成功后同步离线答题队列（失败时静默保留）。
      unawaited(ref.read(offlineLearnSyncProvider).sync());

      final cachedStatus = await auth.readOnboardingStatus();
      ref.read(onboardingStatusProvider.notifier).state = switch (cachedStatus) {
        'completed' => OnboardingStatus.completed,
        'required' => OnboardingStatus.required,
        _ => OnboardingStatus.unknown,
      };
      if (!mounted) return;
      if (user.needsReconsent) {
        context.go('/consent');
        return;
      }
      context.go(cachedStatus == 'completed' ? '/shell' : '/gate');
    } catch (_) {
      if (mounted) setState(() => _error = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: _error
              ? Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline, size: 48),
                    const SizedBox(height: 12),
                    const Text('启动失败，请重试'),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: _boot,
                      child: const Text('重试'),
                    ),
                    TextButton(
                      onPressed: () => context.go('/login'),
                      child: const Text('重新登录'),
                    ),
                  ],
                )
              : const CircularProgressIndicator(),
        ),
      ),
    );
  }
}
