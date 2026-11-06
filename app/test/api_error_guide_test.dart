import 'package:ai_learning/core/errors/api_error_guide.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ApiErrorGuide', () {
    test('TOKEN_REVOKED 引导重新登录', () {
      final guide = ApiErrorGuide.from(
        const ApiException('token revoked', statusCode: 401, code: 'TOKEN_REVOKED'),
      );

      expect(guide.action, ApiErrorAction.reLogin);
      expect(guide.message, '登录状态已失效，请重新登录');
    });

    test('PERMISSION_DENIED 给无权限提示', () {
      final guide = ApiErrorGuide.from(
        const ApiException('denied', statusCode: 403, code: 'PERMISSION_DENIED'),
      );

      expect(guide.action, ApiErrorAction.none);
      expect(guide.message, '当前账号无权限执行该操作');
    });

    test('GRADE_REQUIRED 引导完善年级', () {
      final guide = ApiErrorGuide.from(
        const ApiException('grade required', statusCode: 403, code: 'GRADE_REQUIRED'),
      );

      expect(guide.action, ApiErrorAction.onboarding);
      expect(guide.message, '请先完善年级信息');
    });

    test('未识别业务码按状态码兜底', () {
      final unauthorized =
          ApiErrorGuide.from(const ApiException('unauthorized', statusCode: 401));
      expect(unauthorized.action, ApiErrorAction.reLogin);

      final forbidden =
          ApiErrorGuide.from(const ApiException('forbidden', statusCode: 403));
      expect(forbidden.action, ApiErrorAction.none);
      expect(forbidden.message, '当前账号无权限执行该操作');
    });

    test('普通错误保留后端文案', () {
      final guide = ApiErrorGuide.from(
        const ApiException('试卷不存在', statusCode: 404),
      );

      expect(guide.action, ApiErrorAction.none);
      expect(guide.message, '试卷不存在');
    });
  });
}
