import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/ui.dart';

const _filters = {'': 'Tất cả', 'cho_kiem_tra': 'Chờ duyệt', 'dung': 'Đúng', 'sai': 'Sai'};

class EventsScreen extends StatefulWidget {
  const EventsScreen({super.key});
  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  final _sid = TextEditingController();
  String _f = '';
  List _list = [];
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _preset();
  }

  Future<void> _preset() async {
    try {
      final no = await Api.get('/events/system/notifications') as Map;
      final a = no['active_session'] as Map?;
      if (a != null && mounted) {
        setState(() => _sid.text = (a['session_id'] ?? '').toString());
        _load();
      }
    } catch (_) {}
  }

  Future<void> _load() async {
    if (_sid.text.trim().isEmpty) {
      setState(() => _list = []);
      return toast(context, 'Nhập ID phiên');
    }
    setState(() => _loading = true);
    try {
      final q = _f.isEmpty ? '' : '&trang_thai=$_f';
      final l = await Api.get('/events/session/${_sid.text.trim()}?limit=20$q') as List;
      if (mounted) setState(() => _list = l);
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
        child: Row(children: [
          Expanded(
              child: TextField(
                  controller: _sid,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                      labelText: 'ID phiên', border: OutlineInputBorder()),
                  onSubmitted: (_) => _load())),
          const SizedBox(width: 8),
          FilledButton.tonal(onPressed: _load, child: const Text('Tải')),
        ]),
      ),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: Row(
            children: _filters.entries
                .map((e) => Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                          label: Text(e.value),
                          selected: _f == e.key,
                          onSelected: (_) {
                            setState(() => _f = e.key);
                            _load();
                          }),
                    ))
                .toList()),
      ),
      Expanded(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _list.isEmpty
                ? const EmptyView('Chưa có sự kiện.')
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: _list.length,
                    itemBuilder: (_, i) {
                      final e = _list[i] as Map;
                      return Card(
                        child: ListTile(
                          title: Text(
                              '${label(e['LoaiHanhVi'] as String?)} ${((e['DoTinCay'] ?? 0) * 100).toStringAsFixed(0)}%'),
                          subtitle: Text(
                              '#${e['PK_MaSuKien']} · ${dt(e['ThoiGianPhatHien'])}'),
                          trailing: StatusTag(e['TrangThaiKiemTra'] as String?),
                          onTap: () => Navigator.push(
                              context,
                              MaterialPageRoute(
                                  builder: (_) => EventDetailScreen(
                                      id: e['PK_MaSuKien'] as int,
                                      onDone: _load))),
                        ),
                      );
                    },
                  ),
      ),
    ]);
  }
}

class EventDetailScreen extends StatefulWidget {
  final int id;
  final VoidCallback onDone;
  const EventDetailScreen({required this.id, required this.onDone, super.key});
  @override
  State<EventDetailScreen> createState() => _EventDetailScreenState();
}

class _EventDetailScreenState extends State<EventDetailScreen> {
  Map? _e;
  final _imgs = <Uint8List>[];
  String? _fix;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final e = await Api.get('/events/${widget.id}') as Map;
      if (!mounted) return;
      setState(() {
        _e = e;
        _fix = e['NhanNguoiDung'] as String?;
      });
      for (final ev in (e['evidences'] ?? []) as List) {
        try {
          final b = await Api.bytes(
              '/events/evidences/${ev['PK_MaBangChung']}/file');
          if (mounted) setState(() => _imgs.add(Uint8List.fromList(b)));
        } catch (_) {}
      }
    } on ApiException catch (e) {
      toast(context, e.detail);
    }
  }

  Future<void> _verify(String v) async {
    try {
      await Api.patch('/events/${widget.id}',
          {'TrangThaiKiemTra': v, 'NhanNguoiDung': _fix});
      widget.onDone();
      if (!mounted) return;
      toast(context, 'Đã ghi');
      Navigator.pop(context);
    } on ApiException catch (e) {
      toast(context, e.detail);
    }
  }

  @override
  Widget build(BuildContext context) {
    final e = _e;
    return Scaffold(
      appBar: AppBar(title: Text('Sự kiện #${widget.id}')),
      body: e == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(12), children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Expanded(
                              child: Text(
                                  label(e['LoaiHanhVi'] as String?),
                                  style: const TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold))),
                          StatusTag(e['TrangThaiKiemTra'] as String?),
                        ]),
                        const SizedBox(height: 4),
                        Text(
                            'AI: ${label(e['NhanAI'] as String?)} · ${((e['DoTinCay'] ?? 0) * 100).toStringAsFixed(1)}%'),
                        Text(
                            '${dt(e['ThoiGianPhatHien'])} · Phiên #${e['FK_MaPhienGiamSat']}'),
                      ]),
                ),
              ),
              for (final img in _imgs)
                Card(
                    clipBehavior: Clip.antiAlias,
                    child: Image.memory(img)),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(children: [
                    DropdownButtonFormField<String>(
                      initialValue: _fix,
                      items: [
                        const DropdownMenuItem(
                            value: null, child: Text('Nhãn sửa (tùy chọn)')),
                        ...labelVi.keys.map((k) => DropdownMenuItem(
                            value: k, child: Text('$k — ${labelVi[k]}'))),
                      ],
                      onChanged: (v) => setState(() => _fix = v),
                      decoration: const InputDecoration(
                          border: OutlineInputBorder()),
                    ),
                    const SizedBox(height: 8),
                    Row(children: [
                      Expanded(
                          child: FilledButton(
                              onPressed: () => _verify('dung'),
                              child: const Text('Đúng'))),
                      const SizedBox(width: 8),
                      Expanded(
                          child: OutlinedButton(
                              onPressed: () => _verify('sai'),
                              child: const Text('Sai'))),
                    ]),
                  ]),
                ),
              ),
            ]),
    );
  }
}
