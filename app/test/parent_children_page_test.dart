import 'package:ai_learning/core/models/family.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:ai_learning/core/models/user.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/family_service.dart';
import 'package:ai_learning/core/services/learn_service.dart';
import 'package:ai_learning/features/family/parent_children_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const _parent = AppUser(
  id: 100,
  phone: '13800000000',
  nickname: '家长',
  role: 'parent',
  permissions: ['learn:stats:child:read', 'family:report:read'],
);

class _FakeFamilyService extends FamilyService {
  _FakeFamilyService(this._children) : super(ApiClient());

  final List<FamilyChild> _children;
  int? lastUpdatedChildId;
  int? lastDailyLimit;
  bool? lastTeenMode;

  @override
  Future<List<FamilyChild>> children() async => _children;

  @override
  Future<FamilyChild> updateControls(
    int childId, {
    int? dailyLimitMinutes,
    bool? teenMode,
  }) async {
    lastUpdatedChildId = childId;
    lastDailyLimit = dailyLimitMinutes;
    lastTeenMode = teenMode;
    final base = _children.firstWhere((child) => child.id == childId);
    return FamilyChild(
      id: base.id,
      nickname: base.nickname,
      stage: base.stage,
      grade: base.grade,
      gradeGroup: base.gradeGroup,
      isChild: base.isChild,
      dailyLimitMinutes: dailyLimitMinutes ?? base.dailyLimitMinutes,
      teenMode: teenMode ?? base.teenMode,
    );
  }
}

class _FakeLearnService extends LearnService {
  _FakeLearnService() : super(ApiClient());

  List<int?> requestedStudentIds = [];

  @override
  Future<LearnStats> stats({int? studentId}) async {
    requestedStudentIds.add(studentId);
    return LearnStats(
      totalAnswered: studentId == 2 ? 20 : 10,
      totalCorrect: 8,
      accuracy: 0.8,
      streakDays: studentId == 2 ? 6 : 3,
      dueReviewCount: 0,
      activeWrongCount: 1,
    );
  }
}

Widget _app(List<FamilyChild> children, {_FakeFamilyService? service}) {
  final fake = service ?? _FakeFamilyService(children);
  return ProviderScope(
    overrides: [
      currentUserProvider.overrideWith((ref) => _parent),
      familyServiceProvider.overrideWithValue(fake),
      learnServiceProvider.overrideWithValue(_FakeLearnService()),
    ],
    child: const MaterialApp(home: ParentChildrenPage()),
  );
}

void main() {
  testWidgets('加载孩子并展示学情与家长控制', (tester) async {
    tester.view.physicalSize = const Size(1000, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      _app(const [
        FamilyChild(id: 1, nickname: '小明', grade: 3, dailyLimitMinutes: 120),
        FamilyChild(id: 2, nickname: '小华', grade: 4, teenMode: true),
      ]),
    );
    await tester.pumpAndSettle();

    expect(find.text('家长中心'), findsOneWidget);
    expect(find.text('小明'), findsWidgets);
    expect(find.text('小华'), findsOneWidget);
    expect(find.text('10'), findsOneWidget);
    expect(find.text('每日学习时长：120 分钟'), findsOneWidget);
  });

  testWidgets('切换孩子后按 studentId 拉取学情', (tester) async {
    tester.view.physicalSize = const Size(1000, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      _app(const [
        FamilyChild(id: 1, nickname: '小明', grade: 3),
        FamilyChild(id: 2, nickname: '小华', grade: 4, teenMode: true),
      ]),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('小华'));
    await tester.pumpAndSettle();

    expect(find.text('20'), findsOneWidget);
    expect(find.text('每日学习时长：120 分钟'), findsOneWidget);
  });

  testWidgets('保存家长控制并提示成功', (tester) async {
    tester.view.physicalSize = const Size(1000, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final fake = _FakeFamilyService(const [
      FamilyChild(id: 1, nickname: '小明', grade: 3, dailyLimitMinutes: 120),
    ]);
    await tester.pumpWidget(_app(const [], service: fake));
    await tester.pumpAndSettle();

    await tester.tap(find.byType(Switch));
    await tester.pumpAndSettle();
    await tester.tap(find.text('保存设置'));
    await tester.pumpAndSettle();

    expect(fake.lastUpdatedChildId, 1);
    expect(fake.lastDailyLimit, 120);
    expect(fake.lastTeenMode, isTrue);
    expect(find.text('已保存家长设置'), findsOneWidget);
  });

  testWidgets('未绑定孩子时展示引导文案', (tester) async {
    tester.view.physicalSize = const Size(1000, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_app(const []));
    await tester.pumpAndSettle();

    expect(find.textContaining('还没有已绑定的孩子'), findsOneWidget);
    expect(find.text('保存设置'), findsNothing);
  });
}
