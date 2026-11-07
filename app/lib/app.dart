import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/features/admin/rbac_config_page.dart';
import 'package:ai_learning/features/assignment/assignment_create_page.dart';
import 'package:ai_learning/features/assignment/assignment_detail_page.dart';
import 'package:ai_learning/features/assignment/assignment_grading_page.dart';
import 'package:ai_learning/features/assignment/assignment_list_page.dart';
import 'package:ai_learning/features/auth/login_page.dart';
import 'package:ai_learning/features/common/permission_gate.dart';
import 'package:ai_learning/features/content/content_review_page.dart';
import 'package:ai_learning/features/exam/exam_list_page.dart';
import 'package:ai_learning/features/exam/exam_page.dart';
import 'package:ai_learning/features/exam/exam_report_page.dart';
import 'package:ai_learning/features/exam/past_paper_page.dart';
import 'package:ai_learning/features/family/parent_children_page.dart';
import 'package:ai_learning/features/learn/knowledge_graph_page.dart';
import 'package:ai_learning/features/learn/knowledge_page.dart';
import 'package:ai_learning/features/learn/kp_detail_page.dart';
import 'package:ai_learning/features/learn/unit_page.dart';
import 'package:ai_learning/features/legal/consent_gate.dart';
import 'package:ai_learning/features/legal/legal_consent_page.dart';
import 'package:ai_learning/features/legal/legal_document_page.dart';
import 'package:ai_learning/features/onboarding/entry_gate_page.dart';
import 'package:ai_learning/features/onboarding/onboarding_page.dart';
import 'package:ai_learning/features/practice/practice_config_page.dart';
import 'package:ai_learning/features/practice/practice_page.dart';
import 'package:ai_learning/features/session/session_page.dart';
import 'package:ai_learning/features/shell/app_shell.dart';
import 'package:ai_learning/features/teacher/class_stats_page.dart';
import 'package:ai_learning/features/teacher/teacher_classes_page.dart';
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
      // R-03：政策版本升高后强制先重新同意。
      if (user.needsReconsent &&
          location != '/consent' &&
          !location.startsWith('/legal')) {
        return '/consent';
      }
      if (!user.needsReconsent && location == '/consent') {
        return '/gate';
      }
      final status = ref.read(onboardingStatusProvider);
      if (status == OnboardingStatus.required &&
          location != '/onboarding' &&
          location != '/consent') {
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
      // R-03：政策版本升高后的重新同意页与法务文档页。
      GoRoute(
        path: '/consent',
        builder: (context, state) => const LegalConsentPage(),
      ),
      GoRoute(
        path: '/legal/privacy',
        builder: (context, state) => const LegalDocumentPage(docType: 'privacy'),
      ),
      GoRoute(
        path: '/legal/terms',
        builder: (context, state) => const LegalDocumentPage(docType: 'terms'),
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
        path: '/exams',
        builder: (context, state) => const PermissionGate(
          anyOf: ['learn:exam:take'],
          child: ExamListPage(),
        ),
      ),
      GoRoute(
        path: '/past-papers',
        builder: (context, state) => const PermissionGate(
          anyOf: ['learn:exam:take'],
          child: PastPaperPage(),
        ),
      ),
      GoRoute(
        path: '/exam/report/:attemptId',
        builder: (context, state) {
          final attemptId = int.tryParse(state.pathParameters['attemptId'] ?? '');
          if (attemptId == null) return const ExamListPage();
          return PermissionGate(
            anyOf: const ['learn:exam:report:self'],
            child: ExamReportPage(attemptId: attemptId),
          );
        },
      ),
      GoRoute(
        path: '/exam/:examId',
        builder: (context, state) {
          final examId = int.tryParse(state.pathParameters['examId'] ?? '');
          if (examId == null) return const ExamListPage();
          return PermissionGate(
            anyOf: const ['learn:exam:take'],
            child: ExamPage(examId: examId),
          );
        },
      ),
      GoRoute(
        path: '/textbooks',
        builder: (context, state) => const PermissionGate(
          anyOf: ['learn:content:read'],
          child: TextbookManagePage(),
        ),
      ),
      GoRoute(
        path: '/family',
        builder: (context, state) => const PermissionGate(
          anyOf: ['family:report:read', 'learn:stats:child:read'],
          child: ParentChildrenPage(),
        ),
      ),
      GoRoute(
        path: '/teacher/classes',
        builder: (context, state) => const PermissionGate(
          anyOf: ['learn:stats:class:read'],
          child: TeacherClassesPage(),
        ),
      ),
      GoRoute(
        path: '/content/reviews',
        builder: (context, state) => const PermissionGate(
          anyOf: ['content:review:decide', 'content:publish'],
          child: ContentReviewPage(),
        ),
      ),
      GoRoute(
        path: '/admin/rbac',
        builder: (context, state) => const PermissionGate(
          anyOf: ['system:config:write'],
          child: RbacConfigPage(),
        ),
      ),
      GoRoute(
        path: '/assignments',
        builder: (context, state) => const PermissionGate(
          anyOf: ['learn:exam:take', 'learn:assignment:create'],
          child: AssignmentListPage(),
        ),
      ),
      GoRoute(
        path: '/assignments/create',
        builder: (context, state) => const PermissionGate(
          anyOf: ['learn:assignment:create'],
          child: AssignmentCreatePage(),
        ),
      ),
      GoRoute(
        path: '/assignments/:assignmentId/grading',
        builder: (context, state) {
          final assignmentId =
              int.tryParse(state.pathParameters['assignmentId'] ?? '');
          if (assignmentId == null) return const AssignmentListPage();
          return PermissionGate(
            anyOf: const ['learn:exam:grade'],
            child: AssignmentGradingPage(assignmentId: assignmentId),
          );
        },
      ),
      GoRoute(
        path: '/assignments/:assignmentId',
        builder: (context, state) {
          final assignmentId =
              int.tryParse(state.pathParameters['assignmentId'] ?? '');
          if (assignmentId == null) return const AssignmentListPage();
          return PermissionGate(
            anyOf: const ['learn:exam:take', 'learn:assignment:create'],
            child: AssignmentDetailPage(assignmentId: assignmentId),
          );
        },
      ),
      GoRoute(
        path: '/teacher/classes/:classId/stats',
        builder: (context, state) {
          final classId = int.tryParse(state.pathParameters['classId'] ?? '');
          if (classId == null) return const TeacherClassesPage();
          final query = state.uri.queryParameters;
          return PermissionGate(
            anyOf: const ['learn:stats:class:read'],
            child: ClassStatsPage(
              classId: classId,
              className: query['name'] ?? '班级',
              grade: int.tryParse(query['grade'] ?? ''),
            ),
          );
        },
      ),
      GoRoute(
        path: '/knowledge/:textbookId/graph',
        builder: (context, state) {
          final textbookId = int.tryParse(state.pathParameters['textbookId'] ?? '');
          if (textbookId == null) return const AppShell();
          return PermissionGate(
            anyOf: const ['learn:kp:study'],
            child: KnowledgeGraphPage(
              textbookId: textbookId,
              textbookName: state.uri.queryParameters['name'] ?? '教材',
            ),
          );
        },
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
              textbookId: int.tryParse(query['tid'] ?? ''),
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
        path: '/practice/config',
        builder: (context, state) {
          final qp = state.uri.queryParameters;
          final ids = (qp['ids'] ?? '')
              .split(',')
              .map(int.tryParse)
              .whereType<int>()
              .toList();
          return PermissionGate(
            anyOf: const ['learn:practice:start'],
            child: PracticeConfigPage(
              scopeType: qp['scope'] ?? 'kp',
              scopeIds: ids,
              title: qp['title'] ?? '智能练习',
              chapterId: int.tryParse(qp['chapter'] ?? ''),
              textbookId: int.tryParse(qp['textbook'] ?? ''),
              initialMode: qp['mode'] ?? 'special',
            ),
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
              sessionId: int.tryParse(qp['session'] ?? ''),
              scopeType: qp['scope'],
              scopeIds: (qp['ids'] ?? '')
                  .split(',')
                  .map(int.tryParse)
                  .whereType<int>()
                  .toList(),
              count: int.tryParse(qp['count'] ?? '') ?? 10,
              qTypes: (qp['qtypes'] ?? '')
                  .split(',')
                  .where((item) => item.isNotEmpty)
                  .toList(),
              mode: qp['mode'] ?? 'special',
              seed: int.tryParse(qp['seed'] ?? ''),
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
    final storage = ref.watch(platformPalProvider).storage;
    return ConsentGate(
      storage: storage,
      child: MaterialApp.router(
        title: '深爱学',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1E6FD9)),
          scaffoldBackgroundColor: const Color(0xFFF7F9FC),
        ),
        routerConfig: router,
      ),
    );
  }
}
