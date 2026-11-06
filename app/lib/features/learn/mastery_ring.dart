import 'package:flutter/material.dart';

/// 掌握度环形指示（知识点/单元通用）。
class MasteryRing extends StatelessWidget {
  const MasteryRing({
    super.key,
    required this.score,
    required this.color,
    this.size = 48,
    this.strokeWidth = 5,
  });

  final double score;
  final Color color;
  final double size;
  final double strokeWidth;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            width: size - 4,
            height: size - 4,
            child: CircularProgressIndicator(
              value: (score / 100).clamp(0, 1),
              strokeWidth: strokeWidth,
              backgroundColor: theme.colorScheme.surfaceContainerHighest,
              color: color,
            ),
          ),
          Text(
            score.round().toString(),
            style: theme.textTheme.labelSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}
