import 'dart:io';

import 'package:ai_learning/pal/implementations/android/android_platform_pal.dart';
import 'package:ai_learning/pal/implementations/ohos/ohos_platform_pal.dart';
import 'package:ai_learning/pal/platform_pal.dart';

/// 双端入口分流：Android 走 AndroidPal，HarmonyOS NEXT 走 OhosPal。
PlatformPal createPlatformPal() {
  if (Platform.isAndroid) {
    return createAndroidPlatformPal();
  }
  if (Platform.operatingSystem == 'ohos') {
    return createOhosPlatformPal();
  }
  throw UnsupportedError('暂不支持的平台：${Platform.operatingSystem}');
}
