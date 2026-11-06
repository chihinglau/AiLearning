import 'package:ai_learning/core/models/ai.dart';
import 'package:ai_learning/core/services/api_client.dart';

/// P2-06 AI 讲解与错题归因：服务端做 Prompt 安全与额度控制。
class AIService {
  AIService(this._api);

  final ApiClient _api;

  Future<AIExplanation> explain(
    int questionId, {
    int? wrongQuestionId,
    String? focus,
    int? studentId,
  }) async {
    final suffix = studentId == null ? '' : '?student_id=$studentId';
    final data = await _api.postJson('/api/ai/explain$suffix', {
      'question_id': questionId,
      'wrong_question_id': ?wrongQuestionId,
      'focus': ?focus,
    });
    return AIExplanation.fromJson(data);
  }

  Future<AIDiagnosis> diagnose(int wrongQuestionId, {int? studentId}) async {
    final suffix = studentId == null ? '' : '?student_id=$studentId';
    final data = await _api.postJson('/api/ai/diagnose$suffix', {
      'wrong_question_id': wrongQuestionId,
    });
    return AIDiagnosis.fromJson(data);
  }
}
