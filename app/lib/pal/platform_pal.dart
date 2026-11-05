import 'package:ai_learning/pal/account_pal.dart';
import 'package:ai_learning/pal/screen_time_pal.dart';
import 'package:ai_learning/pal/storage_pal.dart';

enum PalPlatform { android, ohos }

class PlatformPal {
  const PlatformPal({
    required this.platform,
    required this.storage,
    required this.account,
    required this.screenTime,
  });

  final PalPlatform platform;
  final StoragePal storage;
  final AccountPal account;
  final ScreenTimePal screenTime;
}
