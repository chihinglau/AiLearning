import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  List<Textbook> _textbooks = const [];
  List<Chapter> _chapters = const [];
  Textbook? _selectedTextbook;
  bool _loadingTextbooks = true;
  bool _loadingChapters = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadTextbooks();
  }

  Future<void> _loadTextbooks() async {
    setState(() {
      _loadingTextbooks = true;
      _error = null;
    });
    try {
      final grade = ref.read(currentUserProvider)?.grade;
      final textbooks = await ref.read(contentServiceProvider).textbooks(grade: grade);
      if (!mounted) return;
      setState(() {
        _textbooks = textbooks;
        _loadingTextbooks = false;
      });
      if (textbooks.isNotEmpty) {
        await _loadChapters(textbooks.first);
      }
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loadingTextbooks = false;
      });
    }
  }

  Future<void> _loadChapters(Textbook textbook) async {
    setState(() {
      _selectedTextbook = textbook;
      _chapters = const [];
      _loadingChapters = true;
      _error = null;
    });
    try {
      final chapters = await ref.read(contentServiceProvider).chapters(textbook.id);
      if (!mounted) return;
      setState(() {
        _chapters = chapters;
        _loadingChapters = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loadingChapters = false;
      });
    }
  }

  Future<void> _logout() async {
    await ref.read(authServiceProvider).logout();
    ref.read(currentUserProvider.notifier).state = null;
    if (!mounted) return;
    context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('深爱学'),
        actions: [
          IconButton(
            onPressed: _logout,
            icon: const Icon(Icons.logout),
            tooltip: '退出登录',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadTextbooks,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _WelcomeCard(nickname: user?.nickname ?? '', grade: user?.grade),
            const SizedBox(height: 20),
            Text('我的教材', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            if (_loadingTextbooks)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(child: CircularProgressIndicator()),
              )
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _textbooks
                    .map(
                      (textbook) => ChoiceChip(
                        label: Text(
                          '${textbook.subjectLabel} ${textbook.grade}年级 · ${textbook.version}',
                        ),
                        selected: _selectedTextbook?.id == textbook.id,
                        onSelected: (_) => _loadChapters(textbook),
                      ),
                    )
                    .toList(),
              ),
            const SizedBox(height: 20),
            Text('同步练习章节', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            if (_loadingChapters)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_chapters.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(child: Text('暂无章节内容')),
              )
            else
              ..._chapters.map(
                (chapter) => Card(
                  child: ListTile(
                    leading: const Icon(Icons.menu_book_outlined),
                    title: Text(chapter.name),
                    subtitle: chapter.summary == null ? null : Text(chapter.summary!),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.go(
                      '/practice/${chapter.id}?name=${Uri.encodeComponent(chapter.name)}',
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _WelcomeCard extends StatelessWidget {
  const _WelcomeCard({required this.nickname, required this.grade});

  final String nickname;
  final int? grade;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      color: theme.colorScheme.primaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: theme.colorScheme.primary,
              child: const Icon(Icons.person, color: Colors.white),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    nickname.isEmpty ? '同学你好' : '你好，$nickname',
                    style: theme.textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    grade == null ? '深圳本地化教材已就绪' : '$grade 年级 · 深圳本地化教材',
                    style: theme.textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
