import 'dart:async';

import 'package:ai_learning/app.dart';
import 'package:ai_learning/core/monitoring/crash_reporter.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/pal/platform_pal_factory.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final pal = createPlatformPal();
  await pal.storage.init();

  // R-09：全局崩溃捕获 + 启动时重放上次未上报的记录（失败不影响启动）。
  final crashReporter = CrashReporter(storage: pal.storage);
  crashReporter.install();
  unawaited(crashReporter.flush());

  runApp(
    ProviderScope(
      overrides: [platformPalProvider.overrideWithValue(pal)],
      child: const AiLearningApp(),
    ),
  );
}
