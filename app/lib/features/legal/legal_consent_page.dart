import 'package:ai_learning/core/constants/legal_constants.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/features/legal/legal_document_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 登录后重新同意页（R-03）：政策版本升高时强制阅读并重新同意，服务端留痕。
class LegalConsentPage extends ConsumerStatefulWidget {
  const LegalConsentPage({super.key});

  @override
  ConsumerState<LegalConsentPage> createState() => _LegalConsentPageState();
}

class _LegalConsentPageState extends ConsumerState<LegalConsentPage> {
  bool _agreed = false;
  bool _submitting = false;
  String? _error;

  Future<void> _submit() async {
    if (!_agreed || _submitting) return;
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final user = ref.read(currentUserProvider);
      await ref
          .read(legalServiceProvider)
          .accept(
            privacyVersion: kLegalPrivacyVersion,
            termsVersion: kLegalTermsVersion,
            guardianConfirmed: user?.isChild ?? false,
          );
      if (!mounted) return;
      if (user != null) {
        final updated = user.copyWith(needsReconsent: false);
        ref.read(currentUserProvider.notifier).state = updated;
        // 落盘缓存，避免断网启动时用旧状态再次要求同意。
        await ref.read(authServiceProvider).cacheUser(updated);
      }
      if (!mounted) return;
      context.go('/gate');
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = error.message;
      });
    }
  }

  void _openDocument(String docType) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => LegalDocumentPage(docType: docType),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('阅读并同意')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            '隐私政策与用户协议已更新',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '为继续使用深爱学，请阅读并同意最新版本的《用户协议》和《隐私政策》。'
            '如为未满 14 周岁的账号，请由监护人完成确认。',
            style: theme.textTheme.bodyMedium,
          ),
          const SizedBox(height: 20),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.privacy_tip_outlined),
                  title: const Text(kLegalPrivacyTitle),
                  subtitle: const Text('我们收集哪些信息、如何使用与保护'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => _openDocument('privacy'),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.description_outlined),
                  title: const Text(kLegalTermsTitle),
                  subtitle: const Text('服务内容、使用规范与未成年人保护'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => _openDocument('terms'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          CheckboxListTile(
            value: _agreed,
            onChanged: (value) => setState(() => _agreed = value ?? false),
            title: const Text('我已阅读并同意《用户协议》和《隐私政策》'),
            controlAffinity: ListTileControlAffinity.leading,
            contentPadding: EdgeInsets.zero,
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
          ],
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _agreed && !_submitting ? _submit : null,
            child: _submitting
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('同意并继续'),
          ),
        ],
      ),
    );
  }
}
