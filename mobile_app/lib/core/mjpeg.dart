/// Hiển thị luồng MJPEG (/camera/video_feed) bằng HttpClient có sẵn.
library;

import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';

int _indexOf(List<int> buf, int a, int b, [int from = 0]) {
  for (var i = from; i + 1 < buf.length; i++) {
    if (buf[i] == a && buf[i + 1] == b) return i;
  }
  return -1;
}

class MjpegView extends StatefulWidget {
  final String url;
  const MjpegView(this.url, {super.key});
  @override
  State<MjpegView> createState() => _MjpegViewState();
}

class _MjpegViewState extends State<MjpegView> {
  final _ctrl = StreamController<Uint8List>.broadcast();
  HttpClient? _client;
  bool _run = true;

  @override
  void initState() {
    super.initState();
    _pump();
  }

  Future<void> _pump() async {
    _client = HttpClient();
    try {
      final req = await _client!.getUrl(Uri.parse(widget.url));
      final res = await req.close();
      final buf = <int>[];
      await for (final chunk in res) {
        if (!_run) break;
        buf.addAll(chunk);
        for (;;) {
          final s = _indexOf(buf, 0xFF, 0xD8);
          if (s < 0) {
            if (buf.length > 4) {
              buf.removeRange(0, buf.length - 4);
            }
            break;
          }
          final e = _indexOf(buf, 0xFF, 0xD9, s + 2);
          if (e < 0) {
            if (s > 0) buf.removeRange(0, s);
            break;
          }
          if (_run) _ctrl.add(Uint8List.fromList(buf.sublist(s, e + 2)));
          buf.removeRange(0, e + 2);
        }
      }
    } catch (_) {
      // Mất luồng khi dừng camera hoặc rớt mạng: im lặng, StreamBuilder giữ frame cũ.
    }
  }

  @override
  void didUpdateWidget(MjpegView old) {
    super.didUpdateWidget(old);
    if (old.url != widget.url) _pump();
  }

  @override
  void dispose() {
    _run = false;
    _client?.close(force: true);
    _ctrl.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<Uint8List>(
      stream: _ctrl.stream,
      builder: (_, snap) => snap.hasData
          ? Image.memory(snap.data!, gaplessPlayback: true, fit: BoxFit.contain)
          : Container(
              height: 220,
              alignment: Alignment.center,
              color: Colors.black,
              child: const Text('Chưa có luồng — nhấn Bắt đầu')),
    );
  }
}
