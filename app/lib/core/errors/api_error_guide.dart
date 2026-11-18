import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

enum ApiErrorAction { none, reLogin, onboarding }

/// 按业务码把后端错误映射为可执行的引导。
class ApiErrorGuide {
  const ApiErrorGuide({
    required this.code,
    required this.message,
    this.action = ApiErrorAction.none,
  });

  final String? code;
  final String message;
  final ApiErrorAction action;

  factory ApiErrorGuide.from(ApiException error) {
    final code = error.code;
    switch (code) {
      case 'TOKEN_REVOKED':
        return const ApiErrorGuide(
          code: 'TOKEN_REVOKED',
          message: '登录状态已失效，请重新登录',
          action: ApiErrorAction.reLogin,
        );
      case 'PERMISSION_DENIED':
        return const ApiErrorGuide(
          code: 'PERMISSION_DENIED',
          message: '当前账号无权限执行该操作',
        );
      case 'SCOPE_DENIED':
        return const ApiErrorGuide(
          code: 'SCOPE_DENIED',
          message: '无权访问该学生数据',
        );
      case 'GRADE_REQUIRED':
      case 'GRADE_MISSING':
        return const ApiErrorGuide(
          code: 'GRADE_REQUIRED',
          message: '请先完善年级信息',
          action: ApiErrorAction.onboarding,
        );
      case 'DAILY_LIMIT_REACHED':
        return ApiErrorGuide(code: 'DAILY_LIMIT_REACHED', message: error.message);
      // 评审 R2-03/R2-04：真题复核的双人约束与退回留痕失败码
      case 'EXAM_REVIEW_SELF':
        return const ApiErrorGuide(
          code: 'EXAM_REVIEW_SELF',
          message: '双人复核：提交人与复核发布人不能是同一账号，请换人发布',
        );
      case 'EXAM_REVIEW_NOTE_REQUIRED':
        return const ApiErrorGuide(
          code: 'EXAM_REVIEW_NOTE_REQUIRED',
          message: '退回必须填写复核意见，便于试卷负责人整改',
        );
      case 'EXAM_INVALID_STATE':
        return ApiErrorGuide(
          code: 'EXAM_INVALID_STATE',
          message: error.message.isEmpty ? '当前状态不允许该操作，请刷新后重试' : error.message,
        );
    }
    if (error.statusCode == 401) {
      return const ApiErrorGuide(
        code: 'UNAUTHORIZED',
        message: '登录状态已失效，请重新登录',
        action: ApiErrorAction.reLogin,
      );
    }
    if (error.statusCode == 403) {
      return ApiErrorGuide(code: code, message: '当前账号无权限执行该操作');
    }
    return ApiErrorGuide(code: code, message: error.message);
  }
}

Future<void> handleApiError(
  BuildContext context,
  WidgetRef ref,
  ApiException error,
) async {
  final guide = ApiErrorGuide.from(error);
  if (guide.action == ApiErrorAction.reLogin) {
    await ref.read(authServiceProvider).logout();
    ref.read(currentUserProvider.notifier).state = null;
    ref.read(onboardingStatusProvider.notifier).state = OnboardingStatus.unknown;
    if (context.mounted) context.go('/login');
    return;
  }
  if (guide.action == ApiErrorAction.onboarding) {
    ref.read(onboardingStatusProvider.notifier).state = OnboardingStatus.required;
    if (context.mounted) context.go('/onboarding');
    return;
  }
  if (guide.code == 'DAILY_LIMIT_REACHED' && context.mounted) {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('今日学习时长已用完'),
        content: Text('${guide.message}。可在「我的 → 账号与安全」查看今日时长。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
    return;
  }
  if (context.mounted) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(guide.message)),
    );
  }
}
