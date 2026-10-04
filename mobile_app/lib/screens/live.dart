import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/mjpeg.dart';
import '../core/ui.dart';

class LiveScreen extends StatefulWidget {
  final VoidCallback onChanged;
  const LiveScreen({required this.onChanged, super.key});
  @override
  State<LiveScreen> createState() => _LiveScreenState();
}

class _LiveScreenState extends State<LiveScreen> {
  List _devs = [];
  String? _devId;
  final _phong = TextEditingController(text: 'P101');
  final _mon = TextEditingController();
  bool _running = false;
  int? _sessionId;
  double? _fps;
  String _streamKey = '';
  List _alerts = [];
  Uint8List? _shot;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final st = await Api.get('/camera/status') as Map;
      final devs = await Api.get('/devices') as List;
      final no = await Api.get('/events/system/notifications') as Map;
      if (!mounted) return;
      setState(() {
        _loading = false;
        _running = st['running'] == true;
        _sessionId = st['session_id'] as int?;
        _fps = (st['fps'] as num?)?.toDouble();
        _devs = devs;
        _devId = devs.isNotEmpty
            ? (devs.first['PK_MaThietBi']).toString()
            : null;
        _alerts = (no['alerts'] ?? []) as List;
        if (_running) _streamKey = DateTime.now().toString();
      });
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        toast(context, e.detail);
      }
    }
  }

  Future<void> _start() async {
    if (_devId == null) return toast(context, 'Chưa có thiết bị');
    try {
      final d = await Api.post(
          '/camera/start?device_id=$_devId&phong_thi=${Uri.encodeComponent(_phong.text.trim().isEmpty ? 'P101' : _phong.text.trim())}&mon_thi=${Uri.encodeComponent(_mon.text.trim())}')
          as Map;
      if (!mounted) return;
      setState(() {
        _running = true;
        _sessionId = d['session_id'] as int?;
        _streamKey = DateTime.now().toString();
      });
      widget.onChanged();
      toast(context, 'Đã bắt đầu phiên #$_sessionId');
    } on ApiException catch (e) {
      toast(context, e.detail);
    }
  }

  Future<void> _stop() async {
    try {
      await Api.post('/camera/stop');
      if (!mounted) return;
      setState(() => _running = false);
      widget.onChanged();
    } on ApiException catch (e) {
      toast(context, e.detail);
    }
  }

  Future<void> _snap() async {
    try {
      final b = await Api.bytes('/camera/snapshot');
      if (!mounted) return;
      setState(() => _shot = Uint8List.fromList(b));
    } on ApiException catch (e) {
      toast(context, e.detail);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    return ListView(padding: const EdgeInsets.all(12), children: [
      Card(
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          ListTile(
              title: Text(_running
                  ? 'Đang chạy — phiên #$_sessionId${_fps != null ? ' · ${_fps!.toStringAsFixed(1)} fps' : ''}'
                  : 'Chưa chạy')),
          if (_running)
            FutureBuilder<String>(
                future: Api.streamUrl(),
                builder: (_, s) => s.hasData
                    ? MjpegView('${s.data}?t=$_streamKey', key: ValueKey(_streamKey))
                    : const SizedBox(height: 220)),
        ]),
      ),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Phiên giám sát',
                    style:
                        TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  initialValue: _devId,
                  items: _devs
                      .map((d) => DropdownMenuItem<String>(
                          value: d['PK_MaThietBi'].toString(),
                          child: Text(
                              '${d['TenThietBi']} (${d['TrangThai']})')))
                      .toList(),
                  onChanged: (v) => setState(() => _devId = v),
                  decoration: const InputDecoration(
                      labelText: 'Thiết bị', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 8),
                Row(children: [
                  Expanded(
                      child: TextField(
                          controller: _phong,
                          decoration: const InputDecoration(
                              labelText: 'Phòng thi',
                              border: OutlineInputBorder()))),
                  const SizedBox(width: 8),
                  Expanded(
                      child: TextField(
                          controller: _mon,
                          decoration: const InputDecoration(
                              labelText: 'Môn thi',
                              border: OutlineInputBorder()))),
                ]),
                const SizedBox(height: 8),
                Row(children: [
                  Expanded(
                      child: FilledButton(
                          onPressed: _start,
                          child: const Text('Bắt đầu'))),
                  const SizedBox(width: 8),
                  Expanded(
                      child: FilledButton(
                          style: FilledButton.styleFrom(
                              backgroundColor:
                                  Theme.of(context).colorScheme.error),
                          onPressed: _stop,
                          child: const Text('Dừng'))),
                ]),
                const SizedBox(height: 4),
                const Text(
                    'Đổi cam trước/sau: bấm nút xoay trên app phát (DroidCam) ở máy quay.',
                    style: TextStyle(fontSize: 12, color: Colors.grey)),
              ]),
        ),
      ),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Ảnh chụp mới nhất (đã vẽ AI)',
                    style:
                        TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                OutlinedButton(
                    onPressed: _snap, child: const Text('Chụp ảnh')),
                if (_shot != null) ...[
                  const SizedBox(height: 8),
                  Image.memory(_shot!),
                ],
              ]),
        ),
      ),
      Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Cảnh báo chờ duyệt',
                    style:
                        TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                if (_alerts.isEmpty)
                  const Text('Không có cảnh báo chờ.'),
                for (final a in _alerts)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                        '${a['behavior_label']} ${a['confidence']}%'),
                    subtitle: Text(
                        'Phiên #${a['session_id']} · ${dt(a['detected_at'])}'),
                    trailing: StatusTag(a['status'] as String?),
                  ),
              ]),
        ),
      ),
    ]);
  }
}
