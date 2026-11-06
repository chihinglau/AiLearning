import 'package:ai_learning/core/models/practice_session.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('PracticePreview', () {
    test('fromJson 解析题量、覆盖与题型分布', () {
      final preview = PracticePreview.fromJson({
        'count': 10,
        'available': 8,
        'insufficient': true,
        'estimated_minutes': 12,
        'kp_coverage': 0.8,
        'covered_kp_count': 4,
        'range_kp_count': 5,
        'q_type_mix': {'choice': 6, 'fill': 4},
        'due_review_count': 2,
        'seed': 42,
      });

      expect(preview.count, 10);
      expect(preview.available, 8);
      expect(preview.insufficient, isTrue);
      expect(preview.estimatedMinutes, 12);
      expect(preview.kpCoverage, 0.8);
      expect(preview.qTypeMix['choice'], 6);
      expect(preview.dueReviewCount, 2);
      expect(preview.seed, 42);
    });
  });

  group('PracticeStartResult', () {
    test('fromJson 解析题目与 session/seed', () {
      final result = PracticeStartResult.fromJson({
        'session_id': 12,
        'seed': 7,
        'questions': [
          {
            'id': 3,
            'chapter_id': 1,
            'subject': 'math',
            'q_type': 'judge',
            'content': {'stem': '1+1=2'},
            'options': [
              {'key': 'T', 'text': '正确'},
              {'key': 'F', 'text': '错误'},
            ],
          },
        ],
      });

      expect(result.sessionId, 12);
      expect(result.seed, 7);
      expect(result.questions, hasLength(1));
      expect(result.questions.first.qType, 'judge');
    });
  });

  group('PracticeSessionData', () {
    test('fromJson 解析续答进度与已答状态', () {
      final session = PracticeSessionData.fromJson({
        'id': 12,
        'mode': 'sync',
        'scope_type': 'chapter',
        'scope_ids': [1, 2],
        'seed': 7,
        'total_count': 5,
        'answered_count': 3,
        'correct_count': 2,
        'started_at': '2026-11-06T10:00:00',
        'next_index': 3,
        'answers': [
          {
            'question_id': 1,
            'answered': true,
            'is_correct': false,
            'user_answer': {'value': 'A'},
          },
        ],
      });

      expect(session.scopeType, 'chapter');
      expect(session.scopeIds, [1, 2]);
      expect(session.answeredCount, 3);
      expect(session.nextIndex, 3);
      expect(session.answers.first.isCorrect, isFalse);
      expect(session.answers.first.userAnswer?['value'], 'A');
    });
  });

  group('PracticeFinish', () {
    test('fromJson 解析结算、知识点表现与下一步', () {
      final finish = PracticeFinish.fromJson({
        'session': {
          'id': 12,
          'mode': 'special',
          'scope_type': 'kp',
          'scope_ids': [3],
          'seed': 7,
          'total_count': 10,
          'answered_count': 10,
          'correct_count': 8,
          'started_at': '2026-11-06T10:00:00',
          'next_index': 10,
        },
        'accuracy': 0.8,
        'duration_ms': 900000,
        'wrong_count': 2,
        'kp_stats': [
          {
            'knowledge_point_id': 3,
            'name': '20以内加法',
            'answered': 10,
            'correct': 8,
            'accuracy': 0.8,
            'mastery_score': 76,
          },
        ],
        'next_actions': ['replay', 'wrong_book', 'back'],
      });

      expect(finish.session.answeredCount, 10);
      expect(finish.accuracy, 0.8);
      expect(finish.wrongCount, 2);
      expect(finish.kpStats.first.name, '20以内加法');
      expect(finish.nextActions, ['replay', 'wrong_book', 'back']);
    });
  });
}
