import 'package:ai_learning/core/models/org.dart';
import 'package:ai_learning/core/models/user.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/org_service.dart';
import 'package:ai_learning/features/teacher/class_stats_page.dart';
import 'package:ai_learning/features/teacher/teacher_classes_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

const _teacher = AppUser(
  id: 21,
  phone: '13700000000',
  nickname: '王老师',
  role: 'teacher',
  permissions: ['learn:stats:class:read'],
);

class _FakeOrgService extends OrgService {
  _FakeOrgService({this.classList = const [], this.stats}) : super(ApiClient());

  final List<ClassSummary> classList;
  final ClassStats? stats;

  @override
  Future<List<ClassSummary>> classes() async => classList;

  @override
  Future<ClassStats> classStats(int classId, {String? subject}) async {
    return stats ??
        ClassStats(
          classId: classId,
          className: '1 班',
          grade: 6,
          studentCount: 0,
          activeStudentCount: 0,
          submissionRate: 0,
          totalAnswered: 0,
          accuracy: 0,
          avgMastery: 0,
        );
  }
}

Widget _classesApp(_FakeOrgService fake) {
  return ProviderScope(
    overrides: [
      currentUserProvider.overrideWith((ref) => _teacher),
      orgServiceProvider.overrideWithValue(fake),
    ],
    child: MaterialApp.router(
      routerConfig: GoRouter(
        initialLocation: '/teacher/classes',
        routes: [
          GoRoute(
            path: '/teacher/classes',
            builder: (context, state) => const TeacherClassesPage(),
          ),
          GoRoute(
            path: '/teacher/classes/:classId/stats',
            builder: (context, state) =>
                const Scaffold(body: Text('班级学情页')),
          ),
        ],
      ),
    ),
  );
}

void main() {
  testWidgets('展示教师可见班级并进入学情页', (tester) async {
    tester.view.physicalSize = const Size(1000, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      _classesApp(
        _FakeOrgService(
          classList: const [
            ClassSummary(
              id: 8,
              schoolId: 3,
              grade: 6,
              name: '1 班',
              schoolYear: '2026-2027',
              memberCount: 40,
            ),
            ClassSummary(
              id: 9,
              schoolId: 3,
              grade: 6,
              name: '2 班',
              schoolYear: '2026-2027',
              memberCount: 38,
            ),
          ],
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('教师中心'), findsOneWidget);
    expect(find.text('6 年级 1 班'), findsOneWidget);
    expect(find.text('40 名学生 · 2026-2027 学年'), findsOneWidget);
    expect(find.text('6 年级 2 班'), findsOneWidget);

    await tester.tap(find.text('6 年级 1 班'));
    await tester.pumpAndSettle();

    expect(find.text('班级学情页'), findsOneWidget);
  });

  testWidgets('无班级时展示引导文案', (tester) async {
    tester.view.physicalSize = const Size(1000, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_classesApp(_FakeOrgService()));
    await tester.pumpAndSettle();

    expect(find.textContaining('还没有可查看的班级'), findsOneWidget);
  });

  testWidgets('班级学情页展示聚合指标与薄弱知识点', (tester) async {
    tester.view.physicalSize = const Size(1000, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          currentUserProvider.overrideWith((ref) => _teacher),
          orgServiceProvider.overrideWithValue(
            _FakeOrgService(
              stats: const ClassStats(
                classId: 8,
                className: '1 班',
                grade: 6,
                studentCount: 40,
                activeStudentCount: 32,
                submissionRate: 0.8,
                totalAnswered: 1200,
                accuracy: 0.825,
                avgMastery: 61,
                weakPoints: [
                  ClassWeakPoint(
                    knowledgePointId: 101,
                    name: '分数乘法',
                    subject: 'math',
                    avgMastery: 42.5,
                  ),
                ],
              ),
            ),
          ),
        ],
        child: const MaterialApp(
          home: ClassStatsPage(classId: 8, className: '1 班'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('1 班 · 班级学情'), findsOneWidget);
    expect(find.text('40'), findsOneWidget);
    expect(find.text('32'), findsOneWidget);
    expect(find.text('83%'), findsOneWidget);
    expect(find.text('61'), findsOneWidget);
    expect(find.text('80%'), findsOneWidget);
    expect(find.text('数学 · 分数乘法'), findsOneWidget);
    expect(find.textContaining('不含学生个人信息'), findsOneWidget);
  });
}
