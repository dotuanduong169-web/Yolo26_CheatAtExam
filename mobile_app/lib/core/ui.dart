/// Nhãn tiếng Việt + widget dùng chung.
library;

import 'package:flutter/material.dart';

const labelVi = {
  'Cheat_Paper': 'Phao thi',
  'cellphone': 'Điện thoại',
  'quay_dau': 'Quay đầu',
  'quay_sau': 'Quay sau',
  'cui_xuong': 'Cúi xuống',
  'Answer_paper': 'Bài sạch',
  'Head_Turn': 'Quay đầu',
};

String label(String? v) => labelVi[v] ?? (v ?? '—');
String dt(dynamic v) =>
    v == null ? '' : v.toString().substring(0, 19).replaceAll('T', ' ');

class StatusTag extends StatelessWidget {
  final String? s;
  const StatusTag(this.s, {super.key});
  @override
  Widget build(BuildContext context) {
    final c = Theme.of(context).colorScheme;
    final Color fg;
    final String t;
    if (s == 'dung') {
      fg = Colors.green;
      t = 'Đúng';
    } else if (s == 'sai') {
      fg = c.error;
      t = 'Sai';
    } else {
      fg = Colors.amber;
      t = 'Chờ duyệt';
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
          border: Border.all(color: fg), borderRadius: BorderRadius.circular(20)),
      child: Text(t, style: TextStyle(color: fg, fontSize: 12)),
    );
  }
}

class StatCard extends StatelessWidget {
  final String value;
  final String title;
  const StatCard(this.value, this.title, {super.key});
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(value,
              style:
                  const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
          const SizedBox(height: 2),
          Text(title, style: Theme.of(context).textTheme.bodySmall),
        ]),
      ),
    );
  }
}

class EmptyView extends StatelessWidget {
  final String text;
  const EmptyView(this.text, {super.key});
  @override
  Widget build(BuildContext context) =>
      Center(child: Padding(padding: const EdgeInsets.all(32), child: Text(text)));
}

Future<void> toast(BuildContext context, String m) async {
  if (!context.mounted) return;
  ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(m), duration: const Duration(seconds: 2)));
}

Future<bool> confirm(BuildContext context, String m) async =>
    (await showDialog<bool>(
        context: context,
        builder: (_) => AlertDialog(
                content: Text(m),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(context, false),
                      child: const Text('Hủy')),
                  TextButton(
                      onPressed: () => Navigator.pop(context, true),
                      child: const Text('Xóa')),
                ]))) ??
    false;
