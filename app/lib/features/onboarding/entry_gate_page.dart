import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 登录后入口：判定年级/教材是否就绪，未完成则强制进入引导页。
class EntryGatePage extends ConsumerStatefulWidget {
  const EntryGatePage({super.key});

  @override
  ConsumerState<EntryGatePage> createState() => _EntryGatePageState();
}

class _EntryGatePageState extends ConsumerState<EntryGatePage> {
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    Future<void>.microtask(_resolve);
  }

  Future<void> _resolve() async {
    final user = ref.read(currentUserProvider);
    if (user == null) {
      if (mounted) context.go('/login');
      return;
    }
    if (!user.isStudent) {
      await _complete();
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final bindings = await ref.read(textbookServiceProvider).listBindings();
      var required = false;
      if (bindings.isEmpty) {
        final recommendation =
            await ref.read(textbookServiceProvider).recommend();
        required = recommendation.subjects.isNotEmpty;
      }
      if (!mounted) return;
      await ref
          .read(authServiceProvider)
          .writeOnboardingStatus(required ? 'required' : 'completed');
      if (!mounted) return;
      ref.read(onboardingStatusProvider.notifier).state = required
          ? OnboardingStatus.required
          : OnboardingStatus.completed;
      context.go(required ? '/onboarding' : '/shell');
    } on ApiException catch (error) {
      if (!mounted) return;
      // 断网时沿用上次完成的引导状态，直接进入离线可用首页。
      if (error.statusCode == null) {
        final cached = await ref.read(authServiceProvider).readOnboardingStatus();
        if (!mounted) return;
        if (cached == 'completed') {
          await _complete();
          return;
        }
      }
      setState(() {
        _loading = false;
        _error = ApiErrorGuide.from(error).message;
      });
    }
  }

  Future<void> _complete() async {
    await ref.read(authServiceProvider).writeOnboardingStatus('completed');
    ref.read(onboardingStatusProvider.notifier).state =
        OnboardingStatus.completed;
    if (mounted) context.go('/shell');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: _loading
              ? const CircularProgressIndicator()
              : Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.cloud_off_outlined,
                      size: 48,
                      color: Theme.of(context).colorScheme.error,
                    ),
                    const SizedBox(height: 12),
                    Text(_error ?? '加载失败'),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: _resolve,
                      child: const Text('重试'),
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}
