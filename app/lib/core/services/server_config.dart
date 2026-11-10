import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:ai_learning/pal/storage_pal.dart';

/// 服务地址配置（UX-03）：运行时可改，持久化到本地存储。
class ServerConfig {
  ServerConfig._();

  static const String baseUrlKey = 'server.baseUrl';

  /// 规范化服务地址：必须带 http/https 与主机，去掉末尾斜杠；非法返回 null。
  static String? normalize(String raw) {
    var value = raw.trim();
    if (value.isEmpty) return null;
    final uri = Uri.tryParse(value);
    if (uri == null || !uri.hasScheme || uri.host.isEmpty) return null;
    if (uri.scheme != 'http' && uri.scheme != 'https') return null;
    while (value.endsWith('/')) {
      value = value.substring(0, value.length - 1);
    }
    return value.isEmpty ? null : value;
  }
}

class ServerConfigStore {
  ServerConfigStore(this._storage);

  final StoragePal _storage;

  Future<String> baseUrl() async {
    try {
      final saved = ServerConfig.normalize(
        await _storage.read(ServerConfig.baseUrlKey) ?? '',
      );
      if (saved != null) return saved;
    } catch (_) {
      // 读取失败回落编译期默认值。
    }
    return AppConfig.apiBaseUrl;
  }

  /// 保存规范化后的地址；格式非法返回 false。
  Future<bool> saveBaseUrl(String raw) async {
    final value = ServerConfig.normalize(raw);
    if (value == null) return false;
    try {
      await _storage.write(ServerConfig.baseUrlKey, value);
    } catch (_) {
      // 落盘失败仍允许本次会话内生效。
    }
    return true;
  }
}
