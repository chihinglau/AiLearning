class RolePermissionEntry {
  const RolePermissionEntry({
    required this.code,
    required this.name,
    required this.level,
    required this.isSystem,
    required this.isEditable,
    required this.userCount,
    required this.permissions,
  });

  final String code;
  final String name;
  final String level;
  final bool isSystem;
  final bool isEditable;
  final int userCount;
  final List<String> permissions;

  factory RolePermissionEntry.fromJson(Map<String, dynamic> json) {
    return RolePermissionEntry(
      code: json['code'] as String? ?? '',
      name: json['name'] as String? ?? '',
      level: json['level'] as String? ?? '',
      isSystem: json['is_system'] as bool? ?? true,
      isEditable: json['is_editable'] as bool? ?? false,
      userCount: json['user_count'] as int? ?? 0,
      permissions: (json['permissions'] as List<dynamic>? ?? const [])
          .map((item) => item as String)
          .toList(),
    );
  }
}

class PermissionCatalogItem {
  const PermissionCatalogItem({
    required this.code,
    required this.domain,
    this.description,
    required this.roles,
  });

  final String code;
  final String domain;
  final String? description;
  final List<String> roles;

  factory PermissionCatalogItem.fromJson(Map<String, dynamic> json) {
    return PermissionCatalogItem(
      code: json['code'] as String? ?? '',
      domain: json['domain'] as String? ?? '',
      description: json['description'] as String?,
      roles: (json['roles'] as List<dynamic>? ?? const [])
          .map((item) => item as String)
          .toList(),
    );
  }
}

class PermissionCatalog {
  const PermissionCatalog({required this.domains, required this.items});

  final List<String> domains;
  final List<PermissionCatalogItem> items;

  factory PermissionCatalog.fromJson(Map<String, dynamic> json) {
    return PermissionCatalog(
      domains: (json['domains'] as List<dynamic>? ?? const [])
          .map((item) => item as String)
          .toList(),
      items: (json['items'] as List<dynamic>? ?? const [])
          .map((item) => PermissionCatalogItem.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  List<PermissionCatalogItem> byDomain(String domain) {
    return items.where((item) => item.domain == domain).toList();
  }
}

class RolePermissionUpdateResult {
  const RolePermissionUpdateResult({
    required this.code,
    required this.permissions,
    required this.added,
    required this.removed,
  });

  final String code;
  final List<String> permissions;
  final List<String> added;
  final List<String> removed;

  factory RolePermissionUpdateResult.fromJson(Map<String, dynamic> json) {
    return RolePermissionUpdateResult(
      code: json['code'] as String? ?? '',
      permissions: (json['permissions'] as List<dynamic>? ?? const [])
          .map((item) => item as String)
          .toList(),
      added: (json['added'] as List<dynamic>? ?? const [])
          .map((item) => item as String)
          .toList(),
      removed: (json['removed'] as List<dynamic>? ?? const [])
          .map((item) => item as String)
          .toList(),
    );
  }
}
