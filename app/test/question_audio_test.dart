import 'dart:io';

import 'package:ai_learning/core/services/api_client.dart';
import 'package:ai_learning/core/speech/question_audio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakePlayer implements QuestionAudioPlayer {
  final ValueNotifier<bool> _playing = ValueNotifier<bool>(false);
  final ValueNotifier<double?> _progress = ValueNotifier<double?>(null);
  File? playedFile;
  double? playedSpeed;

  @override
  ValueListenable<bool> get playing => _playing;

  @override
  ValueListenable<double?> get progress => _progress;

  @override
  Future<void> play(File file, {double speed = 1.0}) async {
    playedFile = file;
    playedSpeed = speed;
    _playing.value = true;
    _progress.value = 0;
  }

  @override
  Future<void> stop() async {
    _playing.value = false;
    _progress.value = null;
  }

  @override
  Future<void> dispose() async {
    _playing.dispose();
    _progress.dispose();
  }
}

void main() {
  late Directory tempDir;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('qaudio_test');
  });

  tearDown(() async {
    if (await tempDir.exists()) {
      await tempDir.delete(recursive: true);
    }
  });

  test('缓存命中后不再请求网络', () async {
    var calls = 0;
    final cache = QuestionAudioCache(
      fetch: (id) async {
        calls += 1;
        return Uint8List.fromList([1, 2, 3]);
      },
      directory: tempDir,
    );

    final first = await cache.ensure(12);
    final second = await cache.ensure(12);

    expect(first, isNotNull);
    expect(second?.path, first?.path);
    expect(calls, 1);
    expect(await first!.length(), 3);
  });

  test('下载失败返回 null，交由系统 TTS 兜底', () async {
    final cache = QuestionAudioCache(
      fetch: (id) async => throw const ApiException('未就绪', statusCode: 404),
      directory: tempDir,
    );

    expect(await cache.ensure(7), isNull);
    expect(await cache.fileFor(7).exists(), isFalse);
  });

  test('超出上限按最后访问时间淘汰旧文件', () async {
    final files = <File>[];
    for (var index = 0; index < 3; index++) {
      final file = File('${tempDir.path}/old_$index.opus');
      await file.writeAsBytes(Uint8List(30));
      await file.setLastModified(
        DateTime.now().subtract(Duration(minutes: 10 - index)),
      );
      files.add(file);
    }
    final cache = QuestionAudioCache(
      fetch: (id) async => Uint8List(30),
      directory: tempDir,
      maxBytes: 60,
    );

    await cache.trim();

    var total = 0;
    final remaining = <File>[];
    await for (final entity in tempDir.list()) {
      if (entity is File) {
        total += await entity.length();
        remaining.add(entity);
      }
    }
    expect(total, lessThanOrEqualTo(60));
    final names = remaining.map((file) => file.uri.pathSegments.last);
    expect(names, contains(files.last.uri.pathSegments.last));
    expect(names, isNot(contains(files.first.uri.pathSegments.last)));
  });

  test('服务优先播放预生成音频并按设置变速', () async {
    final player = _FakePlayer();
    final service = QuestionAudioService(
      api: ApiClient(baseUrl: 'http://127.0.0.1:1'),
      player: player,
      fetcher: (id) async => Uint8List.fromList([9, 9]),
      directoryResolver: () async => tempDir,
    );

    final played = await service.play(5, speed: 0.85);

    expect(played, isTrue);
    expect(player.playedFile?.path, endsWith('q_5.opus'));
    expect(player.playedSpeed, 0.85);
    await service.stop();
    expect(player.playing.value, isFalse);
  });

  test('音频未就绪返回 false', () async {
    final player = _FakePlayer();
    final service = QuestionAudioService(
      api: ApiClient(baseUrl: 'http://127.0.0.1:1'),
      player: player,
      fetcher: (id) async => throw const ApiException('未就绪', statusCode: 404),
      directoryResolver: () async => tempDir,
    );

    expect(await service.play(5), isFalse);
    expect(player.playedFile, isNull);
  });
}
