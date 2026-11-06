import 'package:ai_learning/core/models/content.dart';
import 'package:ai_learning/core/models/learn.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('KnowledgeNode', () {
    test('fromJson 解析掌握度与分段', () {
      final node = KnowledgeNode.fromJson({
        'id': 3,
        'subject': 'math',
        'name': '20以内加减法',
        'grade': 1,
        'explanation': '凑十法',
        'mastery_score': 84.0,
        'mastery_confidence': 2,
        'mastery_band': 'skilled',
        'question_count': 4,
      });

      expect(node.id, 3);
      expect(node.masteryScore, 84.0);
      expect(node.masteryBand, 'skilled');
      expect(node.bandLabel, '较熟练');
      expect(node.questionCount, 4);
      expect(node.subjectLabel, '数学');
    });

    test('缺省掌握度按未学习(weak)处理', () {
      final node = KnowledgeNode.fromJson({'id': 1, 'subject': 'chinese', 'name': 'x'});
      expect(node.masteryScore, 0);
      expect(node.masteryBand, 'weak');
      expect(node.bandLabel, '薄弱');
    });
  });

  group('ChapterTree', () {
    test('fromJson 解析章节与知识点列表', () {
      final tree = ChapterTree.fromJson({
        'id': 10,
        'textbook_id': 2,
        'grade': 1,
        'name': '加与减',
        'order_index': 1,
        'summary': null,
        'knowledge_points': [
          {'id': 1, 'subject': 'math', 'name': 'a', 'mastery_score': 60.0},
          {'id': 2, 'subject': 'math', 'name': 'b'},
        ],
      });

      expect(tree.id, 10);
      expect(tree.knowledgePoints, hasLength(2));
      expect(tree.knowledgePoints.first.masteryScore, 60.0);
    });
  });

  group('LearnSubmitResult', () {
    test('correctAnswerText 支持单值与多答案列表', () {
      final single = LearnSubmitResult.fromJson({
        'is_correct': false,
        'correct_answer': {'value': 'A'},
        'mastery_score': 0.0,
        'in_wrong_book': true,
      });
      expect(single.correctAnswerText, 'A');
      expect(single.inWrongBook, isTrue);
      expect(single.masteryScore, 0.0);

      final multi = LearnSubmitResult.fromJson({
        'is_correct': true,
        'correct_answer': {'value': ['A', 'C']},
      });
      expect(multi.correctAnswerText, 'A、C');
    });
  });

  group('WrongQuestionItem 与 LearnStats', () {
    test('错题条目解析日期与错因', () {
      final item = WrongQuestionItem.fromJson({
        'id': 1,
        'question_id': 9,
        'wrong_count': 2,
        'correct_streak': 0,
        'status': 'active',
        'interval_days': 1,
        'next_review_at': '2026-11-07T10:00:00',
        'last_wrong_at': '2026-11-06T10:00:00',
        'wrong_reason': 'calculation',
        'subject': 'math',
        'q_type': 'fill',
        'stem': '3 + 5 = ?',
        'chapter_id': 1,
        'knowledge_point_id': 2,
        'difficulty': 2,
      });
      expect(item.wrongCount, 2);
      expect(item.isActive, isTrue);
      expect(item.qType, 'fill');
      expect(item.nextReviewAt, isNotNull);
    });

    test('学情统计与薄弱点解析', () {
      final stats = LearnStats.fromJson({
        'total_answered': 10,
        'total_correct': 7,
        'accuracy': 0.7,
        'streak_days': 3,
        'due_review_count': 2,
        'active_wrong_count': 4,
        'weak_points': [
          {'id': 5, 'subject': 'english', 'name': '时态', 'mastery_score': 20.0},
        ],
      });
      expect(stats.totalAnswered, 10);
      expect(stats.accuracyPercent, '70%');
      expect(stats.streakDays, 3);
      expect(stats.weakPoints.single.name, '时态');
    });
  });

  group('HomeData 首页聚合', () {
    test('解析教材、今日计划、继续学习与推荐', () {
      final home = HomeData.fromJson({
        'grade': 3,
        'stage': 'primary',
        'grade_group': 'primary_mid',
        'semester': 'first',
        'region': 'shenzhen',
        'needs_binding': false,
        'textbooks': [
          {
            'subject': 'math',
            'textbook_id': 12,
            'version': '人教版',
            'grade': 3,
            'semester': 'first',
            'mismatch': false,
          },
        ],
        'recommended': <Map<String, dynamic>>[],
        'mismatch_subjects': <String>[],
        'today_plan': {
          'due_review': 3,
          'practice_questions': 10,
          'practice_minutes': 15,
          'new_kp_target': 1,
        },
        'continue_learning': {
          'subject': 'math',
          'chapter_id': 7,
          'chapter_name': '加与减',
          'knowledge_point_id': 21,
          'knowledge_point_name': '两位数加法',
        },
        'recommendation': {
          'action': 'review',
          'label': '去复习',
          'reason': '今日有 3 道错题到期',
          'knowledge_point_id': null,
        },
        'pending_exams': <Map<String, dynamic>>[],
      });

      expect(home.grade, 3);
      expect(home.stageEnum?.label, '小学');
      expect(home.textbooks.single.subjectLabel, '数学');
      expect(home.todayPlan.dueReview, 3);
      expect(home.continueLearning?.title, '两位数加法');
      expect(home.textbookOf('math')?.textbookId, 12);
      expect(home.recommendation.action, 'review');
    });

    test('解析单元测推荐与章节/试卷信息', () {
      final recommendation = HomeRecommendation.fromJson({
        'action': 'unit_test',
        'label': '单元测试',
        'reason': '「第一单元」已掌握，建议完成单元测检验',
        'chapter_id': 7,
        'chapter_name': '第一单元',
        'exam_id': 99,
      });

      expect(recommendation.action, 'unit_test');
      expect(recommendation.chapterId, 7);
      expect(recommendation.chapterName, '第一单元');
      expect(recommendation.examId, 99);

      final home = HomeData.fromJson({
        'grade': 3,
        'today_plan': <String, dynamic>{},
        'recommendation': {
          'action': 'unit_test',
          'label': '单元测试',
          'exam_id': 99,
        },
        'pending_exams': [
          {'exam_id': 99, 'title': '第一单元测', 'exam_type': 'unit'},
        ],
      });
      expect(home.pendingExams, hasLength(1));
      expect(home.pendingExams.first['exam_id'], 99);
    });

    test('未绑定教材时 needs_binding 与推荐教材可用', () {
      final home = HomeData.fromJson({
        'grade': 1,
        'needs_binding': true,
        'recommended': [
          {'subject': 'chinese', 'textbook_id': 3, 'version': '人教版', 'grade': 1},
        ],
        'today_plan': <String, dynamic>{},
        'recommendation': {'action': 'daily', 'label': '每日一练'},
      });

      expect(home.needsBinding, isTrue);
      expect(home.textbooks, isEmpty);
      expect(home.recommended.single.subjectLabel, '语文');
      expect(home.continueLearning, isNull);
      expect(home.todayPlan.practiceQuestions, 0);
    });
  });

  group('Question 知识点关联', () {
    test('Question.fromJson 解析 knowledge_point_id', () {
      final q = Question.fromJson({
        'id': 1,
        'chapter_id': 1,
        'knowledge_point_id': 8,
        'subject': 'math',
        'q_type': 'choice',
        'content': {'stem': '1+1=?'},
        'options': [
          {'key': 'A', 'text': '1'},
          {'key': 'B', 'text': '2'},
        ],
        'difficulty': 1,
        'tags': <String>[],
      });
      expect(q.knowledgePointId, 8);
      expect(q.options, hasLength(2));
    });
  });
}
