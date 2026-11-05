import 'package:ai_learning/pal/account_pal.dart';
import 'package:ai_learning/pal/platform_pal.dart';
import 'package:ai_learning/pal/screen_time_pal.dart';
import 'package:ai_learning/pal/storage_pal.dart';
import 'package:hive_flutter/hive_flutter.dart';

/// HarmonyOS 端：当前使用 Hive 沙盒存储；鸿蒙安全存储插件就绪后替换为系统密钥库。
class OhosStoragePal implements StoragePal {
  Box<String>? _box;

  @override
  Future<void> init() async {
    await Hive.initFlutter();
    _box = await Hive.openBox<String>('app_storage');
  }

  Box<String> get _requireBox {
    final box = _box;
    if (box == null) {
      throw StateError('StoragePal 尚未初始化');
    }
    return box;
  }

  @override
  Future<String?> read(String key) async => _requireBox.get(key);

  @override
  Future<void> write(String key, String value) => _requireBox.put(key, value);

  @override
  Future<void> delete(String key) => _requireBox.delete(key);
}

/// HarmonyOS 端账号：华为账号 OAuth / 华为 IAP 一体化。
class OhosAccountPal implements AccountPal {
  @override
  String get providerName => '华为账号';

  @override
  Future<AccountProfile?> signIn() async => null;

  @override
  Future<void> signOut() async {}
}

PlatformPal createOhosPlatformPal() {
  return PlatformPal(
    platform: PalPlatform.ohos,
    storage: OhosStoragePal(),
    account: OhosAccountPal(),
    screenTime: const CurfewScreenTimePal(),
  );
}
