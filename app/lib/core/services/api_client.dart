import 'dart:typed_data';

import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:dio/dio.dart';

/// 二进制响应：读题音频等非 JSON 资源。
class ApiBinary {
  const ApiBinary({required this.bytes, this.etag, this.notModified = false});

  final Uint8List bytes;
  final String? etag;
  final bool notModified;
}

class ApiException implements Exception {
  const ApiException(
    this.message, {
    this.statusCode,
    this.payload,
    this.code,
  });

  final String message;
  final int? statusCode;

  /// 后端结构化错误体（如 428 的 impact / confirm_token）。
  final Map<String, dynamic>? payload;

  /// 统一业务错误码（如 TOKEN_REVOKED、PERMISSION_DENIED）。
  final String? code;

  @override
  String toString() => message;
}

/// 双 Token 组合：access 短效 + refresh 长效。
class AuthTokens {
  const AuthTokens({required this.accessToken, required this.refreshToken});

  final String accessToken;
  final String refreshToken;

  factory AuthTokens.fromJson(Map<String, dynamic> json) {
    return AuthTokens(
      accessToken: json['access_token'] as String? ?? '',
      refreshToken: json['refresh_token'] as String? ?? '',
    );
  }
}

typedef TokenRefreshCallback = Future<AuthTokens?> Function(String refreshToken);

class ApiClient {
  ApiClient({String baseUrl = AppConfig.apiBaseUrl, Dio? dio})
      : _dio = dio ??
            Dio(
              BaseOptions(
                baseUrl: baseUrl,
                connectTimeout: const Duration(seconds: 10),
                receiveTimeout: const Duration(seconds: 15),
                contentType: Headers.jsonContentType,
              ),
            ) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final token = _token;
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          if (_shouldRefresh(error)) {
            final refreshed = await _tryRefresh();
            if (refreshed) {
              final options = error.requestOptions;
              options.extra['retried'] = true;
              final token = _token;
              if (token != null && token.isNotEmpty) {
                options.headers['Authorization'] = 'Bearer $token';
              }
              try {
                final response = await _dio.fetch<dynamic>(options);
                return handler.resolve(response);
              } on DioException catch (retryError) {
                return handler.next(retryError);
              }
            }
          }
          handler.next(error);
        },
      ),
    );
  }

  final Dio _dio;
  String? _token;
  String? _refreshToken;

  /// 当前生效的服务地址（UX-03 环境诊断展示用）。
  String get baseUrl => _dio.options.baseUrl;

  /// 运行时切换服务地址，后续请求立即生效。
  void setBaseUrl(String url) {
    _dio.options.baseUrl = url;
  }

  /// 由 AuthService 注入：用 refresh token 换新双 Token。
  TokenRefreshCallback? onRefresh;

  /// 刷新明确失败（401）时回调，用于清理登录态；网络错误不触发。
  Future<void> Function()? onSessionExpired;

  Future<bool>? _refreshing;

  void setToken(String? token) {
    _token = token;
  }

  void setTokens({String? access, String? refresh}) {
    _token = access;
    _refreshToken = refresh;
  }

  bool _shouldRefresh(DioException error) {
    if (error.response?.statusCode != 401) return false;
    if (error.requestOptions.extra['retried'] == true) return false;
    final path = error.requestOptions.path;
    return !path.contains('/api/auth/login') &&
        !path.contains('/api/auth/refresh') &&
        !path.contains('/api/auth/logout');
  }

  /// 并发 401 共享同一次刷新（单飞）。
  Future<bool> _tryRefresh() {
    return _refreshing ??= _doRefresh().whenComplete(() => _refreshing = null);
  }

  Future<bool> _doRefresh() async {
    final refresh = _refreshToken;
    final callback = onRefresh;
    if (refresh == null || refresh.isEmpty || callback == null) {
      return false;
    }
    try {
      final tokens = await callback(refresh);
      if (tokens == null ||
          tokens.accessToken.isEmpty ||
          tokens.refreshToken.isEmpty) {
        return false;
      }
      setTokens(access: tokens.accessToken, refresh: tokens.refreshToken);
      return true;
    } on ApiException catch (error) {
      // 只有明确的 401 才判定会话失效；断网/5xx 保留本地登录态。
      if (error.statusCode == 401) {
        await onSessionExpired?.call();
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> getJson(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    try {
      final response = await _dio.get<dynamic>(path, queryParameters: query);
      return _asMap(response.data);
    } on DioException catch (error) {
      throw _toApiException(error);
    }
  }

  Future<List<dynamic>> getList(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    try {
      final response = await _dio.get<dynamic>(path, queryParameters: query);
      final data = response.data;
      return data is List ? data : const [];
    } on DioException catch (error) {
      throw _toApiException(error);
    }
  }

  /// 下载二进制资源（TT-04 读题音频）：支持 ETag 条件请求，304 时 [ApiBinary.bytes] 为空。
  Future<ApiBinary> getBytes(
    String path, {
    Map<String, dynamic>? query,
    String? ifNoneMatch,
  }) async {
    try {
      final response = await _dio.get<List<int>>(
        path,
        queryParameters: query,
        options: Options(
          responseType: ResponseType.bytes,
          headers: ifNoneMatch == null ? null : {'If-None-Match': ifNoneMatch},
          validateStatus: (status) => status == 200 || status == 304,
        ),
      );
      if (response.statusCode == 304) {
        return ApiBinary(
          bytes: Uint8List(0),
          etag: response.headers.value('etag'),
          notModified: true,
        );
      }
      final data = response.data;
      return ApiBinary(
        bytes: data == null ? Uint8List(0) : Uint8List.fromList(data),
        etag: response.headers.value('etag'),
      );
    } on DioException catch (error) {
      throw _toApiException(error);
    }
  }

  Future<Map<String, dynamic>> postJson(
    String path,
    Map<String, dynamic> body,
  ) async {
    try {
      final response = await _dio.post<dynamic>(path, data: body);
      return _asMap(response.data);
    } on DioException catch (error) {
      throw _toApiException(error);
    }
  }

  Future<Map<String, dynamic>> putJson(
    String path,
    Map<String, dynamic> body,
  ) async {
    try {
      final response = await _dio.put<dynamic>(path, data: body);
      return _asMap(response.data);
    } on DioException catch (error) {
      throw _toApiException(error);
    }
  }

  Future<Map<String, dynamic>> patchJson(
    String path,
    Map<String, dynamic> body,
  ) async {
    try {
      final response = await _dio.patch<dynamic>(path, data: body);
      return _asMap(response.data);
    } on DioException catch (error) {
      throw _toApiException(error);
    }
  }

  Future<Map<String, dynamic>> deleteJson(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    try {
      final response = await _dio.delete<dynamic>(path, data: body);
      return _asMap(response.data);
    } on DioException catch (error) {
      throw _toApiException(error);
    }
  }

  /// OAuth2 密码模式登录使用 form-urlencoded 提交。
  Future<Map<String, dynamic>> postForm(
    String path,
    Map<String, String> form,
  ) async {
    try {
      final response = await _dio.post<dynamic>(
        path,
        data: form,
        options: Options(contentType: Headers.formUrlEncodedContentType),
      );
      return _asMap(response.data);
    } on DioException catch (error) {
      throw _toApiException(error);
    }
  }

  Map<String, dynamic> _asMap(dynamic data) {
    return data is Map<String, dynamic> ? data : const {};
  }

  ApiException _toApiException(DioException error) {
    final statusCode = error.response?.statusCode;
    final data = error.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      final topCode = data['code'] as String?;
      if (detail is String) {
        return ApiException(
          detail,
          statusCode: statusCode,
          payload: data,
          code: topCode,
        );
      }
      if (detail is Map<String, dynamic>) {
        final code = detail['code'] as String? ?? topCode;
        final message = detail['message'] as String?;
        return ApiException(
          message ?? '请求失败（${statusCode ?? error.type.name}）',
          statusCode: statusCode,
          payload: data,
          code: code,
        );
      }
      final message = data['message'];
      if (message is String) {
        return ApiException(
          message,
          statusCode: statusCode,
          payload: data,
          code: topCode,
        );
      }
      return ApiException(
        '请求失败（${statusCode ?? error.type.name}）',
        statusCode: statusCode,
        payload: data,
        code: topCode,
      );
    }
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout) {
      return const ApiException('无法连接服务器，请检查网络或 API 地址');
    }
    return ApiException('请求失败（${statusCode ?? error.type.name}）', statusCode: statusCode);
  }
}
