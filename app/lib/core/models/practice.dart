class SubmitResult {
  const SubmitResult({
    required this.isCorrect,
    required this.correctAnswer,
    this.analysis,
  });

  final bool isCorrect;
  final Map<String, dynamic> correctAnswer;
  final String? analysis;

  factory SubmitResult.fromJson(Map<String, dynamic> json) {
    return SubmitResult(
      isCorrect: json['is_correct'] as bool? ?? false,
      correctAnswer: json['correct_answer'] as Map<String, dynamic>? ?? const {},
      analysis: json['analysis'] as String?,
    );
  }
}
