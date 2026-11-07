import 'package:ai_learning/core/models/content_review.dart';
import 'package:ai_learning/core/services/api_client.dart';

/// P2-09 内容审核双人复核：运营提交、审核员复核、运营发布。
class ContentReviewService {
  ContentReviewService(this._api);

  final ApiClient _api;

  Future<List<ContentReview>> list({String? status}) async {
    final query = <String, dynamic>{};
    if (status != null && status.isNotEmpty) query['status'] = status;
    final data = await _api.getList('/api/content/reviews', query: query);
    return data
        .map((item) => ContentReview.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<ContentReview> decide(
    int reviewId, {
    required bool approve,
    String? comment,
  }) async {
    final data = await _api.postJson(
      '/api/content/reviews/$reviewId/decision',
      {
        'decision': approve ? 'approve' : 'reject',
        'comment': ?comment,
      },
    );
    return ContentReview.fromJson(data);
  }

  Future<ContentReview> publish(int reviewId) async {
    final data =
        await _api.postJson('/api/content/reviews/$reviewId/publish', const {});
    return ContentReview.fromJson(data);
  }
}
