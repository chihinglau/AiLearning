import 'package:flutter/material.dart';

/// 品牌柔和彩功能卡片（UX-01）。
///
/// 淡彩底（accent 12% 叠表面色）+ 同色图标/标题，无渐变、无阴影；
/// 颜色只作辅助识别，标题/图标/副标题同时存在，满足色弱可用性。
class FeatureCard extends StatelessWidget {
  const FeatureCard({
    super.key,
    required this.icon,
    required this.title,
    required this.accent,
    this.subtitle,
    this.trailing,
    this.onTap,
    this.progress,
  });

  final IconData icon;
  final String title;
  final String? subtitle;
  final Color accent;
  final Widget? trailing;
  final VoidCallback? onTap;

  /// 0.0~1.0；非空时在副标题下展示细进度条。
  final double? progress;

  static const double radius = 14;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final background =
        Color.alphaBlend(accent.withValues(alpha: 0.12), theme.colorScheme.surface);
    final border = accent.withValues(alpha: 0.18);
    final label = subtitle == null ? title : '$title，$subtitle';

    return Semantics(
      button: onTap != null,
      label: label,
      child: Opacity(
        opacity: onTap == null ? 0.38 : 1,
        child: Material(
          color: background,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radius),
            side: BorderSide(color: border),
          ),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onTap,
            splashColor: accent.withValues(alpha: 0.08),
            highlightColor: accent.withValues(alpha: 0.04),
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 64),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: accent.withValues(alpha: 0.14),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(icon, color: accent, size: 20),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              color: accent,
                            ),
                          ),
                          if (subtitle != null) ...[
                            const SizedBox(height: 2),
                            Text(
                              subtitle!,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurfaceVariant,
                                fontSize: 12.5,
                              ),
                            ),
                          ],
                          if (progress != null) ...[
                            const SizedBox(height: 8),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: progress!.clamp(0.0, 1.0),
                                minHeight: 4,
                                color: accent,
                                backgroundColor: accent.withValues(alpha: 0.16),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    trailing ??
                        (onTap == null
                            ? const SizedBox.shrink()
                            : Icon(
                                Icons.chevron_right,
                                color: accent.withValues(alpha: 0.72),
                                size: 20,
                              )),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
