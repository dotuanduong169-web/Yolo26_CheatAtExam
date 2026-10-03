import 'package:flutter/material.dart';

import 'core/api.dart';
import 'screens/auth.dart';
import 'screens/home.dart';

void main() => runApp(const ExamCheatApp());

class ExamCheatApp extends StatelessWidget {
  const ExamCheatApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ExamCheat AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF10B981),
            brightness: Brightness.dark),
        useMaterial3: true,
      ),
      home: FutureBuilder<String?>(
        future: Session.token(),
        builder: (_, s) => s.data != null
            ? const HomeScreen()
            : const AuthScreen(),
      ),
    );
  }
}
