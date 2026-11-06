import 'package:ai_learning/core/models/user.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/features/common/permission_gate.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

AppUser _user({List<String> permissions = const []}) {
  return AppUser(
    id: 1,
    phone: '13900000000',
    nickname: '测试学生',
    role: 'student',
    grade: 3,
    permissions: permissions,
  );
}

Widget _app(AppUser? user, {List<String> anyOf = const ['learn:exam:take']}) {
  return ProviderScope(
    overrides: [currentUserProvider.overrideWith((ref) => user)],
    child: MaterialApp.router(
      routerConfig: GoRouter(
        initialLocation: '/protected',
        routes: [
          GoRoute(
            path: '/protected',
            builder: (context, state) => PermissionGate(
              anyOf: anyOf,
              child: const Scaffold(body: Text('受保护内容')),
            ),
          ),
          GoRoute(
            path: '/shell',
            builder: (context, state) =>
                const Scaffold(body: Text('学习首页')),
          ),
        ],
      ),
    ),
  );
}

void main() {
  group('PermissionGate', () {
    testWidgets('命中任一权限点即放行', (tester) async {
      await tester.pumpWidget(
        _app(_user(permissions: const ['learn:exam:take'])),
      );
      await tester.pumpAndSettle();

      expect(find.text('受保护内容'), findsOneWidget);
      expect(find.text('无权限访问'), findsNothing);
    });

    testWidgets('无权限点展示 403 页', (tester) async {
      await tester.pumpWidget(
        _app(_user(permissions: const ['learn:practice:start'])),
      );
      await tester.pumpAndSettle();

      expect(find.text('受保护内容'), findsNothing);
      expect(find.text('无权限访问'), findsOneWidget);
    });

    testWidgets('超管 `*` 直接放行', (tester) async {
      await tester.pumpWidget(_app(_user(permissions: const ['*'])));
      await tester.pumpAndSettle();

      expect(find.text('受保护内容'), findsOneWidget);
    });

    testWidgets('未登录按 fallback 处理', (tester) async {
      await tester.pumpWidget(_app(null));
      await tester.pumpAndSettle();

      expect(find.text('受保护内容'), findsNothing);
      expect(find.text('无权限访问'), findsNothing);
    });

    testWidgets('anyOf 为空视为不限制', (tester) async {
      await tester.pumpWidget(
        _app(_user(permissions: const ['learn:practice:start']), anyOf: const []),
      );
      await tester.pumpAndSettle();

      expect(find.text('受保护内容'), findsOneWidget);
    });
  });

  group('AppUser 权限判定', () {
    test('hasPermission/hasAnyPermission 包含超管短路', () {
      final student = _user(permissions: const ['learn:content:read']);
      expect(student.hasPermission('learn:content:read'), isTrue);
      expect(student.hasPermission('learn:exam:take'), isFalse);
      expect(
        student.hasAnyPermission(const ['learn:exam:take', 'learn:content:read']),
        isTrue,
      );

      final admin = _user(permissions: const ['*']);
      expect(admin.isSuperAdmin, isTrue);
      expect(admin.hasPermission('content:exam:write'), isTrue);
    });
  });
}
