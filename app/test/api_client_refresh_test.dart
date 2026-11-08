import 'dart:convert';
import 'dart:typed_data';

import 'package:ai_learning/core/services/api_client.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeAdapter implements HttpClientAdapter {
  _FakeAdapter(this.handler);

  final Future<ResponseBody> Function(RequestOptions options) handler;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) {
    return handler(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _json(int status, Map<String, dynamic> body) {
  return ResponseBody.fromString(
    jsonEncode(body),
    status,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );
}

ApiClient _client(_FakeAdapter adapter) {
  final dio = Dio(BaseOptions(baseUrl: 'http://test.local'));
  dio.httpClientAdapter = adapter;
  return ApiClient(dio: dio);
}

void main() {
  test('401 时自动刷新并重发原请求', () async {
    var refreshCalls = 0;
    var homeCalls = 0;
    final api = _client(
      _FakeAdapter((options) async {
        if (options.path == '/api/learn/home') {
          homeCalls++;
          final auth = options.headers['Authorization'];
          if (auth == 'Bearer old-access') {
            return _json(401, {'detail': '登录状态已失效'});
          }
          return _json(200, {'ok': true, 'token': auth});
        }
        return _json(404, {'detail': 'not found'});
      }),
    );
    api.setTokens(access: 'old-access', refresh: 'refresh-1');
    api.onRefresh = (refreshToken) async {
      refreshCalls++;
      expect(refreshToken, 'refresh-1');
      return const AuthTokens(
        accessToken: 'new-access',
        refreshToken: 'refresh-2',
      );
    };

    final data = await api.getJson('/api/learn/home');

    expect(data['ok'], true);
    expect(data['token'], 'Bearer new-access');
    expect(refreshCalls, 1);
    expect(homeCalls, 2);
  });

  test('并发 401 只触发一次刷新（单飞）', () async {
    var refreshCalls = 0;
    final api = _client(
      _FakeAdapter((options) async {
        final auth = options.headers['Authorization'];
        if (auth == 'Bearer old-access') {
          return _json(401, {'detail': '登录状态已失效'});
        }
        return _json(200, {'ok': true});
      }),
    );
    api.setTokens(access: 'old-access', refresh: 'refresh-1');
    api.onRefresh = (refreshToken) async {
      refreshCalls++;
      await Future<void>.delayed(const Duration(milliseconds: 20));
      return const AuthTokens(
        accessToken: 'new-access',
        refreshToken: 'refresh-2',
      );
    };

    final results = await Future.wait([
      api.getJson('/api/learn/home'),
      api.getJson('/api/learn/stats'),
    ]);

    expect(results, hasLength(2));
    expect(refreshCalls, 1);
  });

  test('刷新明确返回 401 时回调会话失效', () async {
    var expired = false;
    final api = _client(
      _FakeAdapter(
        (options) async => _json(401, {'detail': '登录状态已失效'}),
      ),
    );
    api.setTokens(access: 'old-access', refresh: 'refresh-1');
    api.onRefresh = (refreshToken) async {
      throw const ApiException('invalid', statusCode: 401);
    };
    api.onSessionExpired = () async => expired = true;

    await expectLater(
      api.getJson('/api/learn/home'),
      throwsA(isA<ApiException>()),
    );
    expect(expired, true);
  });

  test('刷新遇到网络错误时不清除登录态', () async {
    var expired = false;
    final api = _client(
      _FakeAdapter(
        (options) async => _json(401, {'detail': '登录状态已失效'}),
      ),
    );
    api.setTokens(access: 'old-access', refresh: 'refresh-1');
    api.onRefresh = (refreshToken) async {
      throw const ApiException('无法连接服务器');
    };
    api.onSessionExpired = () async => expired = true;

    await expectLater(
      api.getJson('/api/learn/home'),
      throwsA(isA<ApiException>()),
    );
    expect(expired, false);
  });

  test('登录接口的 401 不触发刷新', () async {
    var refreshCalls = 0;
    final api = _client(
      _FakeAdapter(
        (options) async => _json(401, {'detail': '手机号或密码错误'}),
      ),
    );
    api.setTokens(access: 'old-access', refresh: 'refresh-1');
    api.onRefresh = (refreshToken) async {
      refreshCalls++;
      return const AuthTokens(accessToken: 'a', refreshToken: 'b');
    };

    await expectLater(
      api.postForm('/api/auth/login', {'username': 'x', 'password': 'y'}),
      throwsA(isA<ApiException>()),
    );
    expect(refreshCalls, 0);
  });
}
