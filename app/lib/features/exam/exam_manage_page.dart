import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 考试入库（D-04 §8.7.3）：按蓝图组卷，并把新卷派发为班级同卷模考。
///
/// CR-005 / D-09 §5.7：普通卷生成即发布（L20 行为不变）；真题生成即草稿，
/// 需在此提交复核，由 `/exams/reviews` 审核通过后才对学生可见。
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
  // D-09 §5.7 / EX-06：真题溯源表单（仅 is_past_paper=true 时使用）
  final _year = TextEditingController();
  final _region = TextEditingController();
  final _sourceName = TextEditingController();
  final _licenseNote = TextEditingController();
  final _adaptedFrom = TextEditingController();

  List<ExamBlueprint> _blueprints = [];
  String? _blueprintCode;
  bool _isPastPaper = false;
  bool _loading = true;
  bool _busy = false;
  bool _reviewSubmitted = false;
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
    _year.dispose();
    _region.dispose();
    _sourceName.dispose();
    _licenseNote.dispose();
    _adaptedFrom.dispose();
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
    final sourceName = _sourceName.text.trim();
    if (_isPastPaper && sourceName.isEmpty) {
      _snack('历年真题必须填写来源名称');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final title = _title.text.trim();
      String? optional(String value) =>
          value.trim().isEmpty ? null : value.trim();
      final result = await ref.read(examServiceProvider).generateExam(
            blueprintCode: code,
            chapterIds: chapters,
            title: title.isEmpty ? null : title,
            seed: int.tryParse(_seed.text.trim()),
            isPastPaper: _isPastPaper,
            year: _isPastPaper ? int.tryParse(_year.text.trim()) : null,
            region: _isPastPaper ? optional(_region.text) : null,
            sourceName: _isPastPaper ? sourceName : null,
            licenseNote: _isPastPaper ? optional(_licenseNote.text) : null,
            adaptedFrom: _isPastPaper ? optional(_adaptedFrom.text) : null,
          );
      if (!mounted) return;
      setState(() {
        _result = result;
        _reviewSubmitted = false;
        _mockExamId.text = '${result.examId}';
        _busy = false;
      });
      _snack(
        result.isDraft
            ? '真题草稿已生成，ID ${result.examId}（待复核后发布）'
            : '试卷已发布，ID ${result.examId}',
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _busy = false;
      });
      _snack('生成失败：$e');
    }
  }

  Future<void> _openSpecTable() async {
    final result = _result;
    if (result == null) return;
    setState(() => _busy = true);
    try {
      final rows = await ref.read(examServiceProvider).specTable(result.examId);
      if (!mounted) return;
      setState(() => _busy = false);
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('双向细目表'),
          content: SizedBox(
            width: double.maxFinite,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${result.title} · 共 ${result.questionCount} 题 '
                    '${result.totalScore.toStringAsFixed(0)} 分',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 12),
                  if (rows.isEmpty)
                    const Text('暂无细目表数据')
                  else
                    for (final row in rows)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(
                                  row.matches
                                      ? Icons.check_circle_outline
                                      : Icons.error_outline,
                                  size: 16,
                                  color: row.matches
                                      ? Colors.green
                                      : Colors.orange,
                                ),
                                const SizedBox(width: 6),
                                Expanded(
                                  child: Text(
                                    '${row.sectionName}（${row.qType} · ${row.band}）',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            Text(
                              '计划 ${row.plannedCount} 题 / '
                              '${row.plannedScore.toStringAsFixed(0)} 分 → '
                              '实际 ${row.actualCount} 题 / '
                              '${row.actualScore.toStringAsFixed(0)} 分'
                              ' · 覆盖 ${row.chapterCount} 章节',
                            ),
                          ],
                        ),
                      ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('关闭'),
            ),
          ],
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      _snack('细目表读取失败：$e');
    }
  }

  Future<void> _openAnswerSheet() async {
    final result = _result;
    if (result == null) return;
    setState(() => _busy = true);
    try {
      final html = await ref.read(examServiceProvider).answerSheetHtml(result.examId);
      if (!mounted) return;
      setState(() => _busy = false);
      final questionCount = RegExp(r'data-question').allMatches(html).length;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('答题卡（A4 打印版）'),
          content: SizedBox(
            width: double.maxFinite,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '已生成 A4 打印版答题卡：${html.length} 字符'
                    '${questionCount > 0 ? ' · $questionCount 处作答区' : ''}。'
                    '不含题干与答案，可直接打印。',
                  ),
                  const SizedBox(height: 12),
                  SelectableText(
                    html,
                    maxLines: 6,
                    style: const TextStyle(fontSize: 11),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () async {
                await Clipboard.setData(ClipboardData(text: html));
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('答题卡 HTML 已复制到剪贴板')),
                );
              },
              child: const Text('复制 HTML'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('关闭'),
            ),
          ],
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      _snack('答题卡读取失败：$e');
    }
  }

  Future<void> _submitReview() async {
    final result = _result;
    if (result == null || !result.isDraft) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(examServiceProvider).submitForReview(result.examId);
      if (!mounted) return;
      setState(() {
        _reviewSubmitted = true;
        _busy = false;
      });
      _snack('已提交复核，等待内容审核');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _busy = false;
      });
      _snack('提交复核失败：$e');
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
                      '选择蓝图与章节范围生成试卷；普通卷生成即发布，'
                      '真题生成草稿，经复核后才在真题库可见。',
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  key: ValueKey(_blueprintCode),
                  initialValue: _blueprintCode,
                  isExpanded: true,
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
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],
                  selectedItemBuilder: (context) => [
                    for (final blueprint in _blueprints)
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          '${blueprint.name}（${blueprint.subject} · '
                          '${blueprint.totalScore}分）',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
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
                  subtitle: const Text('真题生成草稿，复核发布后仅真题库可见'),
                  onChanged: (value) => setState(() => _isPastPaper = value),
                ),
                if (_isPastPaper) ...[
                  const SizedBox(height: 4),
                  const Text(
                    '真题溯源（来源名称必填；按 D-08 合规红线与 R-07 台账登记）',
                    style: TextStyle(fontSize: 12),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _sourceName,
                    decoration: const InputDecoration(
                      labelText: '来源名称（必填）',
                      hintText: '例如 深圳市教育考试院公开真题',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _year,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: '年份',
                      hintText: '例如 2020',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _region,
                    decoration: const InputDecoration(
                      labelText: '地区',
                      hintText: '例如 深圳 / 广东 / 全国',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _licenseNote,
                    decoration: const InputDecoration(
                      labelText: '授权说明（可选）',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _adaptedFrom,
                    decoration: const InputDecoration(
                      labelText: '改编来源（可选）',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ],
                const SizedBox(height: 8),
                FilledButton.icon(
                  onPressed: _busy ? null : _generate,
                  icon: const Icon(Icons.publish_outlined),
                  label: const Text('生成试卷'),
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
                        '${_result!.insufficient ? ' · 题量不足' : ''} · '
                        '状态 ${_reviewSubmitted ? '待复核' : (_result!.isDraft ? '草稿' : '已发布')}',
                      ),
                    ),
                  ),
                  if (_result!.isDraft && !_reviewSubmitted) ...[
                    const SizedBox(height: 8),
                    OutlinedButton.icon(
                      onPressed: _busy ? null : _submitReview,
                      icon: const Icon(Icons.fact_check_outlined),
                      label: const Text('提交复核'),
                    ),
                  ],
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      OutlinedButton.icon(
                        onPressed: _busy ? null : _openSpecTable,
                        icon: const Icon(Icons.table_chart_outlined),
                        label: const Text('双向细目表'),
                      ),
                      OutlinedButton.icon(
                        onPressed: _busy ? null : _openAnswerSheet,
                        icon: const Icon(Icons.description_outlined),
                        label: const Text('答题卡'),
                      ),
                    ],
                  ),
                  if (_reviewSubmitted) ...[
                    const SizedBox(height: 8),
                    const Text('已提交复核，可在「试卷复核」队列查看'),
                  ],
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
