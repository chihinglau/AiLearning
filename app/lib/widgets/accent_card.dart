import 'package:flutter/material.dart';

/// 淡彩卡片：用强调色做底色分区，让页面重点信息更突出。
///
/// 只接受来自 [AppAccents] 的 accent 色，禁止调用方直接传硬编码色值。
class AccentCard extends StatelessWidget {
  const AccentCard({
    super.key,
    required this.accent,
    this.child,
    this.padding = const EdgeInsets.all(14),
    this.onTap,
    this.margin = EdgeInsets.zero,
  });

  final Color accent;
  final Widget? child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final EdgeInsetsGeometry margin;

  @override
  Widget build(BuildContext context) {
    final radius = BorderRadius.circular(16);
    final content = Ink(
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          accent.withValues(alpha: 0.09),
          Theme.of(context).colorScheme.surface,
        ),
        borderRadius: radius,
        border: Border.all(color: accent.withValues(alpha: 0.26)),
      ),
      child: Padding(padding: padding, child: child),
    );
    return Padding(
      padding: margin,
      child: Material(
        color: Colors.transparent,
        child: onTap == null
            ? content
            : InkWell(borderRadius: radius, onTap: onTap, child: content),
      ),
    );
  }
}
