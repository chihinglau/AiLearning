import 'package:ai_learning/features/learn/learn_page.dart';
import 'package:ai_learning/features/mistakes/mistakes_page.dart';
import 'package:ai_learning/features/profile/profile_page.dart';
import 'package:flutter/material.dart';

/// M2 主框架：学习 / 错题本 / 我的 三 Tab。
class AppShell extends StatefulWidget {
  const AppShell({super.key, this.initialTab = 0});

  /// 0 学习、1 错题本、2 我的。
  final int initialTab;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  late int _index = widget.initialTab;

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
