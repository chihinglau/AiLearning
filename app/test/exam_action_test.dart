import 'package:ai_learning/core/models/exam.dart';
import 'package:ai_learning/core/models/exam_action.dart';
import 'package:flutter_test/flutter_test.dart';

ExamSummary _summary({
  String category = 'available',
  String windowState = 'open',
  ExamAttemptBrief? attempt,
  String? sourceName,
  int attemptCount = 0,
  DateTime? windowStart,
}) {
  return ExamSummary(
    id: 42,
    title: '一年级数学单元测',
    subject: 'math',
    grade: 1,
    examType: 'unit',
    totalScore: 100,
    timeLimitMin: 60,
    questionCount: 20,
    category: category,
    windowState: windowState,
    windowStart: windowStart,
    attempt: attempt,
    sourceName: sourceName,
    attemptCount: attemptCount,
  );
}

ExamAttemptBrief _attempt({int id = 7, String status = 'submitted'}) {
  return ExamAttemptBrief(
    id: id,
    status: status,
    seed: 1,
    startedAt: DateTime(2026, 1, 1),
  );
}

void main() {
  group('examCardDecision（D-09 §4.4 / §5.4 六态决策表）', () {
    test('开放中 + 未考 → 开始考试', () {
      final decision = examCardDecision(_summary());
      expect(decision.action, ExamCardAction.start);
      expect(decision.route, '/exam/42');
      expect(decision.enabled, isTrue);
      expect(decision.message, isNull);
    });

    test('开放中 + 进行中 → 继续答题', () {
      final decision = examCardDecision(_summary(
        category: 'in_progress',
        attempt: _attempt(status: 'in_progress'),
      ));
      expect(decision.action, ExamCardAction.resume);
      expect(decision.route, '/exam/42');
      expect(decision.label, '继续答题');
    });

    test('开放中 + 已完成且有 attempt → 查看报告', () {
      final decision = examCardDecision(
        _summary(category: 'completed', attempt: _attempt()),
      );
      expect(decision.action, ExamCardAction.report);
      expect(decision.route, '/exam/report/7');
    });

    test('已完成但缺 attempt → 明确提示，禁止静默', () {
      final decision = examCardDecision(_summary(category: 'completed'));
      expect(decision.action, ExamCardAction.pendingReport);
      expect(decision.route, isNull);
      expect(decision.message, '报告尚未生成，请稍后重试');
      expect(decision.enabled, isFalse);
    });

    test('未到开放时间且未考 → 禁用并给开放时间提示', () {
      final decision = examCardDecision(_summary(
        windowState: 'scheduled',
        windowStart: DateTime(2030, 6, 1),
      ));
      expect(decision.action, ExamCardAction.scheduled);
      expect(decision.route, isNull);
      expect(decision.message, contains('开放时间'));
      expect(decision.enabled, isFalse);
    });

    test('窗口已结束但已交卷 → 仍可看报告', () {
      final decision = examCardDecision(_summary(
        windowState: 'closed',
        category: 'completed',
        attempt: _attempt(),
      ));
      expect(decision.action, ExamCardAction.closed);
      expect(decision.route, '/exam/report/7');
    });

    test('不限时窗口（unscheduled）视同开放', () {
      final decision = examCardDecision(_summary(windowState: 'unscheduled'));
      expect(decision.action, ExamCardAction.start);
      expect(decision.route, '/exam/42');
    });
  });

  group('D-09 新增模型解析', () {
    test('ExamSummary 解析溯源字段与作答次数', () {
      final exam = ExamSummary.fromJson({
        'id': 1,
        'title': '2020 深圳真题',
        'subject': 'math',
        'grade': 1,
        'exam_type': 'mock',
        'total_score': 100,
        'time_limit_min': 60,
        'question_count': 10,
        'category': 'completed',
        'window_state': 'open',
        'source_name': '深圳市教育考试院公开真题',
        'license_note': '公开卷，仅用于练习',
        'adapted_from': '2020 原卷',
        'attempt_count': 2,
      });
      expect(exam.sourceLabel, '深圳市教育考试院公开真题');
      expect(exam.licenseNote, '公开卷，仅用于练习');
      expect(exam.adaptedFrom, '2020 原卷');
      expect(exam.attemptCount, 2);
    });

    test('缺来源显示「来源待补录」', () {
      expect(_summary().sourceLabel, '来源待补录');
      expect(_summary(sourceName: '  ').sourceLabel, '来源待补录');
    });

    test('PastPaperFilters 容错解析', () {
      final filters = PastPaperFilters.fromJson({
        'years': [2026, 2020],
        'subjects': ['math', 'chinese'],
        'regions': ['深圳'],
        'grades': [1],
        'exam_types': ['mock'],
      });
      expect(filters.years, [2026, 2020]);
      expect(filters.subjects, ['math', 'chinese']);
      expect(filters.regions, ['深圳']);
      expect(
        const PastPaperFilters().years,
        isEmpty,
      );
    });

    test('ExamAttemptHistory 报告路由', () {
      final item = ExamAttemptHistory.fromJson({
        'attempt_id': 9,
        'exam_id': 42,
        'exam_title': '单元测试',
        'exam_type': 'unit',
        'status': 'submitted',
        'started_at': '2026-01-01T08:00:00',
        'total_score': 88.5,
        'full_score': 100,
      });
      expect(item.route, '/exam/report/9');
      expect(item.totalScore, 88.5);
    });

    test('PastPaperDetail 不含答案字段', () {
      final detail = PastPaperDetail.fromJson({
        'id': 42,
        'title': '真题',
        'subject': 'math',
        'grade': 1,
        'exam_type': 'mock',
        'total_score': 100,
        'time_limit_min': 60,
        'question_count': 10,
        'category': 'available',
        'window_state': 'open',
        'source_name': '公开真题',
        'source': 'mock',
        'attempt_count': 3,
      });
      expect(detail.summary.sourceName, '公开真题');
      expect(detail.source, 'mock');
      expect(detail.attemptCount, 3);
    });
  });
}
