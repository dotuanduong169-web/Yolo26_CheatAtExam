import 'package:flutter/material.dart';

import '../core/api.dart';
import 'auth.dart';
import 'events.dart';
import 'live.dart';
import 'more.dart';
import 'sessions.dart';
import 'stats.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _i = 0;
  int _pending = 0;
  bool _running = false;

  @override
  void initState() {
    super.initState();
    _poll();
  }

  Future<void> _poll() async {
    try {
      final st =
          await Api.get('/camera/status') as Map<String, dynamic>;
      final no = await Api.get('/events/system/notifications')
          as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        _running = st['running'] == true;
        _pending = (no['total_pending'] ?? 0) as int;
      });
    } on ApiException catch (e) {
      if (e.status == 401 && mounted) {
        await Session.clear();
        Navigator.pushReplacement(
            context, MaterialPageRoute(builder: (_) => const AuthScreen()));
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      LiveScreen(onChanged: _poll),
      const EventsScreen(),
      const SessionsScreen(),
      const StatsScreen(),
      const MoreScreen(),
    ];
    return Scaffold(
      appBar: AppBar(
        title: const Text('ExamCheat AI'),
        actions: [
          IconButton(
            icon: Badge(
                label: Text('$_pending'),
                isLabelVisible: _pending > 0,
                child: const Icon(Icons.notifications)),
            onPressed: () => setState(() => _i = 1),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Icon(Icons.circle,
                size: 12, color: _running ? Colors.green : Colors.grey),
          ),
        ],
      ),
      body: RefreshIndicator(
          onRefresh: _poll, child: pages[_i]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _i,
        onDestinationSelected: (v) => setState(() => _i = v),
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.videocam), label: 'Trực tiếp'),
          NavigationDestination(
              icon: Icon(Icons.warning), label: 'Sự kiện'),
          NavigationDestination(
              icon: Icon(Icons.history), label: 'Phiên'),
          NavigationDestination(
              icon: Icon(Icons.bar_chart), label: 'Thống kê'),
          NavigationDestination(icon: Icon(Icons.more_horiz), label: 'Thêm'),
        ],
      ),
    );
  }
}
