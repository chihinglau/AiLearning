import 'package:ai_learning/core/theme/app_accents.dart';
import 'package:ai_learning/widgets/feature_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const accent = Color(0xFF4F46C8);

  Widget wrap(Widget child) {
    return MaterialApp(
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1E6FD9)),
        // 测试环境缺少 InkSparkle 着色器，禁用水波纹以稳定触发 onTap。
        splashFactory: NoSplash.splashFactory,
        extensions: const [AppAccents.light],
      ),
      home: Scaffold(body: child),
    );
  }

  testWidgets('展示图标、标题与副标题', (tester) async {
    await tester.pumpWidget(
      wrap(
        const FeatureCard(
          icon: Icons.pause_circle_outline,
          accent: accent,
          title: '继续练习',
          subtitle: '已完成 3/10 题',
        ),
      ),
    );

    expect(find.text('继续练习'), findsOneWidget);
    expect(find.text('已完成 3/10 题'), findsOneWidget);
    expect(find.byIcon(Icons.pause_circle_outline), findsOneWidget);
  });

  testWidgets('进度非空时展示进度条', (tester) async {
    await tester.pumpWidget(
      wrap(
        const FeatureCard(
          icon: Icons.play_arrow_rounded,
          accent: accent,
          title: '继续学习',
          progress: 0.4,
        ),
      ),
    );

    final bar = tester.widget<LinearProgressIndicator>(
      find.byType(LinearProgressIndicator),
    );
    expect(bar.value, 0.4);
  });

  testWidgets('点击触发 onTap', (tester) async {
    var tapped = 0;
    await tester.pumpWidget(
      wrap(
        FeatureCard(
          icon: Icons.assignment_outlined,
          accent: accent,
          title: '考试中心',
          onTap: () => tapped++,
        ),
      ),
    );

    await tester.tap(find.byType(FeatureCard));
    await tester.pumpAndSettle();
    expect(tapped, 1);
  });

  testWidgets('不可点击时标题仍可见且整体降低透明度', (tester) async {
    await tester.pumpWidget(
      wrap(
        const FeatureCard(
          icon: Icons.edit_document,
          accent: accent,
          title: '班级作业',
        ),
      ),
    );

    expect(find.text('班级作业'), findsOneWidget);
    final opacity = tester.widget<Opacity>(
      find.descendant(
        of: find.byType(FeatureCard),
        matching: find.byType(Opacity),
      ),
    );
    expect(opacity.opacity, 0.38);
  });
}
