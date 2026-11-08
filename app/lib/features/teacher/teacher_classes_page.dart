import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/org.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/theme/app_accents.dart';
import 'package:ai_learning/widgets/accent_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 教师中心（P1-06）：授课/班主任班级概览。
class TeacherClassesPage extends ConsumerStatefulWidget {
  const TeacherClassesPage({super.key});

  @override
  ConsumerState<TeacherClassesPage> createState() => _TeacherClassesPageState();
}

class _TeacherClassesPageState extends ConsumerState<TeacherClassesPage> {
  List<ClassSummary> _classes = const [];
  bool _loading = true;
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
      final classes = await ref.read(orgServiceProvider).classes();
      if (!mounted) return;
      setState(() {
        _classes = classes;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loading = false;
      });
    }
  }

  void _openClass(ClassSummary item) {
    final query = {'name': item.name, 'grade': '${item.grade}'};
    final uri = Uri(
      path: '/teacher/classes/${item.id}/stats',
      queryParameters: query,
    );
    context.push(uri.toString());
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accents = AppAccents.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('教师中心'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () =>
              context.canPop() ? context.pop() : context.go('/shell'),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (_error != null)
                    Card(
                      color: theme.colorScheme.errorContainer,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Text(_error!, style: theme.textTheme.bodyMedium),
                      ),
                    ),
                  if (!_loading && _error == null && _classes.isEmpty)
                    const Card(
                      child: Padding(
                        padding: EdgeInsets.all(20),
                        child: Text(
                          '还没有可查看的班级。请联系学校管理员完成班级创建，'
                          '并将你设置为本班班主任或分配授课。',
                        ),
                      ),
                    ),
                  ..._classes.map(
                    (item) => AccentCard(
                      accent: accents.learn,
                      margin: const EdgeInsets.only(bottom: 12),
                      child: ListTile(
                        leading: CircleAvatar(
                          backgroundColor: theme.colorScheme.primaryContainer,
                          child: Icon(
                            Icons.school_outlined,
                            color: theme.colorScheme.primary,
                          ),
                        ),
                        title: Text(item.label),
                        subtitle: Text(
                          '${item.memberCount} 名学生 · ${item.schoolYear} 学年',
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => _openClass(item),
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
