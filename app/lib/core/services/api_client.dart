import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:dio/dio.dart';

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

class ApiClient {
  ApiClient({String baseUrl = AppConfig.apiBaseUrl})
      : _dio = Dio(
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
      ),
    );
  }

  final Dio _dio;
  String? _token;

  void setToken(String? token) {
    _token = token;
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
