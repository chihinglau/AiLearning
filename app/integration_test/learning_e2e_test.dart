import 'package:ai_learning/features/learn/mastery_ring.dart';
import 'package:ai_learning/main.dart' as app;
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

const _apiBase = String.fromEnvironment(
  'E2E_API_BASE',
  defaultValue: 'http://127.0.0.1:18080',
);

final Dio _dio = Dio(
  BaseOptions(
    baseUrl: _apiBase,
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 30),
    validateStatus: (status) => status != null && status < 500,
  ),
);

/// 真机 E2E：登录 → 年级引导 → 教材绑定 → 单元/知识点 → 练习 → 结算 →
/// 考试中心 → 限时答题 → 交卷 → 报告 → 错题本。
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  final password = 'pass1234';
  final phone =
      '139${(DateTime.now().millisecondsSinceEpoch % 100000000).toString().padLeft(8, '0')}';

  testWidgets('学生端学习-练习-考试闭环', (tester) async {
    // ---------------- 账号与环境准备 ----------------
    final registered = await _dio.post(
      '/api/auth/register',
      data: {'phone': phone, 'password': password, 'grade': 3},
    );
    expect(registered.statusCode, 201, reason: '${registered.data}');
    final studentToken = await _login(phone, password);

    // ---------------- 登录与引导 ----------------
    await app.main();
    await _waitFor(tester, find.text('登录'), timeout: const Duration(seconds: 30));

    final loginFields = find.byType(TextField);
    await tester.enterText(loginFields.at(0), phone);
    await tester.enterText(loginFields.at(1), password);
    await tester.tap(find.text('登录'));
    await _waitFor(
      tester,
      find.text('完善学习信息'),
      timeout: const Duration(seconds: 30),
    );

    await tester.tap(find.text('下一步'));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.tap(find.text('下一步'));
    await tester.pump(const Duration(milliseconds: 500));
    await _waitFor(tester, find.text('完成并开始学习'));
    await tester.tap(find.text('完成并开始学习'));
    await _waitFor(
      tester,
      find.text('今日计划'),
      timeout: const Duration(seconds: 40),
    );

    // ---------------- 单元 → 知识点 → 练一练 ----------------
    await _tapVisible(tester, find.text('数学'));
    await _waitFor(tester, find.text('单元掌握度'));
    await tester.pump(const Duration(milliseconds: 300));

    await tester.tap(find.byType(MasteryRing).first);
    await _waitFor(tester, find.text('单元综合练习'));
    await tester.pump(const Duration(milliseconds: 300));

    await _tapVisible(tester, find.text('练一练'));
    await _waitFor(tester, find.text('练习配置'));

    // 练习页当前仅支持选项类题型，取消「填空题」以保证每题都能作答
    final fillChip = find.widgetWithText(FilterChip, '填空题');
    if (fillChip.evaluate().isNotEmpty) {
      await _tapVisible(tester, fillChip);
    }
    final startText = find.text('开始练习');
    await tester.scrollUntilVisible(
      startText,
      300,
      scrollable: find.byType(Scrollable).first,
      maxScrolls: 30,
    );
    final startButton =
        find.ancestor(of: startText, matching: find.byType(FilledButton));
    for (var i = 0; i < 20; i++) {
      final widgets = startButton.evaluate();
      if (widgets.isNotEmpty &&
          (widgets.first.widget as FilledButton).onPressed != null) {
        break;
      }
      await tester.pump(const Duration(milliseconds: 300));
    }
    await _tapVisible(tester, startText);

    // ---------------- 练习答题与结算 ----------------
    var finished = false;
    for (var i = 0; i < 40 && !finished; i++) {
      await _answerCurrent(tester);
      await _tapVisible(tester, find.text('提交答案'));
      final outcome = await _waitForAny(
        tester,
        const ['下一题', '完成练习'],
        timeout: const Duration(seconds: 8),
      );
      expect(outcome, isNotNull, reason: '第 ${i + 1} 题未出现下一步按钮');
      if (outcome == '下一题') {
        await _tapVisible(tester, find.text('下一题'));
      } else {
        await _tapVisible(tester, find.text('完成练习'));
        finished = true;
      }
    }
    expect(finished, isTrue, reason: '练习未走到结算');
    await _waitFor(
      tester,
      find.text('返回主页'),
      timeout: const Duration(seconds: 20),
    );

    // 错题本入口连通性
    await _tapVisible(
      tester,
      find.widgetWithText(OutlinedButton, '去错题本'),
    );
    await _waitFor(tester, find.text('错题本'));
    await tester.pump(const Duration(seconds: 1));
    await tester.tap(find.byIcon(Icons.menu_book_outlined));
    await _waitFor(tester, find.text('今日计划'), timeout: const Duration(seconds: 20));

    // ---------------- 生成一场考试 ----------------
    final home = await _dio.get(
      '/api/learn/home',
      options: _auth(studentToken),
    );
    final textbooks = (home.data['textbooks'] as List).cast<Map<String, dynamic>>();
    final math = textbooks.firstWhere(
      (item) => item['subject'] == 'math',
      orElse: () => throw StateError('自动绑定后未找到数学教材'),
    );
    final units = await _dio.get(
      '/api/learn/textbook/${math['textbook_id']}/units',
      options: _auth(studentToken),
    );
    final adminToken = await _login('13800000000', 'admin123');
    final examTitle = 'E2E 单元测 $phone';
    Map<String, dynamic>? generated;
    for (final raw in (units.data as List).cast<Map<String, dynamic>>()) {
      if ((raw['question_count'] as int? ?? 0) <= 0) continue;
      final response = await _dio.post(
        '/api/exams/generate',
        data: {
          'blueprint_code': 'math_primary_unit',
          'chapter_ids': [raw['id']],
          'title': examTitle,
        },
        options: _auth(adminToken),
      );
      if (response.statusCode == 200) {
        generated = response.data as Map<String, dynamic>;
        break;
      }
    }
    expect(generated, isNotNull, reason: '未能生成 E2E 试卷');

    // ---------------- 考试中心 → 答题 → 报告 ----------------
    await _tapVisible(tester, find.text('考试中心'));
    await _waitFor(
      tester,
      find.text(examTitle),
      timeout: const Duration(seconds: 30),
    );
    await _tapVisible(tester, find.text(examTitle));
    await _waitFor(
      tester,
      find.textContaining('第 1 /'),
      timeout: const Duration(seconds: 30),
    );

    var submitted = false;
    for (var i = 0; i < 50 && !submitted; i++) {
      await tester.pump(const Duration(milliseconds: 300));
      await _answerCurrent(tester);
      if (find.text('下一题').evaluate().isNotEmpty) {
        await tester.tap(find.text('下一题').first);
        await tester.pump(const Duration(milliseconds: 300));
        continue;
      }
      await tester.tap(find.text('交卷').first);
      submitted = true;
    }
    expect(submitted, isTrue, reason: '未找到交卷按钮');

    await _waitFor(tester, find.text('确认交卷'), timeout: const Duration(seconds: 10));
    await tester.tap(find.text('确认交卷'));
    await _waitFor(
      tester,
      find.text('考试报告'),
      timeout: const Duration(seconds: 30),
    );
    await _waitFor(tester, find.textContaining('得分率'));

    await _tapVisible(
      tester,
      find.widgetWithText(OutlinedButton, '返回考试中心'),
    );
    await _waitFor(tester, find.text('查看报告'), timeout: const Duration(seconds: 20));
    await _waitFor(
      tester,
      find.textContaining('得分 '),
      timeout: const Duration(seconds: 20),
    );
    await tester.tap(find.byIcon(Icons.home_outlined));
    await _waitFor(tester, find.text('今日计划'), timeout: const Duration(seconds: 20));
  });
}

Future<String> _login(String phone, String password) async {
  final response = await _dio.post(
    '/api/auth/login',
    data: FormData.fromMap({'username': phone, 'password': password}),
  );
  expect(response.statusCode, 200, reason: '登录失败: ${response.data}');
  return (response.data as Map<String, dynamic>)['access_token'] as String;
}

Options _auth(String token) => Options(
      headers: {'Authorization': 'Bearer $token'},
    );

Future<void> _waitFor(
  WidgetTester tester,
  Finder finder, {
  Duration timeout = const Duration(seconds: 15),
}) async {
  final deadline = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(deadline)) {
    await tester.pump(const Duration(milliseconds: 100));
    if (finder.evaluate().isNotEmpty) return;
  }
  fail('等待超时: $finder');
}

Future<String?> _waitForAny(
  WidgetTester tester,
  List<String> labels, {
  Duration timeout = const Duration(seconds: 10),
}) async {
  final deadline = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(deadline)) {
    await tester.pump(const Duration(milliseconds: 100));
    for (final label in labels) {
      if (find.text(label).evaluate().isNotEmpty) return label;
    }
  }
  return null;
}

Future<void> _tapVisible(WidgetTester tester, Finder finder) async {
  if (finder.evaluate().isEmpty) {
    await tester.scrollUntilVisible(
      finder,
      300,
      scrollable: find.byType(Scrollable).first,
      maxScrolls: 40,
    );
    await tester.pump(const Duration(milliseconds: 300));
  }
  final target = finder.first;
  await tester.ensureVisible(target);
  await tester.pump(const Duration(milliseconds: 300));
  final rect = tester.getRect(target);
  final viewHeight =
      tester.view.physicalSize.height / tester.view.devicePixelRatio;
  final safeBottom = viewHeight - 120;
  if (rect.bottom > safeBottom) {
    await tester.drag(
      find.byType(Scrollable).first,
      Offset(0, -(rect.bottom - safeBottom + 60)),
    );
    await tester.pump(const Duration(milliseconds: 300));
  }
  await tester.tap(target);
  await tester.pump(const Duration(milliseconds: 300));
}

/// 练习/考试通用作答：填空输入文本，多选勾选，单选/判断点选项。
Future<void> _answerCurrent(WidgetTester tester) async {
  final textFields = find.byType(TextField);
  if (textFields.evaluate().isNotEmpty) {
    await tester.enterText(textFields.first, '0');
    await tester.pump(const Duration(milliseconds: 200));
    return;
  }
  final checkboxes = find.byType(CheckboxListTile);
  if (checkboxes.evaluate().isNotEmpty) {
    await _tapVisible(tester, checkboxes);
    return;
  }
  final tiles = find.byType(ListTile);
  if (tiles.evaluate().isNotEmpty) {
    await _tapVisible(tester, tiles);
  }
}
