import 'package:ai_learning/core/models/user.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/auth_service.dart';
import 'package:ai_learning/core/services/content_service.dart';
import 'package:ai_learning/core/services/learn_service.dart';
import 'package:ai_learning/pal/platform_pal.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final platformPalProvider = Provider<PlatformPal>(
  (ref) => throw UnimplementedError('请在 main.dart 的 ProviderScope 中覆盖'),
);

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());

final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(
    ref.watch(apiClientProvider),
    ref.watch(platformPalProvider).storage,
  );
});

final contentServiceProvider = Provider<ContentService>((ref) {
  return ContentService(ref.watch(apiClientProvider));
});

final learnServiceProvider = Provider<LearnService>((ref) {
  return LearnService(ref.watch(apiClientProvider));
});

final currentUserProvider = StateProvider<AppUser?>((ref) => null);
