import 'package:ai_learning/core/models/legal.dart';
import 'package:ai_learning/core/models/user.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('LegalDocument 解析后端 JSON', () {
    final doc = LegalDocument.fromJson({
      'doc_type': 'privacy',
      'title': '隐私政策',
      'version': '2026.11.06',
      'updated_at': '2026-11-06',
      'url': 'https://example.com/legal/privacy',
      'content': '# 隐私政策',
    });

    expect(doc.docType, 'privacy');
    expect(doc.version, '2026.11.06');
    expect(doc.updatedAt, '2026-11-06');
    expect(doc.url, endsWith('/legal/privacy'));
    expect(doc.content, contains('隐私政策'));
  });

  test('LegalDocument 缺少可选字段时使用空值', () {
    final doc = LegalDocument.fromJson({
      'doc_type': 'terms',
      'title': '用户协议',
      'version': '1',
      'content': '正文',
    });

    expect(doc.updatedAt, '');
    expect(doc.url, '');
  });

  test('LegalPolicies 解析文档元数据列表', () {
    final policies = LegalPolicies.fromJson({
      'version': '2026.11.06',
      'documents': [
        {
          'doc_type': 'privacy',
          'title': '隐私政策',
          'version': '2026.11.06',
          'updated_at': '2026-11-06',
          'url': 'https://example.com/legal/privacy',
        },
        {
          'doc_type': 'terms',
          'title': '用户协议',
          'version': '2026.11.06',
          'updated_at': '2026-11-06',
          'url': 'https://example.com/legal/terms',
        },
      ],
    });

    expect(policies.version, '2026.11.06');
    expect(policies.documents, hasLength(2));
    expect(policies.documents.first.docType, 'privacy');
  });

  test('AppUser 解析并复制 needsReconsent', () {
    final user = AppUser.fromJson({
      'id': 7,
      'phone': '13900000000',
      'nickname': '同学',
      'role': 'student',
      'is_child': false,
      'needs_reconsent': true,
    });

    expect(user.needsReconsent, isTrue);
    expect(user.copyWith(needsReconsent: false).needsReconsent, isFalse);
    expect(user.copyWith(needsReconsent: false).id, 7);
  });
}
