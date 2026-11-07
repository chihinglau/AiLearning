import 'package:ai_learning/core/constants/legal_constants.dart';
import 'package:ai_learning/features/legal/consent_gate.dart';
import 'package:ai_learning/features/legal/legal_document_page.dart';
import 'package:ai_learning/pal/storage_pal.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class _MemoryStorage implements StoragePal {
  final Map<String, String> _data = {};

  @override
  Future<void> init() async {}

  @override
  Future<String?> read(String key) async => _data[key];

  @override
  Future<void> write(String key, String value) async {
    _data[key] = value;
  }

  @override
  Future<void> delete(String key) async {
    _data.remove(key);
  }
}

class _FakeApp extends StatelessWidget {
  const _FakeApp();

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(home: Scaffold(body: Text('HOME')));
  }
}

void main() {
  testWidgets('未同意时展示同意门且无法进入应用', (tester) async {
    final storage = _MemoryStorage();
    await tester.pumpWidget(
      ConsentGate(storage: storage, child: const _FakeApp()),
    );
    await tester.pumpAndSettle();

    expect(find.text('欢迎使用深爱学'), findsOneWidget);
    expect(find.text('HOME'), findsNothing);

    final button = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, '同意并进入'),
    );
    expect(button.onPressed, isNull);
  });

  testWidgets('勾选并同意后进入应用，版本写入本地', (tester) async {
    final storage = _MemoryStorage();
    await tester.pumpWidget(
      ConsentGate(storage: storage, child: const _FakeApp()),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byType(Checkbox));
    await tester.pump();
    await tester.tap(find.widgetWithText(FilledButton, '同意并进入'));
    await tester.pumpAndSettle();

    expect(find.text('HOME'), findsOneWidget);
    expect(await storage.read(kLegalConsentStorageKey), kLegalPrivacyVersion);
  });

  testWidgets('已同意当前版本时直接进入应用', (tester) async {
    final storage = _MemoryStorage();
    await storage.write(kLegalConsentStorageKey, kLegalPrivacyVersion);
    await tester.pumpWidget(
      ConsentGate(storage: storage, child: const _FakeApp()),
    );
    await tester.pumpAndSettle();

    expect(find.text('HOME'), findsOneWidget);
    expect(find.text('欢迎使用深爱学'), findsNothing);
  });

  testWidgets('LegalMarkdown 渲染标题、列表与表格', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: LegalMarkdown(
            content: '# 标题\n\n- 第一项\n- 第二项\n\n| 列A | 列B |\n|---|---|\n| 1 | 2 |',
          ),
        ),
      ),
    );

    expect(find.text('标题'), findsOneWidget);
    expect(find.text('第一项'), findsOneWidget);
    expect(find.text('第二项'), findsOneWidget);
    expect(find.textContaining('列A'), findsOneWidget);
  });
}
