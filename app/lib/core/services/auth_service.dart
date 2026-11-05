import 'package:ai_learning/core/models/user.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/pal/storage_pal.dart';

const String _tokenKey = 'auth_token';

class AuthService {
  AuthService(this._api, this._storage);

  final ApiClient _api;
  final StoragePal _storage;

  Future<AppUser> login({required String phone, required String password}) async {
    final data = await _api.postForm('/api/auth/login', {
      'username': phone,
      'password': password,
    });
    final token = data['access_token'] as String?;
    if (token == null || token.isEmpty) {
      throw const ApiException('登录失败：未获取到凭证');
    }
    _api.setToken(token);
    await _storage.write(_tokenKey, token);
    return AppUser.fromJson(await _api.getJson('/api/auth/me'));
  }

  /// 启动时恢复登录态；token 失效则返回 null。
  Future<AppUser?> restoreSession() async {
    final token = await _storage.read(_tokenKey);
    if (token == null || token.isEmpty) return null;
    _api.setToken(token);
    try {
      return AppUser.fromJson(await _api.getJson('/api/auth/me'));
    } on ApiException {
      await logout();
      return null;
    }
  }

  Future<void> logout() async {
    _api.setToken(null);
    await _storage.delete(_tokenKey);
  }
}
