import 'package:ai_learning/core/models/user.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/auth_service.dart';
import 'package:ai_learning/core/services/content_service.dart';
import 'package:ai_learning/core/services/exam_service.dart';
import 'package:ai_learning/core/services/family_service.dart';
import 'package:ai_learning/core/services/learn_service.dart';
import 'package:ai_learning/core/services/textbook_service.dart';
import 'package:ai_learning/core/services/user_service.dart';
import 'package:ai_learning/pal/platform_pal.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 年级/教材引导状态：unknown 表示尚未判定，required 强制进入引导页。
enum OnboardingStatus { unknown, required, completed }

final onboardingStatusProvider =
    StateProvider<OnboardingStatus>((ref) => OnboardingStatus.unknown);

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

final textbookServiceProvider = Provider<TextbookService>((ref) {
  return TextbookService(ref.watch(apiClientProvider));
});

final examServiceProvider = Provider<ExamService>((ref) {
  return ExamService(ref.watch(apiClientProvider));
});

final familyServiceProvider = Provider<FamilyService>((ref) {
  return FamilyService(ref.watch(apiClientProvider));
});

final userServiceProvider = Provider<UserService>((ref) {
  return UserService(ref.watch(apiClientProvider));
});

final currentUserProvider = StateProvider<AppUser?>((ref) => null);
