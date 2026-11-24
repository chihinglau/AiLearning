import 'package:ai_learning/core/constants/app_constants.dart';
import 'package:ai_learning/core/models/textbook_binding.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// 注册页：用户名必填，手机号可选；年级为后端必填项，注册成功即自动登录。
class RegisterPage extends ConsumerStatefulWidget {
  const RegisterPage({super.key});

  @override
  ConsumerState<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends ConsumerState<RegisterPage> {
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _nicknameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _confirmController = TextEditingController();
  Stage _stage = Stage.junior;
  int _grade = 7;
  bool _obscure = true;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _usernameController.dispose();
    _phoneController.dispose();
    _nicknameController.dispose();
    _passwordController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  String? _validate() {
    final username = _usernameController.text.trim();
    final phone = _phoneController.text.trim();
    if (username.isEmpty) return '请填写用户名';
    if (!RegExp(r'^[A-Za-z0-9_\-.一-龥]{2,50}$').hasMatch(username)) {
      return '用户名为 2-50 位字母/数字/下划线/中划线/点/中文';
    }
    if (phone.isNotEmpty && !RegExp(r'^1[3-9]\d{9}$').hasMatch(phone)) {
      return '手机号格式不正确（可留空）';
    }
    if (_passwordController.text.length < 6) return '密码至少 6 位';
    if (_passwordController.text != _confirmController.text) {
      return '两次输入的密码不一致';
    }
    return null;
  }

  Future<void> _submit() async {
    final error = _validate();
    if (error != null) {
      setState(() => _error = error);
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final user = await ref.read(authServiceProvider).register(
            username: _usernameController.text.trim(),
            phone: _phoneController.text.trim(),
            password: _passwordController.text,
            nickname: _nicknameController.text,
            grade: _grade,
            stage: _stage.code,
          );
      ref.read(currentUserProvider.notifier).state = user;
      if (!mounted) return;
      context.go(user.needsReconsent ? '/consent' : '/gate');
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('注册账号')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                controller: _usernameController,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: '用户名（必填）',
                  hintText: '登录时使用，如 xiaoming2026',
                  prefixIcon: Icon(Icons.person_outline),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: '手机号（可选）',
                  hintText: '留空也能注册，用于找回账号',
                  prefixIcon: Icon(Icons.phone_iphone),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _nicknameController,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: '昵称（可选）',
                  hintText: '首页问候显示，默认与用户名一致',
                  prefixIcon: Icon(Icons.badge_outlined),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    flex: 2,
                    child: DropdownButtonFormField<Stage>(
                      initialValue: _stage,
                      decoration: const InputDecoration(
                        labelText: '学段',
                        border: OutlineInputBorder(),
                      ),
                      items: Stage.values
                          .map((stage) => DropdownMenuItem(
                                value: stage,
                                child: Text(stage.label),
                              ))
                          .toList(),
                      onChanged: (stage) {
                        if (stage == null) return;
                        setState(() {
                          _stage = stage;
                          final grades = gradesForStage(stage);
                          if (!grades.contains(_grade)) _grade = grades.first;
                        });
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 3,
                    child: DropdownButtonFormField<int>(
                      initialValue: _grade,
                      decoration: const InputDecoration(
                        labelText: '年级',
                        border: OutlineInputBorder(),
                      ),
                      items: gradesForStage(_stage)
                          .map((grade) => DropdownMenuItem(
                                value: grade,
                                child: Text('$grade 年级'),
                              ))
                          .toList(),
                      onChanged: (grade) {
                        if (grade != null) setState(() => _grade = grade);
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _passwordController,
                obscureText: _obscure,
                textInputAction: TextInputAction.next,
                decoration: InputDecoration(
                  labelText: '密码（至少 6 位）',
                  prefixIcon: const Icon(Icons.lock_outline),
                  suffixIcon: IconButton(
                    icon: Icon(_obscure
                        ? Icons.visibility_outlined
                        : Icons.visibility_off_outlined),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                  border: const OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _confirmController,
                obscureText: _obscure,
                onSubmitted: (_) => _submit(),
                decoration: const InputDecoration(
                  labelText: '确认密码',
                  prefixIcon: Icon(Icons.lock_reset_outlined),
                  border: OutlineInputBorder(),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
              ],
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _loading ? null : _submit,
                child: _loading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('注册并登录'),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: _loading ? null : () => context.pop(),
                child: const Text('已有账号？返回登录'),
              ),
              const SizedBox(height: 8),
              Text(
                '注册后需完成学段/年级与教材确认，才能生成练习与试卷。',
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
