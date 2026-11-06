import 'package:ai_learning/core/models/rbac.dart';
import 'package:ai_learning/core/models/user.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/rbac_service.dart';
import 'package:ai_learning/features/admin/rbac_config_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const _admin = AppUser(
  id: 1,
  phone: '13800000000',
  nickname: '管理员',
  role: 'super_admin',
  permissions: ['*'],
);

const _roles = [
  RolePermissionEntry(
    code: 'student',
    name: '学生',
    level: 'L4',
    isSystem: true,
    isEditable: true,
    userCount: 12,
    permissions: ['learn:content:read'],
  ),
  RolePermissionEntry(
    code: 'teacher',
    name: '教师',
    level: 'L2',
    isSystem: true,
    isEditable: true,
    userCount: 3,
    permissions: ['learn:stats:class:read'],
  ),
  RolePermissionEntry(
    code: 'super_admin',
    name: '超级管理员',
    level: 'L1',
    isSystem: true,
    isEditable: false,
    userCount: 1,
    permissions: ['*'],
  ),
];

const _catalog = PermissionCatalog(
  domains: ['learn'],
  items: [
    PermissionCatalogItem(
      code: 'learn:content:read',
      domain: 'learn',
      description: '查看教材与知识点',
      roles: ['student'],
    ),
    PermissionCatalogItem(
      code: 'learn:stats:class:read',
      domain: 'learn',
      description: '查看班级学情',
      roles: ['teacher'],
    ),
  ],
);

class _FakeRbacService extends RbacService {
  _FakeRbacService() : super(ApiClient());

  List<RolePermissionEntry> rolesResult = _roles;
  PermissionCatalog catalogResult = _catalog;
  String? updatedRoleCode;
  List<String>? updatedPermissions;

  @override
  Future<List<RolePermissionEntry>> roles() async => rolesResult;

  @override
  Future<PermissionCatalog> permissions() async => catalogResult;

  @override
  Future<RolePermissionUpdateResult> updateRolePermissions(
    String roleCode,
    List<String> permissions,
  ) async {
    updatedRoleCode = roleCode;
    updatedPermissions = permissions;
    final before = rolesResult
        .firstWhere((item) => item.code == roleCode)
        .permissions
        .toSet();
    final after = permissions.toSet();
    return RolePermissionUpdateResult(
      code: roleCode,
      permissions: permissions,
      added: after.difference(before).toList(),
      removed: before.difference(after).toList(),
    );
  }
}

Widget _app(_FakeRbacService fake) {
  return ProviderScope(
    overrides: [
      currentUserProvider.overrideWith((ref) => _admin),
      rbacServiceProvider.overrideWithValue(fake),
    ],
    child: const MaterialApp(home: RbacConfigPage()),
  );
}

void main() {
  testWidgets('切换角色并按权限点保存', (tester) async {
    final fake = _FakeRbacService();
    await tester.pumpWidget(_app(fake));
    await tester.pumpAndSettle();

    expect(find.text('学生 L4'), findsOneWidget);
    final contentTile = tester.widget<CheckboxListTile>(
      find.byKey(const ValueKey('perm-learn:content:read')),
    );
    expect(contentTile.value, isTrue);
    expect(tester.widget<FilledButton>(find.byKey(const ValueKey('save-permissions'))).onPressed,
        isNull);

    await tester.tap(find.byKey(const ValueKey('role-chip-teacher')));
    await tester.pumpAndSettle();
    final statsTile = tester.widget<CheckboxListTile>(
      find.byKey(const ValueKey('perm-learn:stats:class:read')),
    );
    expect(statsTile.value, isTrue);

    await tester.tap(find.byKey(const ValueKey('perm-learn:content:read')));
    await tester.pumpAndSettle();
    expect(tester.widget<FilledButton>(find.byKey(const ValueKey('save-permissions'))).onPressed,
        isNotNull);

    await tester.tap(find.byKey(const ValueKey('save-permissions')));
    await tester.pumpAndSettle();

    expect(fake.updatedRoleCode, 'teacher');
    expect(fake.updatedPermissions, contains('learn:content:read'));
    expect(find.text('已保存：新增 1，回收 0'), findsOneWidget);
  });

  testWidgets('超管角色只读不可调整', (tester) async {
    final fake = _FakeRbacService();
    await tester.pumpWidget(_app(fake));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('role-chip-super_admin')));
    await tester.pumpAndSettle();

    expect(find.text('超管固定拥有全部权限（*），不可调整。'), findsOneWidget);
    final tile = tester.widget<CheckboxListTile>(
      find.byKey(const ValueKey('perm-learn:content:read')),
    );
    expect(tile.onChanged, isNull);
    expect(tester.widget<FilledButton>(find.byKey(const ValueKey('save-permissions'))).onPressed,
        isNull);
  });
}
