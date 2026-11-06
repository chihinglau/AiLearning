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
      expect(exam.windowOpen, isTrue);
      expect(exam.windowState, 'unscheduled');
    });

    test('解析考试窗口与可进入状态', () {
      final scheduled = ExamSummary.fromJson({
        'id': 8,
        'title': '期中测试',
        'subject': 'math',
        'grade': 3,
        'exam_type': 'midterm',
        'total_score': 100,
        'time_limit_min': 90,
        'question_count': 28,
        'category': 'available',
        'window_start': '2026-11-08T01:00:00',
        'window_end': '2026-11-08T02:30:00',
        'window_state': 'scheduled',
      });
      expect(scheduled.typeLabel, '期中');
      expect(scheduled.windowOpen, isFalse);
      expect(scheduled.windowLabel, '未到开放时间');
      expect(scheduled.windowRange, isNotNull);

      final closed = ExamSummary.fromJson({
        'id': 9,
        'title': '期末测试',
        'subject': 'english',
        'grade': 3,
        'exam_type': 'final',
        'total_score': 100,
        'time_limit_min': 90,
        'question_count': 36,
        'category': 'available',
        'window_end': '2026-11-06T01:00:00',
        'window_state': 'closed',
      });
      expect(closed.typeLabel, '期末');
      expect(closed.windowOpen, isFalse);
      expect(closed.windowLabel, '已结束');
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

    test('解析待自评主观题：参考答案、评分点与自评分', () {
      final report = ExamReport.fromJson({
        'attempt_id': 22,
        'exam_id': 4,
        'exam_title': '期中测试',
        'exam_type': 'midterm',
        'status': 'grading',
        'full_score': 100,
        'pending_subjective': [
          {
            'question_id': 101,
            'q_type': 'answer',
            'stem': '计算 3/4 + 1/4 并写出过程',
            'full_score': 50,
            'user_answer': {'value': '4/4'},
            'reference_answer': {'value': '1'},
            'scoring_points': ['列式正确（25 分）', '结果正确（25 分）'],
            'analysis': '同分母分数相加，分子相加。',
            'self_score': 40,
          },
        ],
      });

      expect(report.pendingSubjective, hasLength(1));
      final item = report.pendingSubjective.first;
      expect(item.questionId, 101);
      expect(item.userAnswerText, '4/4');
      expect(item.referenceAnswerText, '1');
      expect(item.scoringPoints, hasLength(2));
      expect(item.selfScore, 40);
    });
    test('解析能力维度、班级平均与成绩趋势', () {
      final report = ExamReport.fromJson({
        'attempt_id': 23,
        'exam_id': 5,
        'exam_title': '第二次单元测',
        'exam_type': 'unit',
        'status': 'completed',
        'total_score': 85,
        'full_score': 100,
        'ability_stats': [
          {
            'ability': 'understand',
            'label': '理解',
            'question_count': 4,
            'score': 32,
            'full_score': 40,
            'score_rate': 0.8,
          },
          {
            'ability': 'calculate',
            'label': '计算',
            'question_count': 3,
            'score': 24,
            'full_score': 30,
            'score_rate': 0.8,
          },
          {
            'ability': 'analyze',
            'label': '分析',
            'question_count': 2,
            'score': 12,
            'full_score': 30,
            'score_rate': 0.4,
          },
        ],
        'class_average': {
          'available': true,
          'class_name': '三年级1班',
          'student_count': 4,
          'average_score': 72.5,
          'average_rate': 0.725,
        },
        'trend': {
          'points': [
            {
              'attempt_id': 21,
              'exam_id': 4,
              'exam_title': '第一次单元测',
              'exam_type': 'unit',
              'score_rate': 0.6,
              'total_score': 60,
              'submitted_at': '2026-11-06T02:00:00',
            },
            {
              'attempt_id': 23,
              'exam_id': 5,
              'exam_title': '第二次单元测',
              'exam_type': 'unit',
              'score_rate': 0.85,
              'total_score': 85,
              'submitted_at': '2026-11-06T03:00:00',
            },
          ],
          'delta_rate': 0.25,
        },
      });

      expect(report.abilityStats, hasLength(3));
      expect(report.abilityStats[1].label, '计算');
      expect(report.abilityStats[2].scoreRate, 0.4);
      expect(report.classAverage.available, isTrue);
      expect(report.classAverage.className, '三年级1班');
      expect(report.classAverage.averageScore, 72.5);
      expect(report.trend.points, hasLength(2));
      expect(report.trend.points.last.examTitle, '第二次单元测');
      expect(report.trend.deltaRate, 0.25);
    });
  });
}
