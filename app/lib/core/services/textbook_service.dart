import 'package:ai_learning/core/models/textbook_binding.dart';
import 'package:ai_learning/core/services/api_client.dart';

class TextbookService {
  TextbookService(this._api);

  final ApiClient _api;

  Future<List<TextbookBinding>> listBindings() async {
    final data = await _api.getList('/api/me/textbooks');
    return data
        .map((item) => TextbookBinding.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<TextbookRecommendation> recommend() async {
    final data = await _api.getJson('/api/me/textbooks/recommend');
    return TextbookRecommendation.fromJson(data);
  }

  Future<List<TextbookBinding>> autoBind() async {
    final data = await _api.postJson('/api/me/textbooks/auto-bind', const {});
    final items = data['bindings'] as List<dynamic>? ?? const [];
    return items
        .map((item) => TextbookBinding.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<TextbookBinding> bind({
    required String subject,
    required int textbookId,
  }) async {
    final data = await _api.postJson('/api/me/textbooks/bind', {
      'subject': subject,
      'textbook_id': textbookId,
    });
    return TextbookBinding.fromJson(data);
  }

  Future<TextbookBinding> unbind(int bindingId) async {
    final data = await _api.deleteJson('/api/me/textbooks/$bindingId');
    return TextbookBinding.fromJson(data);
  }
}
