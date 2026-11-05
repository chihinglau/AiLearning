import 'package:ai_learning/app.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/pal/platform_pal_factory.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final pal = createPlatformPal();
  await pal.storage.init();
  runApp(
    ProviderScope(
      overrides: [platformPalProvider.overrideWithValue(pal)],
      child: const AiLearningApp(),
    ),
  );
}
