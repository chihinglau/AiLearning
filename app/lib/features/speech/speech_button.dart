import 'dart:async';

import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/speech/question_audio.dart';
import 'package:ai_learning/core/speech/tts_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 题干右上角的读题按钮（TT-01 / TT-04）：点击播放/停止，长按立即停止。
///
/// 传 [questionId] 时优先播放服务端预生成音频（TT-04 按需缓存），
/// 未就绪/离线/解码失败时自动回退系统 TTS。
class SpeechButton extends ConsumerStatefulWidget {
  const SpeechButton({
    super.key,
    required this.text,
    this.language = 'zh-CN',
    this.questionId,
  });

  /// 已按读法规则清洗过的朗读文本。
  final String text;

  /// 中文题 `zh-CN`，英语题 `en-US`。
  final String language;

  /// 题目 ID：用于请求预生成音频；为空则只用系统 TTS。
  final int? questionId;

  @override
  ConsumerState<SpeechButton> createState() => _SpeechButtonState();
}

class _SpeechButtonState extends ConsumerState<SpeechButton> {
  late final TtsService _tts;
  late final QuestionAudioService _audio;
  bool _unsupported = false;

  bool get _active => _tts.speaking.value || _audio.playing.value;

  @override
  void initState() {
    super.initState();
    _tts = ref.read(ttsServiceProvider);
    _audio = ref.read(questionAudioServiceProvider);
    _tts.speaking.addListener(_onPlayingChanged);
    _audio.playing.addListener(_onPlayingChanged);
  }

  @override
  void dispose() {
    _tts.speaking.removeListener(_onPlayingChanged);
    _audio.playing.removeListener(_onPlayingChanged);
    unawaited(_stopAll());
    super.dispose();
  }

  void _onPlayingChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _stopAll() async {
    await _audio.stop();
    await _tts.stop();
  }

  Future<void> _toggle() async {
    if (_active) {
      await _stopAll();
      return;
    }
    final speed = await ref.read(speechSettingsStoreProvider).speed();
    final questionId = widget.questionId;
    if (questionId != null) {
      final played = await _audio.play(questionId, speed: speed);
      if (played) return;
    }
    try {
      await _tts.speak(widget.text, language: widget.language, speed: speed);
    } catch (_) {
      if (!mounted) return;
      setState(() => _unsupported = true);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('当前设备暂不支持朗读')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final speaking = _active;
    final label = _unsupported
        ? '当前设备暂不支持朗读'
        : (speaking ? '停止朗读' : '朗读题目');
    return Semantics(
      button: true,
      label: label,
      onTap: _unsupported ? null : () => unawaited(_toggle()),
      child: ExcludeSemantics(
        child: InkResponse(
          onTap: _unsupported ? null : () => unawaited(_toggle()),
          onLongPress: _unsupported ? null : () => unawaited(_stopAll()),
          radius: 20,
          child: SizedBox(
            width: 32,
            height: 32,
            child: Icon(
              speaking
                  ? Icons.stop_circle_outlined
                  : Icons.volume_up_outlined,
              size: 22,
              color: _unsupported
                  ? Theme.of(context).disabledColor
                  : Theme.of(context).colorScheme.primary,
            ),
          ),
        ),
      ),
    );
  }
}
