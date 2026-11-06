import 'package:ai_learning/core/models/rbac.dart';
import 'package:ai_learning/core/services/api_client.dart';

class RbacService {
  RbacService(this._api);

  final ApiClient _api;

  Future<List<RolePermissionEntry>> roles() async {
    final data = await _api.getJson('/api/admin/rbac/roles');
    return (data['items'] as List<dynamic>? ?? const [])
        .map((item) => RolePermissionEntry.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<PermissionCatalog> permissions() async {
    return PermissionCatalog.fromJson(
      await _api.getJson('/api/admin/rbac/permissions'),
    );
  }

  Future<RolePermissionUpdateResult> updateRolePermissions(
    String roleCode,
    List<String> permissions,
  ) async {
    final data = await _api.putJson(
      '/api/admin/rbac/roles/$roleCode/permissions',
      {'permissions': permissions},
    );
    return RolePermissionUpdateResult.fromJson(data);
  }
}
