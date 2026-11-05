class AccountProfile {
  const AccountProfile({
    required this.provider,
    required this.openId,
    required this.displayName,
  });

  final String provider;
  final String openId;
  final String displayName;
}

/// 账号能力抽象：Android 走手机号/微信，HarmonyOS 走华为账号，二者由 Pal 隔离。
abstract class AccountPal {
  String get providerName;

  Future<AccountProfile?> signIn();

  Future<void> signOut();
}
