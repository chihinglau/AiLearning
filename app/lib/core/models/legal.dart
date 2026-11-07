/// 法务文档与同意状态模型（R-03）。
class LegalDocument {
  const LegalDocument({
    required this.docType,
    required this.title,
    required this.version,
    required this.content,
    this.updatedAt = '',
    this.url = '',
  });

  final String docType;
  final String title;
  final String version;
  final String content;
  final String updatedAt;
  final String url;

  factory LegalDocument.fromJson(Map<String, dynamic> json) {
    return LegalDocument(
      docType: json['doc_type'] as String? ?? '',
      title: json['title'] as String? ?? '',
      version: json['version'] as String? ?? '',
      content: json['content'] as String? ?? '',
      updatedAt: json['updated_at'] as String? ?? '',
      url: json['url'] as String? ?? '',
    );
  }
}

class LegalDocumentMeta {
  const LegalDocumentMeta({
    required this.docType,
    required this.title,
    required this.version,
    this.updatedAt = '',
    this.url = '',
  });

  final String docType;
  final String title;
  final String version;
  final String updatedAt;
  final String url;

  factory LegalDocumentMeta.fromJson(Map<String, dynamic> json) {
    return LegalDocumentMeta(
      docType: json['doc_type'] as String? ?? '',
      title: json['title'] as String? ?? '',
      version: json['version'] as String? ?? '',
      updatedAt: json['updated_at'] as String? ?? '',
      url: json['url'] as String? ?? '',
    );
  }
}

class LegalPolicies {
  const LegalPolicies({required this.version, required this.documents});

  final String version;
  final List<LegalDocumentMeta> documents;

  factory LegalPolicies.fromJson(Map<String, dynamic> json) {
    final list = (json['documents'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(LegalDocumentMeta.fromJson)
        .toList();
    return LegalPolicies(
      version: json['version'] as String? ?? '',
      documents: list,
    );
  }
}
