import 'package:ai_learning/pal/storage_pal.dart';

/// 读题设置（设计 §3.9.4 / §3.9.12）。
class SpeechSettings {
  const SpeechSettings._();

  static const double defaultSpeed = 0.85;

  /// 可选语速：慢 / 适中 / 正常。
  static const List<double> speedOptions = [0.7, 0.85, 1.0];

  static const String speedKey = 'speech.speed';

  /// 自动读题（TT-05）：1–3 年级默认开启，其余年级默认关闭。
  static const String autoReadKey = 'speech.autoRead';

  static bool defaultAutoRead(int? grade) =>
      grade != null && grade >= 1 && grade <= 3;

  static String speedLabel(double speed) {
    if (speed <= 0.72) return '慢';
    if (speed >= 0.95) return '正常';
    return '适中';
  }
}

/// 读题设置的本地读写；读写失败一律回落默认值，不阻断答题。
class SpeechSettingsStore {
  SpeechSettingsStore(this._storage);

  final StoragePal _storage;
  double? _cached;
  bool? _autoReadCached;

  Future<double> speed() async {
    final cached = _cached;
    if (cached != null) return cached;
    var value = SpeechSettings.defaultSpeed;
    try {
      final raw = await _storage.read(SpeechSettings.speedKey);
      final parsed = double.tryParse(raw ?? '');
      if (parsed != null && SpeechSettings.speedOptions.contains(parsed)) {
        value = parsed;
      }
    } catch (_) {
      // 使用默认语速。
    }
    _cached = value;
    return value;
  }

  Future<void> saveSpeed(double value) async {
    if (!SpeechSettings.speedOptions.contains(value)) return;
    _cached = value;
    try {
      await _storage.write(SpeechSettings.speedKey, value.toString());
    } catch (_) {
      // 落盘失败仍保留本次会话内的设置。
    }
  }

  /// 未设置过时按年级给默认值：1–3 年级开启，其余关闭。
  Future<bool> autoReadEnabled({int? grade}) async {
    final cached = _autoReadCached;
    if (cached != null) return cached;
    var value = SpeechSettings.defaultAutoRead(grade);
    try {
      final raw = await _storage.read(SpeechSettings.autoReadKey);
      if (raw == 'true' || raw == 'false') value = raw == 'true';
    } catch (_) {
      // 使用年级默认值。
    }
    _autoReadCached = value;
    return value;
  }

  Future<void> saveAutoRead(bool enabled) async {
    _autoReadCached = enabled;
    try {
      await _storage.write(SpeechSettings.autoReadKey, enabled.toString());
    } catch (_) {
      // 落盘失败仍保留本次会话内的设置。
    }
  }
}
