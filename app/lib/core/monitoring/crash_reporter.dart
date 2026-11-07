import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/pal/storage_pal.dart';
import 'package:flutter/foundation.dart';

typedef CrashSender = Future<void> Function(Map<String, dynamic> payload);

/// R-09 崩溃与错误监控：捕获 Flutter/平台异常，本地排队后上报后端 `/api/monitor/crash`。
///
/// 设计要点：
/// - 上报不携带账号密码等敏感信息，手机号/邮箱在客户端先掩码，服务端再清洗一次。
/// - 断网或 5xx 时保留队列，下次启动重放；参数非法（4xx）直接丢弃，避免死循环。
/// - 队列上限 [maxQueued]，防止本地存储被异常风暴写满。
class CrashReporter {
  CrashReporter({
    required StoragePal storage,
    CrashSender? sender,
    String appVersion = AppConfig.versionLabel,
    DateTime Function()? clock,
  })  : _storage = storage,
        _sender = sender,
        _appVersion = appVersion,
        _clock = clock ?? DateTime.now;

  static const String queueKey = 'crash_report_queue';
  static const int maxQueued = 10;
  static const int maxMessageChars = 500;
  static const int maxStackChars = 4000;

  final StoragePal _storage;
  final CrashSender? _sender;
  final String _appVersion;
  final DateTime Function() _clock;
  ApiClient? _api;

  /// 安装全局异常钩子；必须在 `runApp` 前调用。
  void install() {
    final previous = FlutterError.onError;
    FlutterError.onError = (details) {
      previous?.call(details);
      unawaited(
        enqueue(
          message: details.exceptionAsString(),
          stack: details.stack?.toString(),
          errorType: details.exception.runtimeType.toString(),
        ),
      );
    };
    PlatformDispatcher.instance.onError = (error, stack) {
      unawaited(
        enqueue(
          message: error.toString(),
          stack: stack.toString(),
          errorType: error.runtimeType.toString(),
        ),
      );
      return true;
    };
  }

  Future<void> enqueue({
    required String message,
    String? stack,
    String? errorType,
    String? route,
    DateTime? occurredAt,
  }) async {
    final payload = buildPayload(
      message: message,
      stack: stack,
      errorType: errorType,
      route: route,
      occurredAt: occurredAt ?? _clock(),
      appVersion: _appVersion,
    );
    final queue = await _readQueue();
    queue.add(payload);
    while (queue.length > maxQueued) {
      queue.removeAt(0);
    }
    await _writeQueue(queue);
  }

  /// 重放本地队列，返回成功上报条数；网络/5xx 失败保留剩余队列。
  Future<int> flush() async {
    final queue = await _readQueue();
    if (queue.isEmpty) return 0;
    final remaining = <Map<String, dynamic>>[];
    var sent = 0;
    for (var index = 0; index < queue.length; index++) {
      try {
        await (_sender ?? _defaultSender)(queue[index]);
        sent++;
      } catch (error) {
        if (error is ApiException &&
            error.statusCode != null &&
            error.statusCode! >= 400 &&
            error.statusCode! < 500 &&
            error.statusCode != 429) {
          continue; // 参数不被接受：丢弃该条，避免重复失败
        }
        remaining.addAll(queue.sublist(index));
        break;
      }
    }
    await _writeQueue(remaining);
    return sent;
  }

  Future<List<Map<String, dynamic>>> _readQueue() async {
    final raw = await _storage.read(queueKey);
    if (raw == null || raw.isEmpty) return <Map<String, dynamic>>[];
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) return <Map<String, dynamic>>[];
      return decoded
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();
    } catch (_) {
      return <Map<String, dynamic>>[];
    }
  }

  Future<void> _writeQueue(List<Map<String, dynamic>> queue) async {
    if (queue.isEmpty) {
      await _storage.delete(queueKey);
      return;
    }
    await _storage.write(queueKey, jsonEncode(queue));
  }

  Future<void> _defaultSender(Map<String, dynamic> payload) async {
    final api = _api ??= ApiClient();
    await api.postJson('/api/monitor/crash', payload);
  }

  /// 构造上报体（纯函数，便于单测）：掩码手机号/邮箱、去控制字符、截断超长字段。
  static Map<String, dynamic> buildPayload({
    required String message,
    String? stack,
    String? errorType,
    String? route,
    DateTime? occurredAt,
    String appVersion = AppConfig.versionLabel,
    String? platform,
    String? osVersion,
    String? deviceModel,
  }) {
    final now = occurredAt ?? DateTime.now();
    return {
      'message': _cleanText(message, maxMessageChars) ?? 'unknown error',
      'stack': _cleanText(stack, maxStackChars),
      'error_type': _cleanText(errorType, 80),
      'route': _cleanText(route, 120),
      'platform': platform ?? _platformName(),
      'os_version': _cleanText(osVersion ?? _osVersion(), 80),
      'device_model': _cleanText(deviceModel, 80),
      'app_version': appVersion,
      'occurred_at': now.toUtc().toIso8601String(),
    };
  }

  static String _platformName() {
    if (kIsWeb) return 'web';
    return defaultTargetPlatform.name;
  }

  static String? _osVersion() {
    try {
      return Platform.operatingSystemVersion;
    } catch (_) {
      return null;
    }
  }

  static final RegExp _controlRe = RegExp(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]');
  static final RegExp _phoneRe = RegExp(r'(?<!\d)(1[3-9]\d{9})(?!\d)');
  static final RegExp _emailRe = RegExp(r'[\w.+-]+@[\w-]+\.[\w.]+');

  static String? _cleanText(String? value, int limit) {
    if (value == null) return null;
    var text = value
        .replaceAll(_controlRe, '')
        .replaceAll(_phoneRe, '1**********')
        .replaceAll(_emailRe, '***@***')
        .trim();
    if (text.isEmpty) return null;
    return text.length <= limit ? text : text.substring(0, limit);
  }
}
