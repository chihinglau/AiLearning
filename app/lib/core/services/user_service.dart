import 'package:ai_learning/core/services/api_client.dart';

class GradeChangeOutcome {
  const GradeChangeOutcome({
    this.grade,
    this.stage,
    this.requiresConfirm = false,
    this.confirmToken,
    this.impactMessage,
  });

  final int? grade;
  final String? stage;
  final bool requiresConfirm;
  final String? confirmToken;
  final String? impactMessage;
}

class UserService {
  UserService(this._api);

  final ApiClient _api;

  Future<GradeChangeOutcome> changeGrade(
    int grade, {
    String? confirmToken,
  }) async {
    try {
      final data = await _api.putJson('/api/users/me/grade', {
        'grade': grade,
        'confirm_token': ?confirmToken,
      });
      return GradeChangeOutcome(
        grade: data['grade'] as int?,
        stage: data['stage'] as String?,
      );
    } on ApiException catch (error) {
      if (error.statusCode == 428) {
        final payload = error.payload ?? const <String, dynamic>{};
        final impact = payload['impact'];
        return GradeChangeOutcome(
          requiresConfirm: true,
          confirmToken: payload['confirm_token'] as String?,
          impactMessage: impact is Map<String, dynamic>
              ? impact['message'] as String?
              : null,
        );
      }
      rethrow;
    }
  }
}
