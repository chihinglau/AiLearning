import 'dart:async';

import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/server_config.dart';
import 'package:ai_learning/core/speech/speech_settings.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 环境诊断（UX-03）：查看/修改服务地址，检测连通性，定位「服务地址不可用」类问题。
class EnvironmentDiagnosticsPage extends ConsumerStatefulWidget {
  const EnvironmentDiagnosticsPage({super.key});

  @override
  ConsumerState<EnvironmentDiagnosticsPage> createState() =>
      _EnvironmentDiagnosticsPageState();
}

class _EnvironmentDiagnosticsPageState
    extends ConsumerState<EnvironmentDiagnosticsPage> {
  final _urlController = TextEditingController();
  bool _loading = true;
  bool _checking = false;
  bool _saving = false;
  String? _checkResult;
  String? _checkError;
  int? _latencyMs;
  bool _autoRead = false;
  double _speed = SpeechSettings.defaultSpeed;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final store = ref.read(speechSettingsStoreProvider);
    final grade = ref.read(currentUserProvider)?.grade;
    final autoRead = await store.autoReadEnabled(grade: grade);
    final speed = await store.speed();
    if (!mounted) return;
    _urlController.text = ref.read(apiClientProvider).baseUrl;
    setState(() {
      _autoRead = autoRead;
      _speed = speed;
      _loading = false;
    });
    unawaited(_check());
  }

  Future<void> _check() async {
    setState(() {
      _checking = true;
      _checkResult = null;
      _checkError = null;
      _latencyMs = null;
    });
    final startedAt = DateTime.now();
    try {
      final data = await ref.read(apiClientProvider).getJson('/health');
      if (!mounted) return;
      setState(() {
        _latencyMs = DateTime.now().difference(startedAt).inMilliseconds;
        _checkResult = '${data['status'] ?? 'ok'} · ${data['app'] ?? '服务正常'}';
        _checking = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _checkError = error.message;
        _checking = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _checkError = '无法连接服务器，请检查服务地址与网络';
        _checking = false;
      });
    }
  }

  Future<void> _save() async {
    final raw = _urlController.text;
    if (ServerConfig.normalize(raw) == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('服务地址格式不正确，需形如 http://192.168.1.10:18080')),
      );
      return;
    }
    setState(() => _saving = true);
    final saved = await ref.read(serverConfigStoreProvider).saveBaseUrl(raw);
    if (!mounted) return;
    if (saved) {
      final normalized = ServerConfig.normalize(raw)!;
      ref.read(apiClientProvider).setBaseUrl(normalized);
      _urlController.text = normalized;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('服务地址已保存并立即生效')),
      );
      await _check();
    }
    if (mounted) setState(() => _saving = false);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final user = ref.watch(currentUserProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('环境诊断')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('应用信息', style: theme.textTheme.titleMedium),
                        const SizedBox(height: 8),
                        _row('应用', AppConfig.displayName),
                        _row('版本', AppConfig.versionLabel),
                        _row('平台', _platformLabel()),
                        _row('登录状态', user == null
                            ? '未登录'
                            : '${user.nickname}（${user.role}）'),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('服务连通性', style: theme.textTheme.titleMedium),
                        const SizedBox(height: 8),
                        _row('服务地址', ref.read(apiClientProvider).baseUrl),
                        if (_checking)
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 8),
                            child: LinearProgressIndicator(),
                          )
                        else if (_checkError != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text(
                              '连接失败：$_checkError',
                              style: TextStyle(color: theme.colorScheme.error),
                            ),
                          )
                        else if (_checkResult != null)
                          _row(
                            '健康检查',
                            '$_checkResult · ${_latencyMs ?? 0} ms',
                          ),
                        const SizedBox(height: 8),
                        OutlinedButton.icon(
                          onPressed: _checking ? null : _check,
                          icon: const Icon(Icons.network_check),
                          label: const Text('重新检测'),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('服务地址', style: theme.textTheme.titleMedium),
                        const SizedBox(height: 8),
                        Text(
                          '修改后立即生效，无需重启；地址需包含 http/https 与端口。'
                          '切换环境后如提示登录失效，请重新登录。',
                          style: theme.textTheme.bodySmall,
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _urlController,
                          keyboardType: TextInputType.url,
                          decoration: const InputDecoration(
                            border: OutlineInputBorder(),
                            labelText: 'API 地址',
                            hintText: 'http://192.168.1.10:18080',
                          ),
                        ),
                        const SizedBox(height: 12),
                        FilledButton(
                          onPressed: _saving ? null : _save,
                          child: Text(_saving ? '保存中…' : '保存并应用'),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('学习能力', style: theme.textTheme.titleMedium),
                        const SizedBox(height: 8),
                        _row('自动读题', _autoRead ? '已开启' : '已关闭'),
                        _row('读题语速', '${_speed.toStringAsFixed(2)}×'),
                        _row(
                          '预生成音频',
                          '1–3 年级语数英可用；未就绪时自动回退系统朗读',
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
    );
  }

  Widget _row(String label, String value) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 84,
            child: Text(label, style: theme.textTheme.bodySmall),
          ),
          Expanded(child: Text(value, style: theme.textTheme.bodyMedium)),
        ],
      ),
    );
  }

  String _platformLabel() {
    if (kIsWeb) return 'Web';
    return defaultTargetPlatform.name;
  }
}
