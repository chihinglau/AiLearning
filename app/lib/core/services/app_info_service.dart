import 'package:ai_learning/core/models/app_info.dart';
import 'package:ai_learning/core/services/api_client.dart';

/// R-06：读取应用信息与备案号；失败时回退本地常量，保证关于页可用。
class AppInfoService {
  AppInfoService(this._client);

  final ApiClient _client;

  Future<AppInfo> fetch() async {
    try {
      return AppInfo.fromJson(await _client.getJson('/app/info'));
    } on ApiException {
      return AppInfo.fallback();
    }
  }
}
