import 'package:ai_learning/core/models/exam.dart';

/// D-09 §4.4 / §5.4：窗口状态 × 作答状态的唯一决策表。
///
/// 抽成纯函数便于单测（L22 / L25），并避免两个页面各自写一套按钮逻辑。
enum ExamCardAction {
  start,
  resume,
  report,
  pendingReport,
  scheduled,
  closed,
}

class ExamCardDecision {
  const ExamCardDecision(
    this.action,
    this.label, {
    this.route,
    this.message,
  });

  final ExamCardAction action;
  final String label;
  final String? route;
  final String? message;

  bool get enabled =>
      action == ExamCardAction.start ||
      action == ExamCardAction.resume ||
      action == ExamCardAction.report;
}

ExamCardDecision examCardDecision(ExamSummary exam) {
  final attempt = exam.attempt;
  final reportRoute =
      attempt == null ? null : '/exam/report/${attempt.id}';

  switch (exam.windowState) {
    case 'scheduled':
      return ExamCardDecision(
        ExamCardAction.scheduled,
        '未开始',
        route: reportRoute,
        message: '开放时间：${exam.windowRange ?? '待公布'}',
      );
    case 'closed':
      return ExamCardDecision(
        ExamCardAction.closed,
        '已结束',
        route: reportRoute,
        message: '考试窗口已结束',
      );
  }

  switch (exam.category) {
    case 'in_progress':
      return ExamCardDecision(
        ExamCardAction.resume,
        '继续答题',
        route: '/exam/${exam.id}',
      );
    case 'completed':
      if (attempt == null) {
        return const ExamCardDecision(
          ExamCardAction.pendingReport,
          '查看报告',
          message: '报告尚未生成，请稍后重试',
        );
      }
      return ExamCardDecision(
        ExamCardAction.report,
        '查看报告',
        route: reportRoute,
      );
    default:
      return ExamCardDecision(
        ExamCardAction.start,
        '开始考试',
        route: '/exam/${exam.id}',
      );
  }
}
