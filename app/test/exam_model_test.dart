import 'package:ai_learning/core/models/exam.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ExamSummary', () {
    test('fromJson 解析分类、作答摘要与类型标签', () {
      final exam = ExamSummary.fromJson({
        'id': 7,
        'title': '第一单元测试',
        'subject': 'math',
        'grade': 1,
        'year': 2026,
        'exam_type': 'unit',
        'total_score': 100,
        'time_limit_min': 45,
        'question_count': 20,
        'category': 'in_progress',
        'attempt': {
          'id': 11,
          'status': 'in_progress',
          'seed': 2,
          'started_at': '2026-11-06T02:00:00',
          'remaining_seconds': 1800,
        },
      });

      expect(exam.typeLabel, '单元测');
      expect(exam.category, 'in_progress');
      expect(exam.attempt?.id, 11);
      expect(exam.attempt?.remainingSeconds, 1800);
    });
  });

  group('ExamAttempt', () {
    test('fromJson 解析试卷题目、已存答案与续答位置', () {
      final attempt = ExamAttempt.fromJson({
        'id': 21,
        'exam_id': 3,
        'status': 'in_progress',
        'seed': 1,
        'started_at': '2026-11-06T01:00:00',
        'submit_token': 'token-1',
        'remaining_seconds': 900,
        'server_now': '2026-11-06T01:15:00',
        'exam': {
          'id': 3,
          'title': '期中测试',
          'subject': 'chinese',
          'grade': 1,
          'source': 'generated',
          'exam_type': 'midterm',
          'total_score': 100,
          'time_limit_min': 60,
          'status': 'published',
          'question_count': 1,
          'questions': [
            {
              'id': 55,
              'chapter_id': 2,
              'subject': 'chinese',
              'q_type': 'choice',
              'content': {'stem': '下列读音正确的是？'},
              'options': [
                {'key': 'A', 'text': '花朵'},
                {'key': 'B', 'text': '花多'},
              ],
              'score': 5,
              'section_index': 0,
            },
          ],
        },
        'answers': [
          {'question_id': 55, 'user_answer': {'value': 'B'}},
        ],
        'next_index': 1,
      });

      expect(attempt.exam.questions, hasLength(1));
      expect(attempt.exam.questions.first.score, 5);
      expect(attempt.answers.first.userAnswer?['value'], 'B');
      expect(attempt.nextIndex, 1);
      expect(attempt.submitToken, 'token-1');
    });
  });

  group('ExamReport', () {
    test('fromJson 解析题型/知识点统计、错题与下一步', () {
      final report = ExamReport.fromJson({
        'attempt_id': 21,
        'exam_id': 3,
        'exam_title': '期中测试',
        'exam_type': 'midterm',
        'status': 'grading',
        'total_score': 80,
        'full_score': 100,
        'objective_score': 80,
        'correct_count': 16,
        'question_count': 20,
        'answered_count': 20,
        'accuracy': 0.8,
        'duration_ms': 1800000,
        'type_stats': [
          {
            'q_type': 'choice',
            'question_count': 10,
            'answered': 10,
            'correct': 8,
            'score': 40,
            'full_score': 50,
            'score_rate': 0.8,
          },
        ],
        'kp_stats': [
          {
            'knowledge_point_id': 8,
            'name': '拼音',
            'question_count': 2,
            'correct': 0,
            'score': 0,
            'full_score': 10,
            'score_rate': 0,
          },
        ],
        'wrong_questions': [
          {
            'question_id': 55,
            'q_type': 'choice',
            'stem': '下列读音正确的是？',
            'user_answer': {'value': 'A'},
            'correct_answer': {'value': 'B'},
            'analysis': '“花朵”读作 huā duǒ。',
            'score': 0,
            'full_score': 5,
          },
        ],
        'next_actions': [
          {
            'action': 'weak_practice',
            'label': '薄弱点专项练习',
            'knowledge_point_ids': [8],
            'count': 1,
          },
        ],
      });

      expect(report.status, 'grading');
      expect(report.typeStats.first.scoreRate, 0.8);
      expect(report.kpStats.first.name, '拼音');
      expect(report.wrongQuestions.first.correctAnswerText, 'B');
      expect(report.wrongQuestions.first.userAnswerText, 'A');
      expect(report.nextActions.first.knowledgePointIds, [8]);
    });
  });
}
