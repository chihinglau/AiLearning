import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 内容举报（R-07）：题目/教材/其他内容的问题反馈入口。
class ContentReportPage extends ConsumerStatefulWidget {
  const ContentReportPage({super.key});

  @override
  ConsumerState<ContentReportPage> createState() => _ContentReportPageState();
}

class _ContentReportPageState extends ConsumerState<ContentReportPage> {
  final _idController = TextEditingController();
  final _descriptionController = TextEditingController();
  String _targetType = 'question';
  String _reason = 'answer_error';
  bool _submitting = false;

  static const _targetLabels = {
    'question': '题目',
    'textbook': '教材',
    'other': '其他',
  };
  static const _reasonLabels = {
    'answer_error': '答案/解析错误',
    'inappropriate': '内容不适宜',
    'infringement': '侵权或版权问题',
    'other': '其他问题',
  };

  @override
  void dispose() {
    _idController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_targetType == "question" && _idController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请填写要举报的题目 ID')),
      );
      return;
    }
    setState(() => _submitting = true);
    try {
      await ref.read(contentReportServiceProvider).submit(
            targetType: _targetType,
            targetId: _targetType == 'question'
                ? int.tryParse(_idController.text.trim())
                : null,
            reason: _reason,
            description: _descriptionController.text.trim(),
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('举报已提交，我们将在 24 小时内核实处理')),
      );
      Navigator.of(context).pop();
    } on ApiException catch (error) {
      if (mounted) await handleApiError(context, ref, error);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('内容举报')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            '如发现题目答案错误、内容不适或涉及版权问题，请在此反馈。'
            '我们将在 24 小时内核实并下架问题内容。',
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            initialValue: _targetType,
            decoration: const InputDecoration(labelText: '举报类型'),
            items: _targetLabels.entries
                .map(
                  (entry) => DropdownMenuItem(
                    value: entry.key,
                    child: Text(entry.value),
                  ),
                )
                .toList(),
            onChanged: (value) {
              if (value != null) setState(() => _targetType = value);
            },
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _idController,
            keyboardType: TextInputType.number,
            decoration: InputDecoration(
              labelText: '内容 ID（题目举报必填）',
              helperText: _targetType == 'question' ? '题目详情页可查看题目 ID' : '可留空',
            ),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _reason,
            decoration: const InputDecoration(labelText: '问题原因'),
            items: _reasonLabels.entries
                .map(
                  (entry) => DropdownMenuItem(
                    value: entry.key,
                    child: Text(entry.value),
                  ),
                )
                .toList(),
            onChanged: (value) {
              if (value != null) setState(() => _reason = value);
            },
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _descriptionController,
            maxLines: 4,
            maxLength: 500,
            decoration: const InputDecoration(
              labelText: '详细说明（可选）',
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: _submitting ? null : _submit,
            child: Text(_submitting ? '提交中…' : '提交举报'),
          ),
        ],
      ),
    );
  }
}
