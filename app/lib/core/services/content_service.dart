import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/practice.dart';
import 'package:ai_learning/core/services/api_client.dart';

class ContentService {
  ContentService(this._api);

  final ApiClient _api;

  Future<List<Textbook>> textbooks({String? subject, int? grade}) async {
    final data = await _api.getList(
      '/api/public/textbooks',
      query: {
        'subject': ?subject,
        'grade': ?grade,
      },
    );
    return data
        .map((item) => Textbook.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<Chapter>> chapters(int textbookId) async {
    final data = await _api.getList(
      '/api/public/chapters',
      query: {'textbook_id': textbookId},
    );
    return data
        .map((item) => Chapter.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<Question>> startPractice({
    required int chapterId,
    int count = 10,
  }) async {
    final data = await _api.postJson('/api/practice/start', {
      'chapter_id': chapterId,
      'count': count,
    });
    final questions = data['questions'] as List<dynamic>? ?? const [];
    return questions
        .map((item) => Question.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<SubmitResult> submitAnswer({
    required int questionId,
    required String optionKey,
    required int durationMs,
  }) async {
    final data = await _api.postJson('/api/practice/submit', {
      'question_id': questionId,
      'user_answer': {'value': optionKey},
      'duration_ms': durationMs,
    });
    return SubmitResult.fromJson(data);
  }
}
