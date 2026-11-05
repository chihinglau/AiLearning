import 'package:ai_learning/features/auth/login_page.dart';
import 'package:ai_learning/features/learn/knowledge_page.dart';
import 'package:ai_learning/features/practice/practice_page.dart';
import 'package:ai_learning/features/session/session_page.dart';
import 'package:ai_learning/features/shell/app_shell.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/login',
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginPage(),
      ),
      GoRoute(
        path: '/shell',
        builder: (context, state) {
          final tab = int.tryParse(state.uri.queryParameters['tab'] ?? '') ?? 0;
          return AppShell(initialTab: tab.clamp(0, 2));
        },
      ),
      // 兼容旧版本跳转。
      GoRoute(
        path: '/home',
        builder: (context, state) => const AppShell(),
      ),
      GoRoute(
        path: '/knowledge/:textbookId',
        builder: (context, state) {
          final textbookId = int.tryParse(state.pathParameters['textbookId'] ?? '');
          if (textbookId == null) {
            return const AppShell();
          }
          return KnowledgePage(
            textbookId: textbookId,
            textbookName: state.uri.queryParameters['name'] ?? '知识点',
            initialChapterId:
                int.tryParse(state.uri.queryParameters['chapter'] ?? ''),
          );
        },
      ),
      GoRoute(
        path: '/session',
        builder: (context, state) {
          final qp = state.uri.queryParameters;
          return SessionPage(
            title: qp['title'] ?? '自适应练习',
            knowledgePointId: int.tryParse(qp['kp'] ?? ''),
            chapterId: int.tryParse(qp['chapter'] ?? ''),
            subject: qp['subject'],
            reviewMode: qp['review'] == '1',
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
          return PracticePage(chapterId: chapterId, chapterName: name);
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
