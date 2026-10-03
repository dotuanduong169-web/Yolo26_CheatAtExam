/// Lớp gọi API BE ExamCheat + lưu phiên (token, quyền, máy chủ).
library;

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiException implements Exception {
  final int status;
  final String detail;
  ApiException(this.status, this.detail);
  @override
  String toString() => 'Lỗi $status: $detail';
}

class Session {
  static const _kToken = 'token';
  static const _kRole = 'role';
  static const _kBase = 'base_url';

  static Future<SharedPreferences> get _prefs => SharedPreferences.getInstance();

  static Future<String> baseUrl() async =>
      (await _prefs).getString(_kBase) ?? '';

  static Future<void> setBaseUrl(String v) async =>
      (await _prefs).setString(_kBase, v);

  static Future<String?> token() async => (await _prefs).getString(_kToken);
  static Future<String?> role() async => (await _prefs).getString(_kRole);

  static Future<void> save(String token, String role) async {
    final p = await _prefs;
    await p.setString(_kToken, token);
    await p.setString(_kRole, role);
  }

  static Future<void> clear() async {
    final p = await _prefs;
    await p.remove(_kToken);
    await p.remove(_kRole);
  }
}

class Api {
  static Future<Map<String, String>> _headers({bool json = true}) async {
    final t = await Session.token();
    return {
      if (json) 'Content-Type': 'application/json',
      if (t != null) 'Authorization': 'Bearer $t',
    };
  }

  static Future<Uri> _uri(String path, [Map<String, String>? query]) async {
    final base = await Session.baseUrl();
    if (base.isEmpty) throw ApiException(0, 'Chưa cấu hình máy chủ');
    return Uri.parse('$base$path').replace(
        queryParameters: {...Uri.parse('$base$path').queryParameters, ...?query});
  }

  static String _detail(String body) {
    try {
      final d = jsonDecode(body);
      if (d is Map && d['detail'] != null) return d['detail'].toString();
    } catch (_) {}
    return body.length > 120 ? body.substring(0, 120) : body;
  }

  static Future<dynamic> _decode(http.Response r) async {
    if (r.statusCode >= 200 && r.statusCode < 300) {
      if (r.body.isEmpty) return {};
      return jsonDecode(r.body);
    }
    throw ApiException(r.statusCode, _detail(r.body));
  }

  static Future<dynamic> get(String path,
      [Map<String, String>? query]) async {
    final r = await http
        .get(await _uri(path, query), headers: await _headers(json: false))
        .timeout(const Duration(seconds: 15));
    return _decode(r);
  }

  static Future<dynamic> post(String path, [Object? body]) async {
    final r = await http
        .post(await _uri(path),
            headers: await _headers(),
            body: body == null ? null : jsonEncode(body))
        .timeout(const Duration(seconds: 15));
    return _decode(r);
  }

  static Future<dynamic> put(String path, Object body) async {
    final r = await http
        .put(await _uri(path),
            headers: await _headers(), body: jsonEncode(body))
        .timeout(const Duration(seconds: 15));
    return _decode(r);
  }

  static Future<dynamic> patch(String path, Object body) async {
    final r = await http
        .patch(await _uri(path),
            headers: await _headers(), body: jsonEncode(body))
        .timeout(const Duration(seconds: 15));
    return _decode(r);
  }

  static Future<dynamic> delete(String path) async {
    final r = await http
        .delete(await _uri(path), headers: await _headers(json: false))
        .timeout(const Duration(seconds: 15));
    return _decode(r);
  }

  /// Tải ảnh (snapshot, bằng chứng) kèm token.
  static Future<List<int>> bytes(String path) async {
    final r = await http
        .get(await _uri(path), headers: await _headers(json: false))
        .timeout(const Duration(seconds: 20));
    if (r.statusCode == 200) return r.bodyBytes;
    throw ApiException(r.statusCode, _detail(r.body));
  }

  static Future<String> streamUrl() async =>
      '${await Session.baseUrl()}/camera/video_feed';
}
