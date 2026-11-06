import 'package:ai_learning/core/models/rbac.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 权限配置后台：按角色查看/勾选权限点，保存后写入 role_permissions 并留审计。
class RbacConfigPage extends ConsumerStatefulWidget {
  const RbacConfigPage({super.key});

  @override
  ConsumerState<RbacConfigPage> createState() => _RbacConfigPageState();
}

class _RbacConfigPageState extends ConsumerState<RbacConfigPage> {
  List<RolePermissionEntry> _roles = const [];
  PermissionCatalog? _catalog;
  String? _selectedCode;
  Set<String> _draft = {};
  bool _loading = true;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final service = ref.read(rbacServiceProvider);
      final results = await Future.wait([service.roles(), service.permissions()]);
      final roles = results[0] as List<RolePermissionEntry>;
      final catalog = results[1] as PermissionCatalog;
      if (!mounted) return;
      final selected = _selectedCode != null &&
              roles.any((item) => item.code == _selectedCode)
          ? _selectedCode!
          : (roles.isNotEmpty ? roles.first.code : null);
      setState(() {
        _roles = roles;
        _catalog = catalog;
        _loading = false;
        _selectRole(selected);
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = '$error';
      });
    }
  }

  void _selectRole(String? code) {
    _selectedCode = code;
    final selected = _selectedRole;
    _draft = {...?selected?.permissions};
  }

  RolePermissionEntry? get _selectedRole {
    for (final role in _roles) {
      if (role.code == _selectedCode) return role;
    }
    return null;
  }

  bool get _dirty {
    final selected = _selectedRole;
    if (selected == null) return false;
    return !_sameSet(_draft, selected.permissions.toSet());
  }

  bool _sameSet(Set<String> left, Set<String> right) {
    if (left.length != right.length) return false;
    for (final item in left) {
      if (!right.contains(item)) return false;
    }
    return true;
  }

  Future<void> _save() async {
    final selected = _selectedRole;
    if (selected == null || !selected.isEditable || _saving) return;
    setState(() => _saving = true);
    try {
      final result = await ref
          .read(rbacServiceProvider)
          .updateRolePermissions(selected.code, _draft.toList()..sort());
      if (!mounted) return;
      setState(() {
        _roles = [
          for (final role in _roles)
            if (role.code == selected.code)
              RolePermissionEntry(
                code: role.code,
                name: role.name,
                level: role.level,
                isSystem: role.isSystem,
                isEditable: role.isEditable,
                userCount: role.userCount,
                permissions: result.permissions,
              )
            else
              role,
        ];
        _draft = result.permissions.toSet();
        _saving = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '已保存：新增 ${result.added.length}，回收 ${result.removed.length}',
          ),
        ),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('保存失败：$error')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('角色权限配置')),
      body: _buildBody(context),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        child: FilledButton(
          key: const ValueKey('save-permissions'),
          onPressed: (_dirty && !_saving && (_selectedRole?.isEditable ?? false))
              ? _save
              : null,
          child: Text(_saving ? '保存中…' : '保存配置'),
        ),
      ),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('加载失败：$_error', textAlign: TextAlign.center),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: _load, child: const Text('重试')),
          ],
        ),
      );
    }
    final catalog = _catalog;
    final selected = _selectedRole;
    if (catalog == null || selected == null) {
      return const Center(child: Text('暂无可配置角色'));
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: 52,
          child: ListView.separated(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            scrollDirection: Axis.horizontal,
            itemCount: _roles.length,
            separatorBuilder: (_, _) => const SizedBox(width: 8),
            itemBuilder: (context, index) {
              final role = _roles[index];
              return ChoiceChip(
                key: ValueKey('role-chip-${role.code}'),
                selected: role.code == _selectedCode,
                label: Text('${role.name} ${role.level}'),
                onSelected: (_) => setState(() => _selectRole(role.code)),
              );
            },
          ),
        ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
            children: [
              Card(
                child: ListTile(
                  leading: CircleAvatar(child: Text(selected.level)),
                  title: Text('${selected.name}（${selected.code}）'),
                  subtitle: Text(
                    '${selected.userCount} 位用户 · ${selected.permissions.length} 项权限',
                  ),
                ),
              ),
              if (!selected.isEditable)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: Text('超管固定拥有全部权限（*），不可调整。'),
                ),
              for (final domain in catalog.domains) ..._domainSection(domain),
            ],
          ),
        ),
      ],
    );
  }

  List<Widget> _domainSection(String domain) {
    final selected = _selectedRole;
    final items = _catalog?.byDomain(domain) ?? const [];
    if (items.isEmpty) return const [];
    final editable = selected?.isEditable ?? false;
    return [
      Padding(
        padding: const EdgeInsets.only(top: 16, bottom: 4),
        child: Text(
          domain,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: Theme.of(context).colorScheme.primary,
              ),
        ),
      ),
      for (final item in items)
        CheckboxListTile(
          key: ValueKey('perm-${item.code}'),
          dense: true,
          controlAffinity: ListTileControlAffinity.leading,
          value: _draft.contains(item.code),
          title: Text(item.code, style: const TextStyle(fontSize: 13)),
          subtitle: item.description == null ? null : Text(item.description!),
          onChanged: editable
              ? (checked) => setState(() {
                    if (checked ?? false) {
                      _draft.add(item.code);
                    } else {
                      _draft.remove(item.code);
                    }
                  })
              : null,
        ),
    ];
  }
}
