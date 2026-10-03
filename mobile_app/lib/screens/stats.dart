import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/ui.dart';

class StatsScreen extends StatefulWidget {
  const StatsScreen({super.key});
  @override
  State<StatsScreen> createState() => _StatsScreenState();
}

class _StatsScreenState extends State<StatsScreen> {
  Map _s = {};
  List _daily = [];
  List _weekly = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final s = await Api.get('/stats/summary') as Map;
      final d = await Api.get('/stats/daily', {'days': '14'}) as List;
      final w = await Api.get('/stats/weekly', {'weeks': '4'}) as List;
      if (mounted) {
        setState(() {
          _s = s;
          _daily = d;
          _weekly = w;
          _loading = false;
        });
      }
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        toast(context, e.detail);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    final mx = _daily.fold<int>(
        1, (m, e) => ((e as Map)['sleeping'] as int) > m ? (e['sleeping'] as int) : m);
    return ListView(padding: const EdgeInsets.all(12), children: [
      GridView.count(
        crossAxisCount: 2,
        shrinkWrap: true,
        mainAxisSpacing: 8,
        crossAxisSpacing: 8,
        childAspectRatio: 2.4,
        physics: const NeverScrollableScrollPhysics(),
        children: [
          StatCard('${_s['sleeping_alerts'] ?? 0}', 'Vật gian lận'),
          StatCard(
              '${(((_s['avg_focus_rate'] ?? 0) as num) * 100).toStringAsFixed(0)}%',
              'Tỉ lệ sạch'),
          StatCard('${_s['total_records'] ?? 0}', 'Lượt snapshot'),
          StatCard('${_s['total_students'] ?? 0}', 'Vật phát hiện'),
        ],
      ),
      const SizedBox(height: 12),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('14 ngày gần nhất',
                    style:
                        TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                if (_daily.isEmpty) const Text('Chưa có dữ liệu.'),
                for (final e in _daily)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                              '${(e as Map)['date'].toString().substring(5)} · ${e['sleeping']} gian lận / ${e['total']}',
                              style: const TextStyle(fontSize: 13)),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: (e['sleeping'] as int) / mx,
                              minHeight: 8,
                              backgroundColor: Colors.grey.shade800,
                              valueColor: AlwaysStoppedAnimation(
                                  (e['sleeping'] as int) > 0
                                      ? Theme.of(context).colorScheme.error
                                      : Colors.green),
                            ),
                          ),
                        ]),
                  ),
              ]),
        ),
      ),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('4 tuần gần nhất',
                    style:
                        TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                if (_weekly.isEmpty) const Text('Chưa có dữ liệu.'),
                for (final e in _weekly)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                              '${(e as Map)['week']} · sạch ${(((e['focus_rate'] ?? 0) as num) * 100).toStringAsFixed(0)}%',
                              style: const TextStyle(fontSize: 13)),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value:
                                  ((e['focus_rate'] ?? 0) as num).toDouble(),
                              minHeight: 8,
                              backgroundColor: Colors.grey.shade800,
                              valueColor: const AlwaysStoppedAnimation(
                                  Colors.green),
                            ),
                          ),
                        ]),
                  ),
              ]),
        ),
      ),
    ]);
  }
}
