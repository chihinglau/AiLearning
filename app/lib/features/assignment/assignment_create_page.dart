import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/org.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 教师布置班级作业：选班级、学科、章节、题型与截止时间，后端统一组卷。
class AssignmentCreatePage extends ConsumerStatefulWidget {
  const AssignmentCreatePage({super.key});

  @override
  ConsumerState<AssignmentCreatePage> createState() => _AssignmentCreatePageState();
}

class _AssignmentCreatePageState extends ConsumerState<AssignmentCreatePage> {
  static const _qTypeOptions = {
    'choice': '单选',
    'fill': '填空',
    'answer': '主观题',
  };

  final _titleController = TextEditingController();
  List<ClassSummary> _classes = const [];
  List<Textbook> _textbooks = const [];
  List<Chapter> _chapters = const [];
  int? _classId;
  int? _textbookId;
  String _subject = 'math';
  final Set<int> _chapterIds = {};
  final Set<String> _qTypes = {'choice', 'answer'};
  int _count = 10;
  int _timeLimitMin = 30;
  int _dueDays = 7;
  bool _loading = true;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadClasses();
  }

  @override
  void dispose() {
    _titleController.dispose();
    super.dispose();
  }

  Future<void> _loadClasses() async {
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

  Future<void> _selectClass(int? classId) async {
    if (classId == null) return;
    final room = _classes.firstWhere((item) => item.id == classId);
    setState(() {
      _classId = classId;
      _textbookId = null;
      _textbooks = const [];
      _chapters = const [];
      _chapterIds.clear();
    });
    try {
      final textbooks = await ref
          .read(contentServiceProvider)
          .textbooks(subject: _subject, grade: room.grade);
      if (!mounted) return;
      setState(() => _textbooks = textbooks);
      if (textbooks.isNotEmpty) {
        await _selectTextbook(textbooks.first.id);
      }
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _error = ApiErrorGuide.from(error).message);
    }
  }

  Future<void> _selectTextbook(int? textbookId) async {
    if (textbookId == null) return;
    setState(() {
      _textbookId = textbookId;
      _chapters = const [];
      _chapterIds.clear();
    });
    try {
      final chapters = await ref.read(contentServiceProvider).chapters(textbookId);
      if (!mounted) return;
      setState(() => _chapters = chapters);
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _error = ApiErrorGuide.from(error).message);
    }
  }

  Future<void> _submit() async {
    final classId = _classId;
    final title = _titleController.text.trim();
    if (classId == null) {
      _showMessage('请先选择班级');
      return;
    }
    if (title.isEmpty) {
      _showMessage('请填写作业标题');
      return;
    }
    if (_chapterIds.isEmpty) {
      _showMessage('请至少选择一个章节');
      return;
    }
    if (_qTypes.isEmpty) {
      _showMessage('请至少选择一种题型');
      return;
    }
    setState(() => _submitting = true);
    try {
      final dueAt =
          DateTime.now().toUtc().add(Duration(days: _dueDays)).toIso8601String();
      final created = await ref.read(assignmentServiceProvider).create(
            classId: classId,
            title: title,
            subject: _subject,
            chapterIds: _chapterIds.toList(),
            count: _count,
            qTypes: _qTypes.toList(),
            timeLimitMin: _timeLimitMin,
            dueAt: dueAt,
          );
      if (!mounted) return;
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('已布置「${created.title}」')),
      );
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = ApiErrorGuide.from(error).message;
      });
    }
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('布置作业')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_error != null)
                  Card(
                    color: theme.colorScheme.errorContainer,
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(_error!, style: theme.textTheme.bodySmall),
                    ),
                  ),
                TextField(
                  key: const ValueKey('assignment-title'),
                  controller: _titleController,
                  decoration: const InputDecoration(
                    labelText: '作业标题',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<int>(
                  key: const ValueKey('assignment-class'),
                  initialValue: _classId,
                  decoration: const InputDecoration(
                    labelText: '班级',
                    border: OutlineInputBorder(),
                  ),
                  items: [
                    for (final item in _classes)
                      DropdownMenuItem(value: item.id, child: Text(item.label)),
                  ],
                  onChanged: _selectClass,
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  key: const ValueKey('assignment-subject'),
                  initialValue: _subject,
                  decoration: const InputDecoration(
                    labelText: '学科',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'math', child: Text('数学')),
                    DropdownMenuItem(value: 'chinese', child: Text('语文')),
                    DropdownMenuItem(value: 'english', child: Text('英语')),
                  ],
                  onChanged: (value) {
                    if (value == null) return;
                    setState(() => _subject = value);
                    if (_classId != null) _selectClass(_classId);
                  },
                ),
                const SizedBox(height: 12),
                if (_textbooks.isNotEmpty)
                  DropdownButtonFormField<int>(
                    key: const ValueKey('assignment-textbook'),
                    initialValue: _textbookId,
                    decoration: const InputDecoration(
                      labelText: '教材',
                      border: OutlineInputBorder(),
                    ),
                    items: [
                      for (final item in _textbooks)
                        DropdownMenuItem(value: item.id, child: Text(item.displayName)),
                    ],
                    onChanged: _selectTextbook,
                  ),
                const SizedBox(height: 12),
                Text('选择章节', style: theme.textTheme.titleSmall),
                const SizedBox(height: 4),
                if (_chapters.isEmpty)
                  Text(
                    _classId == null ? '请先选择班级' : '该教材暂无章节',
                    style: theme.textTheme.bodySmall,
                  )
                else
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: [
                      for (final chapter in _chapters)
                        FilterChip(
                          key: ValueKey('chapter-${chapter.id}'),
                          label: Text(chapter.name),
                          selected: _chapterIds.contains(chapter.id),
                          onSelected: (selected) => setState(() {
                            if (selected) {
                              _chapterIds.add(chapter.id);
                            } else {
                              _chapterIds.remove(chapter.id);
                            }
                          }),
                        ),
                    ],
                  ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<int>(
                        key: const ValueKey('assignment-count'),
                        initialValue: _count,
                        decoration: const InputDecoration(
                          labelText: '题量',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(value: 5, child: Text('5 题')),
                          DropdownMenuItem(value: 10, child: Text('10 题')),
                          DropdownMenuItem(value: 15, child: Text('15 题')),
                          DropdownMenuItem(value: 20, child: Text('20 题')),
                        ],
                        onChanged: (value) => setState(() => _count = value ?? 10),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: DropdownButtonFormField<int>(
                        key: const ValueKey('assignment-time-limit'),
                        initialValue: _timeLimitMin,
                        decoration: const InputDecoration(
                          labelText: '限时',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(value: 20, child: Text('20 分钟')),
                          DropdownMenuItem(value: 30, child: Text('30 分钟')),
                          DropdownMenuItem(value: 45, child: Text('45 分钟')),
                          DropdownMenuItem(value: 60, child: Text('60 分钟')),
                        ],
                        onChanged: (value) => setState(() => _timeLimitMin = value ?? 30),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<int>(
                  key: const ValueKey('assignment-due-days'),
                  initialValue: _dueDays,
                  decoration: const InputDecoration(
                    labelText: '截止时间',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: 1, child: Text('1 天后截止')),
                    DropdownMenuItem(value: 3, child: Text('3 天后截止')),
                    DropdownMenuItem(value: 7, child: Text('7 天后截止')),
                  ],
                  onChanged: (value) => setState(() => _dueDays = value ?? 7),
                ),
                const SizedBox(height: 12),
                Text('题型（单节 5 分）', style: theme.textTheme.titleSmall),
                const SizedBox(height: 4),
                Wrap(
                  spacing: 8,
                  children: [
                    for (final entry in _qTypeOptions.entries)
                      FilterChip(
                        key: ValueKey('qtype-${entry.key}'),
                        label: Text(entry.value),
                        selected: _qTypes.contains(entry.key),
                        onSelected: (selected) => setState(() {
                          if (selected) {
                            _qTypes.add(entry.key);
                          } else {
                            _qTypes.remove(entry.key);
                          }
                        }),
                      ),
                  ],
                ),
                const SizedBox(height: 24),
                FilledButton.icon(
                  key: const ValueKey('submit-assignment'),
                  onPressed: _submitting ? null : _submit,
                  icon: _submitting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.send),
                  label: Text(_submitting ? '布置中…' : '布置作业'),
                ),
              ],
            ),
    );
  }
}
