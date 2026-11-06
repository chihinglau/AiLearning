import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/features/auth/login_page.dart';
import 'package:ai_learning/features/common/permission_gate.dart';
import 'package:ai_learning/features/learn/knowledge_page.dart';
import 'package:ai_learning/features/learn/kp_detail_page.dart';
import 'package:ai_learning/features/learn/unit_page.dart';
import 'package:ai_learning/features/onboarding/entry_gate_page.dart';
import 'package:ai_learning/features/onboarding/onboarding_page.dart';
import 'package:ai_learning/features/practice/practice_page.dart';
import 'package:ai_learning/features/session/session_page.dart';
import 'package:ai_learning/features/shell/app_shell.dart';
import 'package:ai_learning/features/textbook/textbook_manage_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/login',
    redirect: (context, state) {
      final location = state.matchedLocation;
      final user = ref.read(currentUserProvider);
      if (user == null) {
        return location == '/login' ? null : '/login';
      }
      if (location == '/login') return null;
      final status = ref.read(onboardingStatusProvider);
      if (status == OnboardingStatus.required && location != '/onboarding') {
        return '/onboarding';
      }
      if (status == OnboardingStatus.completed && location == '/onboarding') {
        return '/shell';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginPage(),
      ),
      GoRoute(
        path: '/gate',
        builder: (context, state) => const EntryGatePage(),
      ),
      GoRoute(
        path: '/onboarding',
        builder: (context, state) => const OnboardingPage(),
      ),
      GoRoute(
        path: '/shell',
        builder: (context, state) {
          final tab = int.tryParse(state.uri.queryParameters['tab'] ?? '') ?? 0;
          return PermissionGate(
            anyOf: const ['learn:content:read'],
            child: AppShell(initialTab: tab.clamp(0, 2)),
          );
        },
      ),
      // 兼容旧版本跳转。
      GoRoute(
        path: '/home',
        builder: (context, state) => const PermissionGate(
          anyOf: ['learn:content:read'],
          child: AppShell(),
        ),
      ),
      GoRoute(
        path: '/textbooks',
        builder: (context, state) => const PermissionGate(
          anyOf: ['learn:content:read'],
          child: TextbookManagePage(),
        ),
      ),
      GoRoute(
        path: '/knowledge/:textbookId',
        builder: (context, state) {
          final textbookId = int.tryParse(state.pathParameters['textbookId'] ?? '');
          if (textbookId == null) {
            return const AppShell();
          }
          return PermissionGate(
            anyOf: const ['learn:kp:study'],
            child: KnowledgePage(
              textbookId: textbookId,
              textbookName: state.uri.queryParameters['name'] ?? '知识点',
              initialChapterId:
                  int.tryParse(state.uri.queryParameters['chapter'] ?? ''),
            ),
          );
        },
      ),
      GoRoute(
        path: '/unit/:chapterId',
        builder: (context, state) {
          final chapterId = int.tryParse(state.pathParameters['chapterId'] ?? '');
          if (chapterId == null) return const AppShell();
          final query = state.uri.queryParameters;
          return PermissionGate(
            anyOf: const ['learn:kp:study'],
            child: UnitPage(
              chapterId: chapterId,
              unitName: query['name'] ?? '单元',
              textbookName: query['textbook'] ?? '教材',
            ),
          );
        },
      ),
      GoRoute(
        path: '/kp/:kpId',
        builder: (context, state) {
          final kpId = int.tryParse(state.pathParameters['kpId'] ?? '');
          if (kpId == null) return const AppShell();
          return PermissionGate(
            anyOf: const ['learn:kp:study'],
            child: KpDetailPage(kpId: kpId),
          );
        },
      ),
      GoRoute(
        path: '/session',
        builder: (context, state) {
          final qp = state.uri.queryParameters;
          return PermissionGate(
            anyOf: const ['learn:practice:start'],
            child: SessionPage(
              title: qp['title'] ?? '自适应练习',
              knowledgePointId: int.tryParse(qp['kp'] ?? ''),
              chapterId: int.tryParse(qp['chapter'] ?? ''),
              subject: qp['subject'],
              reviewMode: qp['review'] == '1',
            ),
          );
        },
      ),
      GoRoute(
        path: '/practice/:chapterId',
        builder: (context, state) {
          final chapterId = int.tryParse(state.pathParameters['chapterId'] ?? '');
          final name = state.uri.queryParameters['name'] ?? '同步练习';
          if (chapterId == null) {
            return const LoginPage();
          }
          return PermissionGate(
            anyOf: const ['learn:practice:start'],
            child: PracticePage(chapterId: chapterId, chapterName: name),
          );
        },
      ),
    ],
  );
});

class AiLearningApp extends ConsumerWidget {
  const AiLearningApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: '深爱学',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1E6FD9)),
        scaffoldBackgroundColor: const Color(0xFFF7F9FC),
      ),
      routerConfig: router,
    );
  }
}
