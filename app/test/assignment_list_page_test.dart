import 'package:ai_learning/core/models/assignment.dart';
import 'package:ai_learning/core/models/user.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/assignment_service.dart';
import 'package:ai_learning/features/assignment/assignment_list_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const _student = AppUser(
  id: 7,
  phone: '13900000000',
  nickname: '小明',
  role: 'student',
  permissions: ['learn:exam:take'],
);

const _teacher = AppUser(
  id: 3,
  phone: '13800000003',
  nickname: '王老师',
  role: 'teacher',
  permissions: ['learn:assignment:create', 'learn:exam:grade'],
);

const _items = [
  AssignmentInfo(
    id: 1,
    title: '第 1 单元课后作业',
    subject: 'math',
    classId: 10,
    className: '一年级 1 班',
    examId: 21,
    studentCount: 12,
    submittedCount: 12,
    pendingGrading: 3,
    myAttemptId: 31,
    myStatus: 'completed',
    myTotalScore: 88,
  ),
  AssignmentInfo(
    id: 2,
    title: '口算专项练习',
    subject: 'math',
    classId: 10,
    className: '一年级 1 班',
    examId: 22,
    studentCount: 12,
    submittedCount: 4,
    myStatus: null,
  ),
];

class _FakeAssignmentService extends AssignmentService {
  _FakeAssignmentService() : super(ApiClient());

  List<AssignmentInfo> result = _items;

  @override
  Future<List<AssignmentInfo>> list() async => result;
}

Widget _app(_FakeAssignmentService fake, {required AppUser user}) {
  return ProviderScope(
    overrides: [
      currentUserProvider.overrideWith((ref) => user),
      assignmentServiceProvider.overrideWithValue(fake),
    ],
    child: const MaterialApp(home: AssignmentListPage()),
  );
}

void main() {
  testWidgets('学生查看作业状态与得分', (tester) async {
    final fake = _FakeAssignmentService();
    await tester.pumpWidget(_app(fake, user: _student));
    await tester.pumpAndSettle();

    expect(find.text('第 1 单元课后作业'), findsOneWidget);
    expect(find.text('口算专项练习'), findsOneWidget);
    expect(find.text('已完成'), findsOneWidget);
    expect(find.text('未开始'), findsOneWidget);
    expect(find.textContaining('得分 88'), findsOneWidget);
    expect(find.byKey(const ValueKey('create-assignment-fab')), findsNothing);
  });

  testWidgets('教师看到待批改与布置入口', (tester) async {
    final fake = _FakeAssignmentService();
    await tester.pumpWidget(_app(fake, user: _teacher));
    await tester.pumpAndSettle();

    expect(find.text('待批改 3'), findsOneWidget);
    expect(find.textContaining('提交 12/12'), findsOneWidget);
    expect(find.byKey(const ValueKey('create-assignment-fab')), findsOneWidget);
  });
}
