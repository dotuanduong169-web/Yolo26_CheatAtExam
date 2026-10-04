import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/ui.dart';
import 'auth.dart';

class MoreScreen extends StatefulWidget {
  const MoreScreen({super.key});
  @override
  State<MoreScreen> createState() => _MoreScreenState();
}

class _MoreScreenState extends State<MoreScreen> {
  List _devs = [];
  Map? _me;
  List _users = [];
  final _nn = TextEditingController();
  final _nr = TextEditingController();
  final _nl = TextEditingController();
  final _meName = TextEditingController();
  final _pwOld = TextEditingController();
  final _pwNew = TextEditingController();
  final _host = TextEditingController();
  bool _isAdmin = false;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final devs = await Api.get('/devices') as List;
      final me = await Api.get('/users/profile') as Map;
      final role = await Session.role();
      final admin = (role ?? me['VaiTro']) == 'admin';
      List users = [];
      if (admin) {
        users = await Api.get('/users/list', {'limit': '20'}) as List;
      }
      if (!mounted) return;
      setState(() {
        _loading = false;
        _devs = devs;
        _me = me;
        _isAdmin = admin;
        _users = users;
        _meName.text = (me['HoVaTen'] ?? '') as String;
      });
      _host.text = await Session.baseUrl();
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        toast(context, e.detail);
      }
    }
  }

  Future<void> _devCreate() async {
    try {
      await Api.post('/devices', {
        'TenThietBi': _nn.text.trim(),
        'DuongDanRTSP': _nr.text.trim(),
        if (_nl.text.trim().isNotEmpty) 'MoTaViTri': _nl.text.trim(),
      });
      _nn.clear();
      _nr.clear();
      _nl.clear();
      _load();
    } on ApiException catch (e) {
      toast(context, e.detail);
    }
  }

  Future<void> _devDel(int id) async {
    if (!await confirm(context, 'Xóa thiết bị #$id?')) return;
    try {
      await Api.delete('/devices/$id');
      _load();
    } on ApiException catch (e) {
      toast(context, e.detail);
    }
  }

  Future<void> _devTest(int id) async {
    try {
      final d = await Api.post('/devices/$id/test') as Map;
      if (!mounted) return;
      toast(context, d['online'] == true
          ? 'Online · ${d['latency_ms']}ms'
          : 'Offline: ${d['message']}');
    } on ApiException catch (e) {
      toast(context, e.detail);
    }
  }

  Future<void> _userCreate() async {
    final u = TextEditingController();
    final n = TextEditingController();
    final p = TextEditingController();
    String role = 'teacher';
    final ok = await showDialog<bool>(
        context: context,
        builder: (_) => StatefulBuilder(
            builder: (ctx, setDlg) => AlertDialog(
              title: const Text('Tạo tài khoản'),
              content: Column(mainAxisSize: MainAxisSize.min, children: [
                TextField(controller: u,
                    decoration: const InputDecoration(labelText: 'Tên đăng nhập')),
                TextField(controller: n,
                    decoration: const InputDecoration(labelText: 'Họ tên')),
                TextField(controller: p, obscureText: true,
                    decoration: const InputDecoration(labelText: 'Mật khẩu')),
                DropdownButtonFormField<String>(
                    initialValue: role,
                    items: const [
                      DropdownMenuItem(value: 'teacher', child: Text('teacher')),
                      DropdownMenuItem(value: 'admin', child: Text('admin')),
                    ],
                    onChanged: (v) => setDlg(() => role = v ?? 'teacher')),
              ]),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: const Text('Hủy')),
                TextButton(
                    onPressed: () => Navigator.pop(context, true),
                    child: const Text('Tạo')),
              ],
            )));
    if (ok != true) return;
    try {
      await Api.post('/users/create', {
        'TenDangNhap': u.text.trim(),
        'HoVaTen': n.text.trim(),
        'MatKhau': p.text,
        'VaiTro': role
      });
      _load();
    } on ApiException catch (e) {
      if (mounted) toast(context, e.detail);
    }
  }

  Future<void> _userToggleRole(Map u) async {
    final nr = u['VaiTro'] == 'admin' ? 'teacher' : 'admin';
    try {
      await Api.put('/users/${u['PK_MaNguoiDung']}', {'VaiTro': nr});
      _load();
    } on ApiException catch (e) {
      if (mounted) toast(context, e.detail);
    }
  }

  Future<void> _userToggleLock(Map u) async {
    final ns = u['TrangThai'] == 'hoat_dong' ? 'khoa' : 'hoat_dong';
    try {
      await Api.put('/users/${u['PK_MaNguoiDung']}', {'TrangThai': ns});
      _load();
    } on ApiException catch (e) {
      if (mounted) toast(context, e.detail);
    }
  }

  Future<void> _meSave() async {
    try {
      await Api.put('/users/update', {'HoVaTen': _meName.text.trim()});
      if (mounted) toast(context, 'Đã lưu');
    } on ApiException catch (e) {
      if (mounted) toast(context, e.detail);
    }
  }

  Future<void> _pwChange() async {
    try {
      await Api.put('/users/change-password',
          {'MatKhauCu': _pwOld.text, 'MatKhauMoi': _pwNew.text});
      if (!mounted) return;
      toast(context, 'Đổi xong');
      _pwOld.clear();
      _pwNew.clear();
    } on ApiException catch (e) {
      if (mounted) toast(context, e.detail);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    return ListView(padding: const EdgeInsets.all(12), children: [
      _section('Thiết bị biên', [
        if (_devs.isEmpty) const Text('Chưa có thiết bị.'),
        for (final d in _devs)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${(d as Map)['TenThietBi']}',
                        style: const TextStyle(fontWeight: FontWeight.bold)),
                    Text('${d['DuongDanRTSP']} · ${d['TrangThai'] ?? ''}',
                        style: const TextStyle(fontSize: 13)),
                    const SizedBox(height: 8),
                    Row(children: [
                      Expanded(
                          child: OutlinedButton(
                              onPressed: () => _devTest(
                                  d['PK_MaThietBi'] as int),
                              child: const Text('Kiểm tra'))),
                      const SizedBox(width: 8),
                      Expanded(
                          child: OutlinedButton(
                              onPressed: () =>
                                  _devDel(d['PK_MaThietBi'] as int),
                              child: const Text('Xóa'))),
                    ]),
                  ]),
            ),
          ),
        TextField(controller: _nn,
            decoration: const InputDecoration(labelText: 'Tên (Cam P101)')),
        TextField(controller: _nr,
            decoration: const InputDecoration(
                labelText: 'Nguồn (0 / rtsp://… / http://…/video)')),
        TextField(controller: _nl,
            decoration:
                const InputDecoration(labelText: 'Vị trí (tùy chọn)')),
        const SizedBox(height: 8),
        OutlinedButton(onPressed: _devCreate, child: const Text('Thêm')),
      ]),
      if (_isAdmin)
        _section('Người dùng (admin)', [
          for (final u in _users)
            Card(
              child: ListTile(
                title: Text('${(u as Map)['TenDangNhap']}'),
                subtitle: Text(
                    '${u['HoVaTen'] ?? ''} · ${u['VaiTro']} · ${u['TrangThai'] ?? ''}'),
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  IconButton(
                      icon: const Icon(Icons.swap_horiz),
                      onPressed: () => _userToggleRole(u)),
                  IconButton(
                      icon: const Icon(Icons.lock_outline),
                      onPressed: () => _userToggleLock(u)),
                ]),
              ),
            ),
          OutlinedButton(
              onPressed: _userCreate, child: const Text('Tạo tài khoản')),
        ]),
      _section('Tôi', [
        Text('${_me?['HoVaTen'] ?? ''} · ${_me?['VaiTro'] ?? ''}',
            style: const TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        TextField(controller: _meName,
            decoration: const InputDecoration(labelText: 'Họ tên mới')),
        OutlinedButton(onPressed: _meSave, child: const Text('Lưu họ tên')),
        TextField(controller: _pwOld, obscureText: true,
            decoration: const InputDecoration(labelText: 'Mật khẩu cũ')),
        TextField(controller: _pwNew, obscureText: true,
            decoration: const InputDecoration(labelText: 'Mật khẩu mới')),
        OutlinedButton(onPressed: _pwChange, child: const Text('Đổi mật khẩu')),
        TextField(controller: _host,
            decoration: const InputDecoration(labelText: 'Máy chủ')),
        OutlinedButton(
            onPressed: () async {
              await Session.setBaseUrl(_host.text.trim());
              if (context.mounted) toast(context, 'Đã lưu máy chủ');
            },
            child: const Text('Lưu máy chủ')),
        const SizedBox(height: 8),
        FilledButton(
          style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error),
          onPressed: () async {
            try {
              await Api.post('/users/logout');
            } catch (_) {}
            await Session.clear();
            if (!context.mounted) return;
            Navigator.pushReplacement(context,
                MaterialPageRoute(builder: (_) => const AuthScreen()));
          },
          child: const Text('Đăng xuất'),
        ),
      ]),
    ]);
  }

  Widget _section(String title, List<Widget> children) => Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: const TextStyle(
                        fontSize: 15, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                ...children,
              ]),
        ),
      );
}
