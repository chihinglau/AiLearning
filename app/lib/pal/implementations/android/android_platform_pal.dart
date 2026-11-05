import 'package:ai_learning/pal/account_pal.dart';
import 'package:ai_learning/pal/platform_pal.dart';
import 'package:ai_learning/pal/screen_time_pal.dart';
import 'package:ai_learning/pal/storage_pal.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Android 端：凭据写入系统 Keystore（flutter_secure_storage）。
class AndroidStoragePal implements StoragePal {
  AndroidStoragePal({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  @override
  Future<void> init() async {}

  @override
  Future<String?> read(String key) => _storage.read(key: key);

  @override
  Future<void> write(String key, String value) =>
      _storage.write(key: key, value: value);

  @override
  Future<void> delete(String key) => _storage.delete(key: key);
}

/// Android 端账号：手机号+短信 / 微信 SDK，SDK 接入前返回 null 由页面兜底。
class AndroidAccountPal implements AccountPal {
  @override
  String get providerName => '微信登录';

  @override
  Future<AccountProfile?> signIn() async => null;

  @override
  Future<void> signOut() async {}
}

PlatformPal createAndroidPlatformPal() {
  return PlatformPal(
    platform: PalPlatform.android,
    storage: AndroidStoragePal(),
    account: AndroidAccountPal(),
    screenTime: const CurfewScreenTimePal(),
  );
}
