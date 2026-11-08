import 'dart:async';

import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/features/learn/learn_page.dart';
import 'package:ai_learning/features/mistakes/mistakes_page.dart';
import 'package:ai_learning/features/profile/profile_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// M2 主框架：学习 / 错题本 / 我的 三 Tab。
class AppShell extends ConsumerStatefulWidget {
  const AppShell({super.key, this.initialTab = 0});

  /// 0 学习、1 错题本、2 我的。
  final int initialTab;

  @override
  ConsumerState<AppShell> createState() => _AppShellState();
}

class _AppShellState extends ConsumerState<AppShell>
    with WidgetsBindingObserver {
  late int _index = widget.initialTab;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // 回到前台时尝试同步离线答题队列。
    if (state == AppLifecycleState.resumed) {
      unawaited(ref.read(offlineLearnSyncProvider).sync());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: const [
          LearnPage(),
          MistakesPage(),
          ProfilePage(),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (value) => setState(() => _index = value),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.menu_book_outlined),
            selectedIcon: Icon(Icons.menu_book),
            label: '学习',
          ),
          NavigationDestination(
            icon: Icon(Icons.fact_check_outlined),
            selectedIcon: Icon(Icons.fact_check),
            label: '错题本',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: '我的',
          ),
        ],
      ),
    );
  }
}
