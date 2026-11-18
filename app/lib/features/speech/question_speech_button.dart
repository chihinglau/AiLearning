import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/speech/question_audio.dart';
import 'package:ai_learning/core/speech/question_speech.dart';
import 'package:ai_learning/core/speech/speech_policy.dart';
import 'package:ai_learning/features/speech/speech_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 题目朗读/听力按钮的统一入口，避免三个页面各写一份判定与参数。
///
/// 两类行为：
/// - 普通题：播读题干 + 选项（`QuestionSpeech.questionScript`），受 [SpeechPolicy] 年级/科目门禁；
/// - 听力题（`qType == listening`）：播放听力材料（`content.script`），走 `kind=listening`。
///   听力音频是作答必需品，不受读题门禁限制（英语本身已全年级开放）。
class QuestionSpeechButton extends ConsumerWidget {
  const QuestionSpeechButton({
    super.key,
    required this.question,
    this.showLabel = false,
  });

  final Question question;

  /// 听力题建议传 true：渲染成带文字的按钮（「播放听力材料」），
  /// 触摸目标大、低年级学生一眼能认出，避免只靠题干旁的小图标。
  final bool showLabel;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final grade = ref.watch(currentUserProvider)?.grade;
    final isListening = question.isListening;
    if (!isListening &&
        !SpeechPolicy.enabled(grade: grade, subject: question.subject)) {
      return const SizedBox.shrink();
    }
    final language = question.subject == 'english' ? 'en-US' : 'zh-CN';
    final text = isListening
        ? (question.listeningScript ?? '')
        : QuestionSpeech.questionScript(
            stem: question.stem,
            options: question.options,
          );
    return SpeechButton(
      text: text,
      language: language,
      questionId: question.id,
      audioKind: isListening
          ? QuestionAudioKind.listening
          : QuestionAudioKind.reading,
      showLabel: showLabel && isListening,
      idleLabel: isListening ? '播放听力材料' : '朗读题目',
    );
  }
}
