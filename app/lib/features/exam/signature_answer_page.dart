import 'dart:convert';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

/// 手写图片作答：在画板上书写，导出 PNG data URL，作为主观题答案。
class SignatureAnswerPage extends StatefulWidget {
  const SignatureAnswerPage({super.key, required this.questionStem});

  final String questionStem;

  @override
  State<SignatureAnswerPage> createState() => _SignatureAnswerPageState();
}

class _SignatureAnswerPageState extends State<SignatureAnswerPage> {
  final _boundaryKey = GlobalKey();
  final List<List<Offset>> _strokes = [];
  bool _exporting = false;

  void _start(Offset point) {
    setState(() => _strokes.add([point]));
  }

  void _extend(Offset point) {
    if (_strokes.isEmpty) return;
    setState(() => _strokes.last.add(point));
  }

  void _undo() {
    if (_strokes.isEmpty) return;
    setState(() => _strokes.removeLast());
  }

  void _clear() {
    if (_strokes.isEmpty) return;
    setState(() => _strokes.clear());
  }

  Future<void> _export() async {
    if (_strokes.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请先在画板上写答案')),
      );
      return;
    }
    setState(() => _exporting = true);
    try {
      final boundary =
          _boundaryKey.currentContext!.findRenderObject() as RenderRepaintBoundary;
      final image = await boundary.toImage(pixelRatio: 1.0);
      final data = await image.toByteData(format: ui.ImageByteFormat.png);
      if (data == null) throw StateError('图片导出失败');
      final bytes = data.buffer.asUint8List();
      final dataUrl = 'data:image/png;base64,${base64Encode(bytes)}';
      if (!mounted) return;
      Navigator.of(context).pop(dataUrl);
    } catch (_) {
      if (!mounted) return;
      setState(() => _exporting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('图片导出失败，请重试')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('手写图片作答'),
        actions: [
          TextButton(
            key: const ValueKey('signature-undo'),
            onPressed: _strokes.isEmpty ? null : _undo,
            child: const Text('撤销'),
          ),
          TextButton(
            key: const ValueKey('signature-clear'),
            onPressed: _strokes.isEmpty ? null : _clear,
            child: const Text('清空'),
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.questionStem,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodySmall,
                ),
                const SizedBox(height: 4),
                Text(
                  '用手指或手写笔书写，完成后点击「提交图片」。',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.outline,
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: theme.colorScheme.outlineVariant),
              ),
              clipBehavior: Clip.antiAlias,
              child: GestureDetector(
                key: const ValueKey('signature-canvas'),
                onPanStart: (details) => _start(details.localPosition),
                onPanUpdate: (details) => _extend(details.localPosition),
                child: RepaintBoundary(
                  key: _boundaryKey,
                  child: CustomPaint(
                    painter: _StrokePainter(strokes: _strokes),
                    size: Size.infinite,
                  ),
                ),
              ),
            ),
          ),
          SafeArea(
            minimum: const EdgeInsets.all(16),
            child: SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                key: const ValueKey('signature-submit'),
                onPressed: _exporting ? null : _export,
                icon: _exporting
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.image_outlined),
                label: Text(_exporting ? '生成图片…' : '提交图片'),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StrokePainter extends CustomPainter {
  const _StrokePainter({required this.strokes});

  final List<List<Offset>> strokes;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.black87
      ..strokeWidth = 2.6
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;
    for (final stroke in strokes) {
      if (stroke.length < 2) {
        if (stroke.isNotEmpty) {
          canvas.drawCircle(stroke.first, 1.5, paint..style = PaintingStyle.fill);
        }
        continue;
      }
      final path = Path()..moveTo(stroke.first.dx, stroke.first.dy);
      for (final point in stroke.skip(1)) {
        path.lineTo(point.dx, point.dy);
      }
      canvas.drawPath(path, paint..style = PaintingStyle.stroke);
    }
  }

  @override
  bool shouldRepaint(covariant _StrokePainter oldDelegate) => true;
}
