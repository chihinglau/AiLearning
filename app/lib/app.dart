import 'package:ai_learning/features/auth/login_page.dart';
import 'package:ai_learning/features/home/home_page.dart';
import 'package:ai_learning/features/practice/practice_page.dart';
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
        path: '/home',
        builder: (context, state) => const HomePage(),
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
