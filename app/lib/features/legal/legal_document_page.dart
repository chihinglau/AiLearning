import 'package:ai_learning/core/constants/legal_constants.dart';
import 'package:ai_learning/core/models/legal.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/legal_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 隐私政策 / 用户协议页（R-03）。
///
/// [localOnly] 为 true 时只读取 App 内置版本（首启同意阶段不发网络请求）。
class LegalDocumentPage extends ConsumerStatefulWidget {
  const LegalDocumentPage({
    super.key,
    required this.docType,
    this.localOnly = false,
  });

  final String docType;
  final bool localOnly;

  @override
  ConsumerState<LegalDocumentPage> createState() => _LegalDocumentPageState();
}

class _LegalDocumentPageState extends ConsumerState<LegalDocumentPage> {
  LegalDocument? _doc;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final service = ref.read(legalServiceProvider);
    try {
      final doc = widget.localOnly
          ? await LegalService.loadBundled(widget.docType)
          : await service.fetch(widget.docType);
      if (mounted) setState(() => _doc = doc);
    } catch (_) {
      if (mounted) setState(() => _error = '文档加载失败，请稍后重试');
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = widget.docType == 'privacy'
        ? kLegalPrivacyTitle
        : kLegalTermsTitle;
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: _error != null
          ? Center(child: Text(_error!))
          : _doc == null
              ? const Center(child: CircularProgressIndicator())
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 40),
                  children: [
                    LegalMarkdown(content: _doc!.content),
                    const SizedBox(height: 24),
                    Text(
                      '版本 ${_doc!.version}'
                      '${_doc!.updatedAt.isEmpty ? '' : ' · 更新于 ${_doc!.updatedAt}'}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
    );
  }
}

/// 轻量 Markdown 渲染：覆盖标题、列表、表格、引用与分隔线。
class LegalMarkdown extends StatelessWidget {
  const LegalMarkdown({super.key, required this.content});

  final String content;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final widgets = <Widget>[];
    final bullets = <String>[];
    final table = <String>[];
    final paragraph = <String>[];

    void flushBullets() {
      if (bullets.isEmpty) return;
      widgets.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (final item in bullets)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('• '),
                      Expanded(child: Text(item, style: theme.textTheme.bodyMedium)),
                    ],
                  ),
                ),
            ],
          ),
        ),
      );
      bullets.clear();
    }

    void flushTable() {
      if (table.isEmpty) return;
      widgets.add(
        Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            border: Border.all(color: theme.colorScheme.outlineVariant),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            table.join('\n'),
            style: const TextStyle(fontFamily: 'monospace', fontSize: 12, height: 1.6),
          ),
        ),
      );
      table.clear();
    }

    void flushParagraph() {
      if (paragraph.isEmpty) return;
      widgets.add(
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Text(paragraph.join(' '), style: theme.textTheme.bodyMedium),
        ),
      );
      paragraph.clear();
    }

    void flushAll() {
      flushParagraph();
      flushBullets();
      flushTable();
    }

    for (final raw in content.split('\n')) {
      final line = raw.trim();
      if (line.startsWith('|')) {
        flushParagraph();
        flushBullets();
        table.add(line);
        continue;
      }
      flushTable();
      if (line.isEmpty) {
        flushAll();
        continue;
      }
      final heading = RegExp(r'^(#{1,3})\s+(.*)$').firstMatch(line);
      if (heading != null) {
        flushAll();
        final level = heading.group(1)!.length;
        final text = _plain(heading.group(2)!);
        widgets.add(
          Padding(
            padding: EdgeInsets.only(top: level == 1 ? 0 : 16, bottom: 8),
            child: Text(
              text,
              style: level == 1
                  ? theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)
                  : level == 2
                      ? theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)
                      : theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
          ),
        );
        continue;
      }
      if (RegExp(r'^---+$').hasMatch(line)) {
        flushAll();
        widgets.add(const Divider(height: 24));
        continue;
      }
      if (line.startsWith('- ') || line.startsWith('* ')) {
        flushParagraph();
        bullets.add(_plain(line.substring(2)));
        continue;
      }
      if (line.startsWith('>')) {
        flushAll();
        widgets.add(
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Text(
              _plain(line.replaceFirst(RegExp(r'^>\s*'), '')),
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.outline,
              ),
            ),
          ),
        );
        continue;
      }
      flushBullets();
      paragraph.add(_plain(line));
    }
    flushAll();

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: widgets);
  }

  /// 去掉 Markdown 行内标记（加粗/代码/链接），保留可读文本。
  static String _plain(String text) {
    return text
        .replaceAll(RegExp(r'\*\*([^*]+)\*\*'), r'$1')
        .replaceAll(RegExp(r'`([^`]+)`'), r'$1')
        .replaceAllMapped(
          RegExp(r'\[([^\]]+)\]\([^)]*\)'),
          (match) => match.group(1) ?? '',
        );
  }
}
