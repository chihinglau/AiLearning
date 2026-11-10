import 'package:ai_learning/core/speech/question_audio.dart';
import 'package:ai_learning/core/speech/tts_service.dart';

/// 统一读题入口（TT-04/TT-05）：优先播放服务端预生成音频，未就绪/离线回退系统 TTS。
class QuestionReader {
  QuestionReader({
    required TtsService tts,
    required QuestionAudioService audio,
  })  : _tts = tts,
        _audio = audio;

  final TtsService _tts;
  final QuestionAudioService _audio;

  bool get active => _tts.speaking.value || _audio.playing.value;

  /// 播放一道题；系统 TTS 也不可用时抛出异常，由调用方提示。
  Future<void> read({
    required int? questionId,
    required String text,
    required String language,
    required double speed,
  }) async {
    if (questionId != null) {
      final played = await _audio.play(questionId, speed: speed);
      if (played) return;
    }
    await _tts.speak(text, language: language, speed: speed);
  }

  Future<void> stop() async {
    await _audio.stop();
    await _tts.stop();
  }
}
