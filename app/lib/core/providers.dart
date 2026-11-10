import 'dart:async';

import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:ai_learning/core/models/user.dart';
import 'package:ai_learning/core/offline/offline_exam_store.dart';
import 'package:ai_learning/core/offline/offline_exam_sync.dart';
import 'package:ai_learning/core/offline/offline_learn_store.dart';
import 'package:ai_learning/core/offline/offline_learn_sync.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/app_info_service.dart';
import 'package:ai_learning/core/services/ai_service.dart';
import 'package:ai_learning/core/services/assignment_service.dart';
import 'package:ai_learning/core/services/auth_service.dart';
import 'package:ai_learning/core/services/compliance_service.dart';
import 'package:ai_learning/core/services/content_service.dart';
import 'package:ai_learning/core/services/content_report_service.dart';
import 'package:ai_learning/core/services/content_review_service.dart';
import 'package:ai_learning/core/services/exam_service.dart';
import 'package:ai_learning/core/services/family_service.dart';
import 'package:ai_learning/core/services/learn_service.dart';
import 'package:ai_learning/core/services/legal_service.dart';
import 'package:ai_learning/core/services/offline_learn_service.dart';
import 'package:ai_learning/core/services/org_service.dart';
import 'package:ai_learning/core/services/rbac_service.dart';
import 'package:ai_learning/core/services/server_config.dart';
import 'package:ai_learning/core/services/textbook_service.dart';
import 'package:ai_learning/core/services/user_service.dart';
import 'package:ai_learning/core/speech/question_audio.dart';
import 'package:ai_learning/core/speech/question_reader.dart';
import 'package:ai_learning/core/speech/speech_settings.dart';
import 'package:ai_learning/core/speech/tts_service.dart';
import 'package:ai_learning/pal/platform_pal.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 年级/教材引导状态：unknown 表示尚未判定，required 强制进入引导页。
enum OnboardingStatus { unknown, required, completed }

final onboardingStatusProvider =
    StateProvider<OnboardingStatus>((ref) => OnboardingStatus.unknown);

final platformPalProvider = Provider<PlatformPal>(
  (ref) => throw UnimplementedError('请在 main.dart 的 ProviderScope 中覆盖'),
);

final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(baseUrl: ref.watch(initialBaseUrlProvider)),
);

/// 服务地址（UX-03）：默认取编译期配置，启动时用本地保存值覆盖。
final initialBaseUrlProvider = Provider<String>((ref) => AppConfig.apiBaseUrl);

final serverConfigStoreProvider = Provider<ServerConfigStore>((ref) {
  return ServerConfigStore(ref.watch(platformPalProvider).storage);
});

final authServiceProvider = Provider<AuthService>((ref) {
  final api = ref.watch(apiClientProvider);
  final auth = AuthService(api, ref.watch(platformPalProvider).storage);
  // refresh 明确失效时清理本地登录态，路由随 currentUser 变化回到登录页。
  api.onSessionExpired = () async {
    await auth.clearSession();
    ref.read(currentUserProvider.notifier).state = null;
    ref.read(onboardingStatusProvider.notifier).state = OnboardingStatus.unknown;
  };
  return auth;
});

final contentServiceProvider = Provider<ContentService>((ref) {
  return ContentService(ref.watch(apiClientProvider));
});

final offlineLearnStoreProvider = Provider<OfflineLearnStore>((ref) {
  return HiveOfflineLearnStore();
});

final offlineLearnServiceProvider = Provider<OfflineLearnService>((ref) {
  return OfflineLearnService(
    ref.watch(apiClientProvider),
    ref.watch(offlineLearnStoreProvider),
  );
});

final offlineLearnSyncProvider = Provider<OfflineLearnSync>((ref) {
  return OfflineLearnSync(
    ref.watch(apiClientProvider),
    ref.watch(offlineLearnStoreProvider),
  );
});

final learnServiceProvider = Provider<LearnService>((ref) {
  return LearnService(
    ref.watch(apiClientProvider),
    offline: ref.watch(offlineLearnServiceProvider),
  );
});

final textbookServiceProvider = Provider<TextbookService>((ref) {
  return TextbookService(ref.watch(apiClientProvider));
});

final examServiceProvider = Provider<ExamService>((ref) {
  return ExamService(ref.watch(apiClientProvider));
});

final offlineExamStoreProvider = Provider<OfflineExamStore>((ref) {
  return HiveOfflineExamStore();
});

final offlineExamSyncProvider = Provider<OfflineExamSync>((ref) {
  return OfflineExamSync(
    ref.watch(examServiceProvider),
    ref.watch(offlineExamStoreProvider),
  );
});

final assignmentServiceProvider = Provider<AssignmentService>((ref) {
  return AssignmentService(ref.watch(apiClientProvider));
});

final aiServiceProvider = Provider<AIService>((ref) {
  return AIService(ref.watch(apiClientProvider));
});

final contentReviewServiceProvider = Provider<ContentReviewService>((ref) {
  return ContentReviewService(ref.watch(apiClientProvider));
});

final contentReportServiceProvider = Provider<ContentReportService>((ref) {
  return ContentReportService(ref.watch(apiClientProvider));
});

final familyServiceProvider = Provider<FamilyService>((ref) {
  return FamilyService(ref.watch(apiClientProvider));
});

final orgServiceProvider = Provider<OrgService>((ref) {
  return OrgService(ref.watch(apiClientProvider));
});

final rbacServiceProvider = Provider<RbacService>((ref) {
  return RbacService(ref.watch(apiClientProvider));
});

final userServiceProvider = Provider<UserService>((ref) {
  return UserService(ref.watch(apiClientProvider));
});

final legalServiceProvider = Provider<LegalService>((ref) {
  return LegalService(ref.watch(apiClientProvider));
});

final complianceServiceProvider = Provider<ComplianceService>((ref) {
  return ComplianceService(ref.watch(apiClientProvider));
});

final appInfoServiceProvider = Provider<AppInfoService>((ref) {
  return AppInfoService(ref.watch(apiClientProvider));
});

final currentUserProvider = StateProvider<AppUser?>((ref) => null);

/// 读题（TT-01）：系统 TTS 与本地语速设置。
final ttsServiceProvider = Provider<TtsService>((ref) {
  final service = TtsService();
  ref.onDispose(service.dispose);
  return service;
});

/// TT-04：优先播放服务端预生成音频，未就绪时由调用方回退系统 TTS。
final questionAudioServiceProvider = Provider<QuestionAudioService>((ref) {
  final service = QuestionAudioService(api: ref.watch(apiClientProvider));
  ref.onDispose(() => unawaited(service.dispose()));
  return service;
});

final speechSettingsStoreProvider = Provider<SpeechSettingsStore>((ref) {
  return SpeechSettingsStore(ref.watch(platformPalProvider).storage);
});

/// TT-05：统一读题入口（预生成音频优先，系统 TTS 兜底）。
final questionReaderProvider = Provider<QuestionReader>((ref) {
  return QuestionReader(
    tts: ref.watch(ttsServiceProvider),
    audio: ref.watch(questionAudioServiceProvider),
  );
});
