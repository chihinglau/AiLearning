import 'dart:async';

import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/practice.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/speech/question_speech.dart';
import 'package:ai_learning/core/theme/app_accents.dart';
import 'package:ai_learning/features/speech/readable_question_text.dart';
import 'package:ai_learning/features/speech/speech_button.dart';
import 'package:ai_learning/widgets/accent_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class PracticePage extends ConsumerStatefulWidget {
  const PracticePage({
    super.key,
    required this.chapterId,
    required this.chapterName,
  });

  final int chapterId;
  final String chapterName;

  @override
  ConsumerState<PracticePage> createState() => _PracticePageState();
}

class _PracticePageState extends ConsumerState<PracticePage> {
  List<Question> _questions = const [];
  int _index = 0;
  int _correctCount = 0;
  String? _selectedKey;
  SubmitResult? _result;
  bool _loading = true;
  bool _submitting = false;
  bool _finished = false;
  String? _error;
  DateTime _startedAt = DateTime.now();

  Question? get _currentQuestion =>
      _index < _questions.length ? _questions[_index] : null;

  @override
  void initState() {
    super.initState();
    _loadQuestions();
  }

  @override
  void dispose() {
    unawaited(ref.read(questionReaderProvider).stop());
    super.dispose();
  }

  Future<void> _loadQuestions() async {
    setState(() {
      _loading = true;
      _error = null;
      _finished = false;
      _index = 0;
      _correctCount = 0;
    });
    try {
      final questions = await ref
          .read(contentServiceProvider)
          .startPractice(chapterId: widget.chapterId);
      if (!mounted) return;
      setState(() {
        _questions = questions;
        _loading = false;
        _startedAt = DateTime.now();
      });
      unawaited(_maybeAutoRead());
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = ApiErrorGuide.from(error).message;
        _loading = false;
      });
    }
  }

  Future<void> _submit() async {
    final question = _currentQuestion;
    final key = _selectedKey;
    if (question == null || key == null) return;

    setState(() => _submitting = true);
    try {
      final result = await ref
          .read(contentServiceProvider)
          .submitAnswer(
            questionId: question.id,
            optionKey: key,
            durationMs: DateTime.now().difference(_startedAt).inMilliseconds,
          );
      if (!mounted) return;
      setState(() {
        _result = result;
        if (result.isCorrect) {
          _correctCount += 1;
        }
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      await handleApiError(context, ref, error);
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  void _next() {
    if (_index + 1 >= _questions.length) {
      setState(() => _finished = true);
      return;
    }
    setState(() {
      _index += 1;
      _selectedKey = null;
      _result = null;
      _startedAt = DateTime.now();
    });
    unawaited(_maybeAutoRead());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.chapterName)),
      body: _buildBody(context),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!),
            const SizedBox(height: 12),
            FilledButton(onPressed: _loadQuestions, child: const Text('重试')),
          ],
        ),
      );
    }
    if (_finished) {
      return _buildSummary(context);
    }
    final question = _currentQuestion;
    if (question == null) {
      return const _EmptyPracticeState();
    }
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            '第 ${_index + 1} / ${_questions.length} 题 · 难度 ${question.difficulty}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: ReadableQuestionText(
                  text: question.stem,
                  spokenText: QuestionSpeech.questionScript(
                    stem: question.stem,
                    options: question.options,
                  ),
                  language:
                      question.subject == 'english' ? 'en-US' : 'zh-CN',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              if (_speechEnabled(question))
                SpeechButton(
                  key: ValueKey('speech-${question.id}'),
                  text: QuestionSpeech.questionScript(
                    stem: question.stem,
                    options: question.options,
                  ),
                  language: question.subject == 'english' ? 'en-US' : 'zh-CN',
                  questionId: question.id,
                ),
            ],
          ),
          const SizedBox(height: 20),
          ...question.options.map(
            (option) => Card(
              child: ListTile(
                selected: _selectedKey == option.key,
                leading: CircleAvatar(child: Text(option.key)),
                title: Text(option.text),
                onTap: _result == null
                    ? () => setState(() => _selectedKey = option.key)
                    : null,
              ),
            ),
          ),
          if (question.options.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Text('该题型交互将在后续版本开放，当前版本先支持选择题。'),
            ),
          const SizedBox(height: 20),
          if (_result == null)
            FilledButton(
              onPressed: _selectedKey == null || _submitting ? null : _submit,
              child: _submitting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('提交答案'),
            )
          else
            _FeedbackCard(
              result: _result!,
              onNext: _next,
              isLast: _index + 1 >= _questions.length,
            ),
        ],
      ),
    );
  }

  /// 读题仅对 1–3 年级语文/数学/英语开放（设计 §3.9.12）。
  bool _speechEnabled(Question question) {
    final grade = ref.watch(currentUserProvider)?.grade;
    if (grade == null || grade < 1 || grade > 3) return false;
    return const {'chinese', 'math', 'english'}.contains(question.subject);
  }

  /// TT-05：进入新题时按设置自动读题；同一题只触发一次，失败不阻断答题。
  String? _autoReadKey;

  Future<void> _maybeAutoRead() async {
    final question = _currentQuestion;
    if (question == null || !_speechEnabled(question)) return;
    final key = '${question.id}@$_index';
    if (_autoReadKey == key) return;
    _autoReadKey = key;
    final store = ref.read(speechSettingsStoreProvider);
    final grade = ref.read(currentUserProvider)?.grade;
    if (!await store.autoReadEnabled(grade: grade)) return;
    if (!mounted) return;
    try {
      await ref.read(questionReaderProvider).read(
            questionId: question.id,
            text: QuestionSpeech.questionScript(
              stem: question.stem,
              options: question.options,
            ),
            language: question.subject == 'english' ? 'en-US' : 'zh-CN',
            speed: await store.speed(),
          );
    } catch (_) {
      // 设备不支持朗读时静默降级。
    }
  }

  Widget _buildSummary(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.emoji_events_outlined,
              size: 72,
              color: theme.colorScheme.primary,
            ),
            const SizedBox(height: 16),
            Text(
              '本次练习完成',
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text('答对 $_correctCount / ${_questions.length} 题'),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () => context.go('/home'),
              child: const Text('返回首页'),
            ),
            TextButton(onPressed: _loadQuestions, child: const Text('再练一次')),
          ],
        ),
      ),
    );
  }
}

class _FeedbackCard extends StatelessWidget {
  const _FeedbackCard({
    required this.result,
    required this.onNext,
    required this.isLast,
  });

  final SubmitResult result;
  final VoidCallback onNext;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accents = AppAccents.of(context);
    final correctColor = result.isCorrect
        ? accents.learn
        : theme.colorScheme.error;
    return AccentCard(
      accent: correctColor,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                result.isCorrect ? Icons.check_circle : Icons.cancel,
                color: correctColor,
              ),
              const SizedBox(width: 8),
              Text(
                result.isCorrect ? '回答正确' : '回答错误',
                style: theme.textTheme.titleMedium?.copyWith(
                  color: correctColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text('正确答案：${result.correctAnswer['value'] ?? '-'}'),
          if (result.analysis != null) ...[
            const SizedBox(height: 8),
            Text(result.analysis!, style: theme.textTheme.bodyMedium),
          ],
          const SizedBox(height: 12),
          FilledButton(onPressed: onNext, child: Text(isLast ? '完成练习' : '下一题')),
        ],
      ),
    );
  }
}

/// 空态：该知识点暂无题目（内容库覆盖缺口：教材真实章节已建但还没出题）。
/// 不要退化成错误页或裸文本——用户看到的是「内容准备中」，不是「出错了」。
class _EmptyPracticeState extends StatelessWidget {
  const _EmptyPracticeState();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.hourglass_empty, size: 44, color: theme.colorScheme.outline),
            const SizedBox(height: 14),
            Text('本节内容准备中', style: theme.textTheme.titleMedium),
            const SizedBox(height: 6),
            Text(
              '该节暂无题目，教研内容正在补充中。可先返回教材目录浏览其它已更新的章节。',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}