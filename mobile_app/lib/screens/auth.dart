import 'package:flutter/material.dart';

import '../core/api.dart';
import '../core/ui.dart';
import 'home.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _host = TextEditingController();
  final _u = TextEditingController(text: 'admin');
  final _p = TextEditingController();
  final _ru = TextEditingController();
  final _rn = TextEditingController();
  final _rp = TextEditingController();
  bool _reg = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    Session.baseUrl().then((v) => _host.text = v);
  }

  Future<void> _login() async {
    final host = _host.text.trim();
    if (host.isEmpty) return toast(context, 'Nhập máy chủ, VD http://192.168.1.10:8000');
    setState(() => _busy = true);
    try {
      await Session.setBaseUrl(host);
      final d = await Api.post('/users/login',
          {'TenDangNhap': _u.text.trim(), 'MatKhau': _p.text}) as Map;
      await Session.save(d['access_token'] as String, (d['role'] ?? '') as String);
      if (!mounted) return;
      Navigator.pushReplacement(
          context, MaterialPageRoute(builder: (_) => const HomeScreen()));
    } on ApiException catch (e) {
      toast(context, e.detail);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _register() async {
    try {
      await Session.setBaseUrl(_host.text.trim());
      await Api.post('/users/register', {
        'TenDangNhap': _ru.text.trim(),
        'HoVaTen': _rn.text.trim(),
        'MatKhau': _rp.text
      });
      if (!mounted) return;
      toast(context, 'Tạo xong, đăng nhập đi');
      setState(() => _reg = false);
    } on ApiException catch (e) {
      toast(context, e.detail);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(children: [
            const Text('ExamCheat AI',
                style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text('Giám sát gian lận phòng thi'),
            const SizedBox(height: 24),
            TextField(
                controller: _host,
                decoration: const InputDecoration(
                    labelText: 'Máy chủ',
                    hintText: 'http://192.168.1.10:8000',
                    border: OutlineInputBorder()),
                keyboardType: TextInputType.url),
            const SizedBox(height: 12),
            if (!_reg) ...[
              TextField(
                  controller: _u,
                  decoration: const InputDecoration(
                      labelText: 'Tên đăng nhập', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(
                  controller: _p,
                  obscureText: true,
                  decoration: const InputDecoration(
                      labelText: 'Mật khẩu', border: OutlineInputBorder())),
              const SizedBox(height: 16),
              FilledButton(
                  onPressed: _busy ? null : _login,
                  child: Text(_busy ? 'Đang vào…' : 'Đăng nhập')),
              TextButton(
                  onPressed: () => setState(() => _reg = true),
                  child: const Text('Chưa có tài khoản? Đăng ký')),
            ] else ...[
              TextField(
                  controller: _ru,
                  decoration: const InputDecoration(
                      labelText: 'Tên đăng nhập mới',
                      border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(
                  controller: _rn,
                  decoration: const InputDecoration(
                      labelText: 'Họ và tên', border: OutlineInputBorder())),
              const SizedBox(height: 12),
              TextField(
                  controller: _rp,
                  obscureText: true,
                  decoration: const InputDecoration(
                      labelText: 'Mật khẩu', border: OutlineInputBorder())),
              const SizedBox(height: 16),
              FilledButton(
                  onPressed: _register, child: const Text('Tạo tài khoản')),
              TextButton(
                  onPressed: () => setState(() => _reg = false),
                  child: const Text('Về đăng nhập')),
            ],
          ]),
        ),
      ),
    );
  }
}
