/// P2-06 AI 讲解与错题归因模型。
class AIExplanation {
  const AIExplanation({
    required this.questionId,
    required this.provider,
    required this.explanation,
    this.focus,
    this.steps = const [],
    this.cautions = const [],
    this.remainingQuota = 0,
  });

  final int questionId;
  final String provider;
  final String explanation;
  final String? focus;
  final List<String> steps;
  final List<String> cautions;
  final int remainingQuota;

  factory AIExplanation.fromJson(Map<String, dynamic> json) {
    return AIExplanation(
      questionId: json['question_id'] as int? ?? 0,
      provider: json['provider'] as String? ?? 'rule',
      explanation: json['explanation'] as String? ?? '',
      focus: json['focus'] as String?,
      steps: (json['steps'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
      cautions: (json['cautions'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
      remainingQuota: json['remaining_quota'] as int? ?? 0,
    );
  }
}

class AIDiagnosis {
  const AIDiagnosis({
    required this.wrongId,
    required this.questionId,
    required this.provider,
    required this.reason,
    required this.reasonLabel,
    required this.confidence,
    required this.explanation,
    this.suggestions = const [],
    this.remainingQuota = 0,
  });

  final int wrongId;
  final int questionId;
  final String provider;
  final String reason;
  final String reasonLabel;
  final String confidence;
  final String explanation;
  final List<String> suggestions;
  final int remainingQuota;

  String get confidenceLabel => switch (confidence) {
        'high' => '高置信',
        'medium' => '中置信',
        _ => '低置信',
      };

  factory AIDiagnosis.fromJson(Map<String, dynamic> json) {
    return AIDiagnosis(
      wrongId: json['wrong_id'] as int? ?? 0,
      questionId: json['question_id'] as int? ?? 0,
      provider: json['provider'] as String? ?? 'rule',
      reason: json['reason'] as String? ?? 'other',
      reasonLabel: json['reason_label'] as String? ?? '其他',
      confidence: json['confidence'] as String? ?? 'low',
      explanation: json['explanation'] as String? ?? '',
      suggestions: (json['suggestions'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
      remainingQuota: json['remaining_quota'] as int? ?? 0,
    );
  }
}
