import 'package:ai_learning/core/models/content_review.dart';
import 'package:ai_learning/core/models/user.dart';
import 'package:ai_learning/core/providers.dart';
import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/services/content_review_service.dart';
import 'package:ai_learning/features/content/content_review_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const _auditor = AppUser(
  id: 1,
  phone: '13600000052',
  nickname: '审核员',
  role: 'auditor',
  permissions: ['content:review:decide'],
);

const _operator = AppUser(
  id: 2,
  phone: '13600000051',
  nickname: '内容运营',
  role: 'content_operator',
  permissions: ['content:question:write', 'content:publish'],
);

ContentReview _review({
  int id = 1,
  String status = 'pending',
  String title = '待复核单元测',
}) {
  return ContentReview(
    id: id,
    contentType: 'exam',
    contentId: 9,
    title: title,
    status: status,
    submittedBy: 2,
    submittedAt: DateTime(2026, 11, 7),
  );
}

class _FakeContentReviewService extends ContentReviewService {
  _FakeContentReviewService(this.items) : super(ApiClient());

  final List<ContentReview> items;
  final List<int> decided = [];
  final List<int> published = [];
  final List<String?> requestedStatus = [];

  @override
  Future<List<ContentReview>> list({String? status}) async {
    requestedStatus.add(status);
    if (status == null) return items;
    return items.where((item) => item.status == status).toList();
  }

  @override
  Future<ContentReview> decide(
    int reviewId, {
    required bool approve,
    String? comment,
  }) async {
    decided.add(reviewId);
    final index = items.indexWhere((item) => item.id == reviewId);
    final updated = ContentReview(
      id: items[index].id,
      contentType: items[index].contentType,
      contentId: items[index].contentId,
      title: items[index].title,
      status: approve ? 'approved' : 'rejected',
      submittedBy: items[index].submittedBy,
      submittedAt: items[index].submittedAt,
      reviewedBy: 1,
      reviewedAt: DateTime(2026, 11, 7),
      comment: comment,
    );
    items[index] = updated;
    return updated;
  }

  @override
  Future<ContentReview> publish(int reviewId) async {
    published.add(reviewId);
    final index = items.indexWhere((item) => item.id == reviewId);
    final updated = ContentReview(
      id: items[index].id,
      contentType: items[index].contentType,
      contentId: items[index].contentId,
      title: items[index].title,
      status: 'published',
      submittedBy: items[index].submittedBy,
      submittedAt: items[index].submittedAt,
      publishedBy: 2,
      publishedAt: DateTime(2026, 11, 7),
    );
    items[index] = updated;
    return updated;
  }
}

Widget _app(_FakeContentReviewService service, AppUser user) {
  return ProviderScope(
    overrides: [
      currentUserProvider.overrideWith((ref) => user),
      contentReviewServiceProvider.overrideWithValue(service),
    ],
    child: const MaterialApp(home: ContentReviewPage()),
  );
}

void main() {
  testWidgets('审核员通过待复核内容', (tester) async {
    tester.view.physicalSize = const Size(900, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final service = _FakeContentReviewService([_review()]);
    await tester.pumpWidget(_app(service, _auditor));
    await tester.pumpAndSettle();

    expect(find.text('内容审核'), findsOneWidget);
    expect(find.text('待复核单元测'), findsOneWidget);
    expect(find.text('待复核'), findsWidgets);

    await tester.tap(find.byKey(const ValueKey('approve-1')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(service.decided, [1]);
    expect(find.text('已通过复核'), findsOneWidget);

    await tester.pumpAndSettle();
    expect(find.text('暂无复核单'), findsOneWidget);
    expect(service.requestedStatus.last, 'pending');
  });

  testWidgets('运营发布已通过复核内容', (tester) async {
    tester.view.physicalSize = const Size(900, 1600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final service = _FakeContentReviewService([
      _review(status: 'approved', title: '已通过的单元测'),
    ]);
    await tester.pumpWidget(_app(service, _operator));
    await tester.pumpAndSettle();

    await tester.tap(find.text('已通过'));
    await tester.pumpAndSettle();

    expect(find.text('已通过的单元测'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('publish-1')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(service.published, [1]);
    expect(find.text('内容已发布'), findsOneWidget);
  });
}
