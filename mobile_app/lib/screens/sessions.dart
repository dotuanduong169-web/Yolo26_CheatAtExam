import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/ui.dart';
import 'events.dart';

class SessionsScreen extends StatefulWidget {
  const SessionsScreen({super.key});
  @override
  State<SessionsScreen> createState() => _SessionsScreenState();
}

class _SessionsScreenState extends State<SessionsScreen> {
  final _q = TextEditingController();
  Map _sum = {};
  final _list = <dynamic>[];
  int _skip = 0;
  bool _loading = false;
  bool _hasMore = true;

  @override
  void initState() {
    super.initState();
    _load(reset: true);
  }

  Future<void> _load({bool reset = false}) async {
    if (_loading) return;
    setState(() => _loading = true);
    try {
      if (reset) {
        _skip = 0;
        _list.clear();
        _hasMore = true;
        _sum = await Api.get('/history/summary') as Map;
      }
      final l = await Api.get('/history/sessions',
          {'skip': '$_skip', 'limit': '10', 'search': _q.text.trim()}) as List;
      if (!mounted) return;
      setState(() {
        _list.addAll(l);
        _skip += l.length;
        _hasMore = l.length == 10;
      });
    } on ApiException catch (e) {
      toast(context, e.detail);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          mainAxisSpacing: 8,
          crossAxisSpacing: 8,
          childAspectRatio: 2.4,
          physics: const NeverScrollableScrollPhysics(),
          children: [
            StatCard('${_sum['tong_phien'] ?? 0}', 'Tổng phiên'),
            StatCard('${_sum['dang_giam_sat'] ?? 0}', 'Đang chạy'),
            StatCard('${_sum['tong_su_kien'] ?? 0}', 'Sự kiện'),
            StatCard('${_sum['cho_kiem_tra'] ?? 0}', 'Chờ duyệt'),
          ],
        ),
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: Row(children: [
          Expanded(
              child: TextField(
                  controller: _q,
                  decoration: const InputDecoration(
                      labelText: 'Tìm phòng/môn',
                      border: OutlineInputBorder()),
                  onSubmitted: (_) => _load(reset: true))),
          const SizedBox(width: 8),
          FilledButton.tonal(
              onPressed: () => _load(reset: true),
              child: const Text('Tìm')),
        ]),
      ),
      Expanded(
        child: _list.isEmpty && !_loading
            ? const EmptyView('Chưa có phiên.')
            : ListView.builder(
                padding: const EdgeInsets.all(12),
                itemCount: _list.length + (_hasMore ? 1 : 0),
                itemBuilder: (_, i) {
                  if (i >= _list.length) {
                    return OutlinedButton(
                        onPressed: _loading ? null : () => _load(),
                        child: Text(
                            _loading ? 'Đang tải…' : 'Tải thêm'));
                  }
                  final s = _list[i] as Map;
                  return Card(
                    child: ListTile(
                      title: Text(
                          '${s['PhongThi'] ?? '—'} · ${s['MonThi'] ?? ''}'),
                      subtitle: Text(
                          '#${s['PK_MaPhienGiamSat']} · ${dt(s['ThoiGianBatDau'])} · ${s['so_su_kien']} sự kiện'),
                      trailing: Text('${s['TrangThai'] ?? ''}',
                          style: const TextStyle(fontSize: 12)),
                      onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => SessionDetailScreen(
                                  id: s['PK_MaPhienGiamSat'] as int,
                                  onDeleted: () => _load(reset: true)))),
                    ),
                  );
                },
              ),
      ),
    ]);
  }
}

class SessionDetailScreen extends StatefulWidget {
  final int id;
  final VoidCallback onDeleted;
  const SessionDetailScreen(
      {required this.id, required this.onDeleted, super.key});
  @override
  State<SessionDetailScreen> createState() => _SessionDetailScreenState();
}

class _SessionDetailScreenState extends State<SessionDetailScreen> {
  Map? _d;

  @override
  void initState() {
    super.initState();
    Api.get('/history/session/${widget.id}').then((v) {
      if (mounted) setState(() => _d = v as Map);
    }).catchError((e) {
      if (e is ApiException) toast(context, e.detail);
    });
  }

  Future<void> _del() async {
    if (!await confirm(context, 'Xóa phiên #${widget.id}?')) return;
    try {
      await Api.delete('/history/session/${widget.id}');
      widget.onDeleted();
      if (!mounted) return;
      Navigator.pop(context);
    } on ApiException catch (e) {
      toast(context, e.detail);
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return Scaffold(
      appBar: AppBar(title: Text('Phiên #${widget.id}')),
      body: d == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(12), children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                      '${(d['session'] as Map)['PhongThi'] ?? ''} · ${(d['session'] as Map)['MonThi'] ?? ''}\n${dt((d['session'] as Map)['ThoiGianBatDau'])} → ${(d['session'] as Map)['ThoiGianKetThuc'] != null ? dt((d['session'] as Map)['ThoiGianKetThuc']) : 'đang chạy'}'),
                ),
              ),
              for (final e in (d['events'] ?? []) as List)
                Card(
                  child: ListTile(
                    title: Text(
                        '${label((e as Map)['LoaiHanhVi'] as String?)} ${(((e)['DoTinCay'] ?? 0) * 100).toStringAsFixed(0)}%'),
                    subtitle:
                        Text(dt(e['ThoiGianPhatHien'])),
                    trailing:
                        StatusTag(e['TrangThaiKiemTra'] as String?),
                    onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                            builder: (_) => EventDetailScreen(
                                id: e['PK_MaSuKien'] as int,
                                onDone: () {}))),
                  ),
                ),
              if (((d['events'] ?? []) as List).isEmpty)
                const EmptyView('Chưa có sự kiện.'),
              FilledButton(
                style: FilledButton.styleFrom(
                    backgroundColor: Theme.of(context).colorScheme.error),
                onPressed: _del,
                child: const Text('Xóa phiên'),
              ),
            ]),
    );
  }
}
