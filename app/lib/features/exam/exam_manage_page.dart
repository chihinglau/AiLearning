import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 考试入库（D-04 §8.7.3）：按蓝图组卷发布，并把新卷派发为班级同卷模考。
class ExamManagePage extends ConsumerStatefulWidget {
  const ExamManagePage({super.key});

  @override
  ConsumerState<ExamManagePage> createState() => _ExamManagePageState();
}

class _ExamManagePageState extends ConsumerState<ExamManagePage> {
  final _title = TextEditingController();
  final _chapters = TextEditingController();
  final _seed = TextEditingController();
  final _mockExamId = TextEditingController();
  final _classId = TextEditingController();

  List<ExamBlueprint> _blueprints = [];
  String? _blueprintCode;
  bool _isPastPaper = false;
  bool _loading = true;
  bool _busy = false;
  String? _error;
  ExamGenerateResult? _result;
  MockExamAssignment? _assignment;

  @override
  void initState() {
    super.initState();
    _loadBlueprints();
  }

  @override
  void dispose() {
    _title.dispose();
    _chapters.dispose();
    _seed.dispose();
    _mockExamId.dispose();
    _classId.dispose();
    super.dispose();
  }

  Future<void> _loadBlueprints() async {
    try {
      final items = await ref.read(examServiceProvider).blueprints();
      if (!mounted) return;
      setState(() {
        _blueprints = items;
        _blueprintCode = items.isEmpty ? null : items.first.code;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  List<int> _chapterIds() => _chapters.text
      .split(RegExp(r'[,，\s]+'))
      .map(int.tryParse)
      .whereType<int>()
      .toList();

  void _snack(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _generate() async {
    final code = _blueprintCode;
    final chapters = _chapterIds();
    if (code == null || code.isEmpty) {
      _snack('请先选择组卷蓝图');
      return;
    }
    if (chapters.isEmpty) {
      _snack('请填写至少一个章节 ID（逗号分隔）');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final title = _title.text.trim();
      final result = await ref.read(examServiceProvider).generateExam(
            blueprintCode: code,
            chapterIds: chapters,
            title: title.isEmpty ? null : title,
            seed: int.tryParse(_seed.text.trim()),
            isPastPaper: _isPastPaper,
          );
      if (!mounted) return;
      setState(() {
        _result = result;
        _mockExamId.text = '${result.examId}';
        _busy = false;
      });
      _snack('试卷已发布，ID ${result.examId}');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _busy = false;
      });
      _snack('发布失败：$e');
    }
  }

  Future<void> _assign() async {
    final examId = int.tryParse(_mockExamId.text.trim());
    final classId = int.tryParse(_classId.text.trim());
    if (examId == null || classId == null) {
      _snack('请填写有效的试卷 ID 与班级 ID');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final assignment = await ref
          .read(examServiceProvider)
          .assignClassMock(classId: classId, examId: examId);
      if (!mounted) return;
      setState(() {
        _assignment = assignment;
        _busy = false;
      });
      _snack('已派发到 ${assignment.studentCount} 名学生');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _busy = false;
      });
      _snack('派发失败：$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('考试管理与发布')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                const Card(
                  child: ListTile(
                    leading: Icon(Icons.info_outline),
                    title: Text('组卷入库'),
                    subtitle: Text(
                      '选择蓝图与章节范围生成试卷并发布；发布后学生可在考试中心看到，'
                      '真题仅在真题库展示。',
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  key: ValueKey(_blueprintCode),
                  initialValue: _blueprintCode,
                  decoration: const InputDecoration(
                    labelText: '组卷蓝图',
                    border: OutlineInputBorder(),
                  ),
                  items: [
                    for (final blueprint in _blueprints)
                      DropdownMenuItem<String>(
                        value: blueprint.code,
                        child: Text(
                          '${blueprint.name}（${blueprint.subject} · '
                          '${blueprint.totalScore}分）',
                        ),
                      ),
                  ],
                  onChanged: (value) =>
                      setState(() => _blueprintCode = value),
                ),
                if (_blueprints.isEmpty) ...[
                  const SizedBox(height: 8),
                  const Text('暂无可用蓝图，请先由内容管理员导入 exam_blueprints'),
                ],
                const SizedBox(height: 12),
                TextField(
                  controller: _title,
                  decoration: const InputDecoration(
                    labelText: '试卷标题（可选）',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _chapters,
                  decoration: const InputDecoration(
                    labelText: '章节 ID（必填，逗号分隔）',
                    hintText: '例如 1,2,3',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _seed,
                  decoration: const InputDecoration(
                    labelText: '组卷种子（可选）',
                    border: OutlineInputBorder(),
                  ),
                ),
                SwitchListTile(
                  value: _isPastPaper,
                  title: const Text('标记为历年真题'),
                  subtitle: const Text('真题不进入考试中心列表，仅真题库可见'),
                  onChanged: (value) => setState(() => _isPastPaper = value),
                ),
                const SizedBox(height: 8),
                FilledButton.icon(
                  onPressed: _busy ? null : _generate,
                  icon: const Icon(Icons.publish_outlined),
                  label: const Text('生成并发布试卷'),
                ),
                if (_result != null) ...[
                  const SizedBox(height: 16),
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.check_circle_outline),
                      title: Text(_result!.title),
                      subtitle: Text(
                        'ID ${_result!.examId} · ${_result!.questionCount} 题 · '
                        '${_result!.totalScore.toStringAsFixed(0)} 分 · '
                        'KP 覆盖 ${(_result!.kpCoverage * 100).toStringAsFixed(0)}% · '
                        '兜底 ${_result!.fallbackCount} 题'
                        '${_result!.insufficient ? ' · 题量不足' : ''}',
                      ),
                    ),
                  ),
                ],
                const Divider(height: 32),
                const Text(
                  '派发班级同卷模考',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _mockExamId,
                  decoration: const InputDecoration(
                    labelText: '试卷 ID',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _classId,
                  decoration: const InputDecoration(
                    labelText: '班级 ID',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: _busy ? null : _assign,
                  icon: const Icon(Icons.group_add_outlined),
                  label: const Text('派发到班级'),
                ),
                if (_assignment != null) ...[
                  const SizedBox(height: 12),
                  Card(
                    child: ListTile(
                      leading: const Icon(Icons.done_all),
                      title: Text(_assignment!.title),
                      subtitle: Text(
                        '班级 ${_assignment!.classId} · '
                        '${_assignment!.studentCount} 名学生 · '
                        '${_assignment!.questionCount} 题',
                      ),
                    ),
                  ),
                ],
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text('错误：$_error', style: const TextStyle(color: Colors.red)),
                ],
                const SizedBox(height: 24),
              ],
            ),
    );
  }
}
