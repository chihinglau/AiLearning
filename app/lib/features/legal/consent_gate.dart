import 'package:ai_learning/core/constants/legal_constants.dart';
import 'package:ai_learning/features/legal/legal_document_page.dart';
import 'package:ai_learning/pal/storage_pal.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// 首启同意门（R-03）：未同意前不进入 App，也不发起任何网络请求。
///
/// 同意结果写入本地存储；隐私政策版本升高后需重新同意。
class ConsentGate extends StatefulWidget {
  const ConsentGate({super.key, required this.storage, required this.child});

  final StoragePal storage;
  final Widget child;

  @override
  State<ConsentGate> createState() => _ConsentGateState();
}

class _ConsentGateState extends State<ConsentGate> {
  bool _loading = true;
  bool _ready = false;
  bool _agreed = false;

  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    final saved = await widget.storage.read(kLegalConsentStorageKey);
    if (!mounted) return;
    setState(() {
      _ready = saved == kLegalPrivacyVersion;
      _loading = false;
    });
  }

  Future<void> _accept() async {
    await widget.storage.write(kLegalConsentStorageKey, kLegalPrivacyVersion);
    if (!mounted) return;
    setState(() => _ready = true);
  }

  void _openDocument(String docType) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => LegalDocumentPage(docType: docType, localOnly: true),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_ready) return widget.child;
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1E6FD9)),
      ),
      home: _loading
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : _buildGate(context),
    );
  }

  Widget _buildGate(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Icon(Icons.school_outlined, size: 64, color: theme.colorScheme.primary),
              const SizedBox(height: 16),
              Text(
                '欢迎使用深爱学',
                textAlign: TextAlign.center,
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 20),
              Text(
                '我们仅收集实现学习功能所必需的信息，不出售个人信息，不用于广告；'
                '未满 14 周岁请在监护人陪同下阅读并同意。',
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 20),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Checkbox(
                        value: _agreed,
                        onChanged: (value) => setState(() => _agreed = value ?? false),
                      ),
                      Expanded(
                        child: Wrap(
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            const Text('我已阅读并同意'),
                            TextButton(
                              onPressed: () => _openDocument('terms'),
                              child: const Text('《用户协议》'),
                            ),
                            const Text('和'),
                            TextButton(
                              onPressed: () => _openDocument('privacy'),
                              child: const Text('《隐私政策》'),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _agreed ? _accept : null,
                child: const Text('同意并进入'),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () => SystemNavigator.pop(),
                child: const Text('不同意并退出'),
              ),
              const SizedBox(height: 12),
              Text(
                '版本 $kLegalPrivacyVersion · 不同意将退出应用且不采集任何信息',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
