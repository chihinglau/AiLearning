import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';

/// 系统 TTS 封装（方案 A 兜底）。
///
/// 只负责「把一段文本读出来」：语言、语速、停止与播放状态。
/// 引擎初始化放在首次使用时，避免单元测试/无插件环境在构造阶段触达平台通道。
class TtsService {
  TtsService({FlutterTts? engine}) : _engine = engine;

  FlutterTts? _engine;
  bool _disposed = false;

  /// 是否正在朗读，供按钮切换图标。
  final ValueNotifier<bool> speaking = ValueNotifier<bool>(false);

  /// flutter_tts 的 rate 以 0.5 为「正常语速」，业务侧 1.0 = 正常，故做线性映射。
  static double engineRate(double speed) => (speed * 0.5).clamp(0.0, 1.0);

  FlutterTts _ensureEngine() {
    final existing = _engine;
    if (existing != null) return existing;
    final engine = FlutterTts();
    engine.setCompletionHandler(_markStopped);
    engine.setCancelHandler(_markStopped);
    engine.setErrorHandler((_) => _markStopped());
    _engine = engine;
    return engine;
  }

  void _markStopped() {
    if (_disposed) return;
    speaking.value = false;
  }

  Future<void> speak(
    String text, {
    String language = 'zh-CN',
    double speed = 0.85,
  }) async {
    if (text.trim().isEmpty) return;
    final engine = _ensureEngine();
    try {
      await engine.stop();
      await engine.setLanguage(language);
      await engine.setSpeechRate(engineRate(speed));
      await engine.setVolume(1.0);
      await engine.setPitch(1.0);
      speaking.value = true;
      await engine.speak(text);
    } catch (_) {
      _markStopped();
      rethrow;
    }
  }

  Future<void> stop() async {
    _markStopped();
    final engine = _engine;
    if (engine == null) return;
    try {
      await engine.stop();
    } catch (_) {
      // 引擎不可用时静默降级，不打断答题。
    }
  }

  void dispose() {
    _disposed = true;
    speaking.dispose();
    _engine = null;
  }
}
