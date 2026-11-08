import 'dart:convert';

import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/auth_service.dart';
import 'package:ai_learning/pal/storage_pal.dart';
import 'package:flutter_test/flutter_test.dart';

class _MemoryStorage implements StoragePal {
  final Map<String, String> values = {};

  @override
  Future<void> init() async {}

  @override
  Future<String?> read(String key) async => values[key];

  @override
  Future<void> write(String key, String value) async => values[key] = value;

  @override
  Future<void> delete(String key) async => values.remove(key);
}

class _FakeApi extends ApiClient {
  Map<String, dynamic>? meResponse;
  ApiException? getError;
  final List<String> log = [];
  Map<String, dynamic>? lastBody;

  @override
  Future<Map<String, dynamic>> postForm(
    String path,
    Map<String, String> form,
  ) async {
    log.add('form:$path');
    return {
      'access_token': 'access-1',
      'refresh_token': 'refresh-1',
      'token_type': 'bearer',
      'expires_in': 7200,
    };
  }

  @override
  Future<Map<String, dynamic>> getJson(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    log.add('get:$path');
    final error = getError;
    if (error != null) throw error;
    return meResponse ?? {'id': 1, 'phone': '13900000000', 'role': 'student'};
  }

  @override
  Future<Map<String, dynamic>> postJson(
    String path,
    Map<String, dynamic> body,
  ) async {
    log.add('post:$path');
    lastBody = body;
    return {'ok': true};
  }
}

void main() {
  test('登录保存双 Token 与用户缓存', () async {
    final storage = _MemoryStorage();
    final api = _FakeApi();
    final auth = AuthService(api, storage);

    final user = await auth.login(phone: '13900000000', password: 'pass');

    expect(user.phone, '13900000000');
    expect(storage.values['auth_token'], 'access-1');
    expect(storage.values['auth_refresh_token'], 'refresh-1');
    expect(storage.values.containsKey('auth_user'), true);
  });

  test('断网启动回退缓存用户并保留 Token', () async {
    final storage = _MemoryStorage();
    await storage.write('auth_token', 'access-1');
    await storage.write('auth_refresh_token', 'refresh-1');
    await storage.write(
      'auth_user',
      jsonEncode({'id': 1, 'phone': '13900000000', 'role': 'student'}),
    );
    final api = _FakeApi()..getError = const ApiException('无法连接服务器');
    final auth = AuthService(api, storage);

    final user = await auth.restoreSession();

    expect(user, isNotNull);
    expect(user!.phone, '13900000000');
    expect(storage.values['auth_token'], 'access-1');
    expect(storage.values['auth_refresh_token'], 'refresh-1');
  });

  test('无缓存用户且断网时返回 null 但不清理 Token', () async {
    final storage = _MemoryStorage();
    await storage.write('auth_token', 'access-1');
    await storage.write('auth_refresh_token', 'refresh-1');
    final api = _FakeApi()..getError = const ApiException('无法连接服务器');
    final auth = AuthService(api, storage);

    expect(await auth.restoreSession(), isNull);
    expect(storage.values['auth_token'], 'access-1');
  });

  test('401 启动时清空会话', () async {
    final storage = _MemoryStorage();
    await storage.write('auth_token', 'access-1');
    await storage.write('auth_refresh_token', 'refresh-1');
    await storage.write('auth_user', '{}');
    final api = _FakeApi()
      ..getError = const ApiException('登录状态已失效', statusCode: 401);
    final auth = AuthService(api, storage);

    expect(await auth.restoreSession(), isNull);
    expect(storage.values.containsKey('auth_token'), false);
    expect(storage.values.containsKey('auth_refresh_token'), false);
    expect(storage.values.containsKey('auth_user'), false);
  });

  test('在线启动成功后刷新用户缓存', () async {
    final storage = _MemoryStorage();
    await storage.write('auth_token', 'access-1');
    await storage.write('auth_refresh_token', 'refresh-1');
    final api = _FakeApi();
    final auth = AuthService(api, storage);

    final user = await auth.restoreSession();

    expect(user?.id, 1);
    final cached = jsonDecode(storage.values['auth_user']!) as Map;
    expect(cached['phone'], '13900000000');
  });

  test('登出调用服务端并清空本地', () async {
    final storage = _MemoryStorage();
    await storage.write('auth_token', 'access-1');
    await storage.write('auth_refresh_token', 'refresh-1');
    await storage.write('auth_user', '{}');
    final api = _FakeApi();
    final auth = AuthService(api, storage);

    await auth.logout();

    expect(api.log, contains('post:/api/auth/logout'));
    expect(api.lastBody?['refresh_token'], 'refresh-1');
    expect(storage.values, isEmpty);
  });
}
