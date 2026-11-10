import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/speech/speech_settings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 学习设置（TT-01 / TT-05）：读题语速与低年级自动读题。
class LearningSettingsPage extends ConsumerStatefulWidget {
  const LearningSettingsPage({super.key});

  @override
  ConsumerState<LearningSettingsPage> createState() =>
      _LearningSettingsPageState();
}

class _LearningSettingsPageState extends ConsumerState<LearningSettingsPage> {
  double _speed = SpeechSettings.defaultSpeed;
  bool _autoRead = false;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final store = ref.read(speechSettingsStoreProvider);
    final grade = ref.read(currentUserProvider)?.grade;
    final speed = await store.speed();
    final autoRead = await store.autoReadEnabled(grade: grade);
    if (!mounted) return;
    setState(() {
      _speed = speed;
      _autoRead = autoRead;
      _loading = false;
    });
  }

  Future<void> _select(double speed) async {
    setState(() => _speed = speed);
    await ref.read(speechSettingsStoreProvider).saveSpeed(speed);
  }

  Future<void> _toggleAutoRead(bool enabled) async {
    setState(() => _autoRead = enabled);
    await ref.read(speechSettingsStoreProvider).saveAutoRead(enabled);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('学习设置')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text('自动读题', style: theme.textTheme.titleMedium),
                const SizedBox(height: 8),
                Text(
                  '打开后，1–3 年级语文、数学、英语题目进入时会自动朗读题干与选项；'
                  '仍可随时点击题干右侧喇叭停止或重播。',
                  style: theme.textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                Card(
                  child: SwitchListTile(
                    title: const Text('进入新题目时自动朗读'),
                    subtitle: Text(
                      SpeechSettings.defaultAutoRead(
                        ref.watch(currentUserProvider)?.grade,
                      )
                          ? '当前年级默认开启'
                          : '当前年级默认关闭',
                    ),
                    value: _autoRead,
                    onChanged: _toggleAutoRead,
                  ),
                ),
                const SizedBox(height: 24),
                Text('读题语速', style: theme.textTheme.titleMedium),
                const SizedBox(height: 8),
                Text(
                  '1–3 年级语文、数学、英语题目可点击题干右侧的喇叭朗读，'
                  '语速设置会立即生效。',
                  style: theme.textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
                for (final speed in SpeechSettings.speedOptions)
                  Card(
                    child: ListTile(
                      title: Text(
                        '${SpeechSettings.speedLabel(speed)} · '
                        '${speed.toStringAsFixed(2)}×',
                      ),
                      trailing: speed == _speed
                          ? Icon(
                              Icons.check_circle_outline,
                              color: theme.colorScheme.primary,
                            )
                          : null,
                      onTap: () => _select(speed),
                    ),
                  ),
              ],
            ),
    );
  }
}
