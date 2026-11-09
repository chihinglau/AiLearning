import 'dart:convert';

import 'package:ai_learning/core/models/user.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/pal/storage_pal.dart';

const String _tokenKey = 'auth_token';
const String _refreshKey = 'auth_refresh_token';
const String _userKey = 'auth_user';
const String _onboardingKey = 'onboarding_status';

/// 双 Token 登录态：access 短效自动续期，refresh 长效保证长期免登录与离线启动。
class AuthService {
  AuthService(this._api, this._storage) {
    // 请求 401 时由 ApiClient 自动用 refresh 换新 Token。
    _api.onRefresh = _refreshTokens;
  }

  final ApiClient _api;
  final StoragePal _storage;

  Future<AppUser> login({
    required String phone,
    required String password,
  }) async {
    final data = await _api.postForm('/api/auth/login', {
      'username': phone,
      'password': password,
    });
    final token = data['access_token'] as String?;
    if (token == null || token.isEmpty) {
      throw const ApiException('登录失败：未获取到凭证');
    }
    final refresh = data['refresh_token'] as String? ?? '';
    _api.setTokens(access: token, refresh: refresh.isEmpty ? null : refresh);
    await _storage.write(_tokenKey, token);
    if (refresh.isNotEmpty) {
      await _storage.write(_refreshKey, refresh);
    } else {
      await _storage.delete(_refreshKey);
    }
    final me = await _api.getJson('/api/auth/me');
    await _storage.write(_userKey, jsonEncode(me));
    return AppUser.fromJson(me);
  }

  /// 启动时恢复登录态。
  ///
  /// - 联网成功：刷新本地缓存用户。
  /// - 断网/5xx：回退本地缓存用户（离线可用）。
  /// - 明确 401：清理会话返回 null。
  Future<AppUser?> restoreSession() async {
    final access = await _storage.read(_tokenKey);
    final refresh = await _storage.read(_refreshKey);
    if ((access == null || access.isEmpty) &&
        (refresh == null || refresh.isEmpty)) {
      return null;
    }
    _api.setTokens(access: access, refresh: refresh);
    try {
      final me = await _api.getJson('/api/auth/me');
      await _storage.write(_userKey, jsonEncode(me));
      return AppUser.fromJson(me);
    } on ApiException catch (error) {
      if (error.statusCode == 401) {
        await clearSession();
        return null;
      }
      // 网络错误（statusCode == null）或服务端 5xx：保留登录态并回退缓存。
      return _readCachedUser();
    }
  }

  /// 缓存当前用户，供断网启动时恢复（如同意新协议后需立即落盘）。
  Future<void> cacheUser(AppUser user) async {
    await _storage.write(_userKey, jsonEncode(user.toJson()));
  }

  Future<AppUser?> _readCachedUser() async {
    final raw = await _storage.read(_userKey);
    if (raw == null || raw.isEmpty) return null;
    try {
      final json = jsonDecode(raw);
      if (json is Map<String, dynamic>) {
        return AppUser.fromJson(json);
      }
    } on FormatException {
      // 缓存损坏时忽略，走重新登录。
    }
    return null;
  }

  Future<AuthTokens?> _refreshTokens(String refreshToken) async {
    final data = await _api.postJson('/api/auth/refresh', {
      'refresh_token': refreshToken,
    });
    final tokens = AuthTokens.fromJson(data);
    if (tokens.accessToken.isEmpty || tokens.refreshToken.isEmpty) {
      return null;
    }
    await _storage.write(_tokenKey, tokens.accessToken);
    await _storage.write(_refreshKey, tokens.refreshToken);
    return tokens;
  }

  Future<void> logout() async {
    final refresh = await _storage.read(_refreshKey);
    if (refresh != null && refresh.isNotEmpty) {
      try {
        await _api.postJson('/api/auth/logout', {'refresh_token': refresh});
      } on ApiException {
        // 离线登出：本地清理即可，服务端令牌到期自然失效。
      }
    }
    await clearSession();
  }

  /// 仅清理本地登录态（不请求服务端），供会话失效回调使用。
  Future<void> clearSession() async {
    _api.setTokens(access: null, refresh: null);
    await _storage.delete(_tokenKey);
    await _storage.delete(_refreshKey);
    await _storage.delete(_userKey);
  }

  Future<String?> readOnboardingStatus() {
    return _storage.read(_onboardingKey);
  }

  Future<void> writeOnboardingStatus(String status) {
    return _storage.write(_onboardingKey, status);
  }
}
