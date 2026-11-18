import 'dart:async';

import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/speech/question_audio.dart';
import 'package:ai_learning/core/speech/tts_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 题干右上角的读题按钮（TT-01 / TT-04）：点击播放/停止，长按立即停止。
///
/// 传 [questionId] 时优先播放服务端预生成音频（TT-04 按需缓存），
/// 未就绪/离线/解码失败时自动回退系统 TTS。
///
/// [audioKind] 为 [QuestionAudioKind.listening] 时播放听力材料（`content.script`），
/// 走独立缓存与服务端 `kind=listening` 分支，与读题音频互不覆盖。
class SpeechButton extends ConsumerStatefulWidget {
  const SpeechButton({
    super.key,
    required this.text,
    this.language = 'zh-CN',
    this.questionId,
    this.audioKind = QuestionAudioKind.reading,
    this.showLabel = false,
    this.idleLabel = '朗读题目',
    this.attemptId,
  });

  /// 已按读法规则清洗过的朗读文本；听力题传 `content.script`，仅作 TTS 兜底。
  final String text;

  /// 中文题 `zh-CN`，英语题 `en-US`。
  final String language;

  /// 题目 ID：用于请求预生成音频；为空则只用系统 TTS。
  final int? questionId;

  /// 取哪一类预生成音频：读题（题干+选项）或听力材料。
  final QuestionAudioKind audioKind;

  /// true 时渲染成「图标 + 文字」的按钮（听力材料用），否则只渲染图标。
  final bool showLabel;

  /// 未播放时展示的文案。
  final String idleLabel;

  /// 试卷作答 id：听力材料播放次数按 (attempt, question) 记账，练习场景传 null。
  final int? attemptId;

  @override
  ConsumerState<SpeechButton> createState() => _SpeechButtonState();
}

class _SpeechButtonState extends ConsumerState<SpeechButton> {
  late final TtsService _tts;
  late final QuestionAudioService _audio;
  bool _unsupported = false;

  bool get _isListening => widget.audioKind == QuestionAudioKind.listening;

  bool get _active => _tts.speaking.value || _audio.playing.value;

  @override
  void initState() {
    super.initState();
    _tts = ref.read(ttsServiceProvider);
    _audio = _isListening
        ? ref.read(listeningAudioServiceProvider)
        : ref.read(questionAudioServiceProvider);
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
    final questionId = widget.questionId;
    // 试卷听力：先占播放额度。音频命中本地缓存时不会发音频请求，
    // 所以次数必须由这个专门的接口累计（后端按 attempt+question 记账）。
    final attemptId = widget.attemptId;
    if (_isListening && attemptId != null && questionId != null) {
      try {
        await ref
            .read(examServiceProvider)
            .takeListeningPlay(attemptId, questionId);
      } on ApiException catch (error) {
        if (!mounted) return;
        if (error.code == 'LISTENING_PLAY_LIMIT') {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(error.message)),
          );
          return;
        }
        // 其它错误（离线、网络抖动）不阻断作答，继续尝试播放本地/服务端音频。
      } catch (_) {
        // 同上：额度接口不可用时不让听力功能整体失效。
      }
    }
    final speed = await ref.read(speechSettingsStoreProvider).speed();
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
        SnackBar(
          content: Text(_isListening ? '听力音频尚未就绪，请稍后再试' : '当前设备暂不支持朗读'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final speaking = _active;
    final label = _unsupported ? '当前设备暂不支持朗读' : (speaking ? '停止播放' : widget.idleLabel);
    final icon = Icon(
      speaking
          ? Icons.stop_circle_outlined
          : (_isListening ? Icons.headphones_outlined : Icons.volume_up_outlined),
      color: _unsupported
          ? Theme.of(context).disabledColor
          : Theme.of(context).colorScheme.primary,
    );
    // 触摸目标按 Material 可达性口径给到 48×48（原 32×32 的 InkResponse 在真机上
    // 反复点不中：EBG-AN00 上耳机图标点了 3 次既没发生音频请求也没启动播放器）。
    if (widget.showLabel) {
      return OutlinedButton.icon(
        onPressed: _unsupported ? null : () => unawaited(_toggle()),
        icon: Icon(
          speaking
              ? Icons.stop_circle_outlined
              : (_isListening ? Icons.headphones_outlined : Icons.volume_up_outlined),
          size: 20,
        ),
        label: Text(label),
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(0, 44),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          tapTargetSize: MaterialTapTargetSize.padded,
        ),
      );
    }
    return IconButton(
      onPressed: _unsupported ? null : () => unawaited(_toggle()),
      tooltip: label,
      iconSize: 22,
      constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
      padding: const EdgeInsets.all(8),
      icon: icon,
    );
  }
}
