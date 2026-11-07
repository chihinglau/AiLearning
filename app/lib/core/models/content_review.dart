/// P2-09 内容审核双人复核模型。
class ContentReview {
  const ContentReview({
    required this.id,
    required this.contentType,
    required this.contentId,
    required this.title,
    required this.status,
    required this.submittedBy,
    required this.submittedAt,
    this.note,
    this.reviewedBy,
    this.reviewedAt,
    this.comment,
    this.publishedBy,
    this.publishedAt,
  });

  final int id;
  final String contentType;
  final int contentId;
  final String title;
  final String status;
  final int submittedBy;
  final DateTime submittedAt;
  final String? note;
  final int? reviewedBy;
  final DateTime? reviewedAt;
  final String? comment;
  final int? publishedBy;
  final DateTime? publishedAt;

  String get typeLabel => switch (contentType) {
        'question' => '题目',
        'exam' => '试卷',
        _ => '内容',
      };

  String get statusLabel => switch (status) {
        'pending' => '待复核',
        'approved' => '已通过',
        'rejected' => '已驳回',
        'published' => '已发布',
        _ => status,
      };

  bool get canApprove => status == 'pending';
  bool get canPublish => status == 'approved';

  factory ContentReview.fromJson(Map<String, dynamic> json) {
    return ContentReview(
      id: json['id'] as int? ?? 0,
      contentType: json['content_type'] as String? ?? '',
      contentId: json['content_id'] as int? ?? 0,
      title: json['title'] as String? ?? '',
      status: json['status'] as String? ?? 'pending',
      submittedBy: json['submitted_by'] as int? ?? 0,
      submittedAt:
          DateTime.tryParse(json['submitted_at'] as String? ?? '') ??
              DateTime.now(),
      note: json['note'] as String?,
      reviewedBy: json['reviewed_by'] as int?,
      reviewedAt: DateTime.tryParse(json['reviewed_at'] as String? ?? ''),
      comment: json['comment'] as String?,
      publishedBy: json['published_by'] as int?,
      publishedAt: DateTime.tryParse(json['published_at'] as String? ?? ''),
    );
  }
}
