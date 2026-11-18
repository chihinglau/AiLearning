import 'dart:async';
import 'dart:io';

import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';

/// 预生成音频的本地缓存上限（TT-04：按教材 LRU 200 MB）。
const int questionAudioCacheBytes = 200 * 1024 * 1024;

/// 服务端音频资产版本。合成规则、音色或文本口径变化时递增：
/// 客户端缓存目录随之切换，避免本地 `q_<id>.opus` 把旧读音一直播下去。
const int questionAudioAssetVersion = 2;

/// 生成音频统一按 1.0 倍速合成；客户端用播放器变速，避免为每个语速重复生成。
const double questionAudioGeneratedSpeed = 1.0;

/// 同一道题的两类音频：读题（题干+选项）与听力材料（content.script）。
///
/// 服务端按 `kind` 分目录、分缓存键；客户端也按 kind 分本地文件名，
/// 否则 `q_12.opus` 会被两种语义互相覆盖。
enum QuestionAudioKind {
  reading,
  listening;

  /// 服务端 query 参数值
  String get wire => name;

  /// 本地缓存文件名后缀（reading 保持旧名，兼容既有缓存）
  String get fileSuffix => this == QuestionAudioKind.reading ? '' : '_listen';
}

typedef QuestionAudioFetcher = Future<Uint8List> Function(int questionId);

/// 条件请求通道：带 `If-None-Match` 取音频，命中（304）时 [ApiBinary.bytes] 为空。
typedef ConditionalAudioFetcher = Future<ApiBinary> Function(
  int questionId, {
  String? ifNoneMatch,
});

/// 单题音频文件缓存：命中直接返回；未命中下载落盘；超限按最后访问时间淘汰。
class QuestionAudioCache {
  QuestionAudioCache({
    required this.fetch,
    required Directory directory,
    int maxBytes = questionAudioCacheBytes,
    this.kind = QuestionAudioKind.reading,
    ConditionalAudioFetcher? conditionalFetch,
  })  : _directory = directory,
        _maxBytes = maxBytes,
        _conditionalFetch = conditionalFetch;

  final QuestionAudioFetcher fetch;
  final Directory _directory;
  final int _maxBytes;
  final QuestionAudioKind kind;

  /// 有该通道时，首次（或显式要求）播放会先做 ETag 条件校验：
  /// 服务端重合成过（ETag 变了）就重下，没变（304）就复用本地文件。
  final ConditionalAudioFetcher? _conditionalFetch;

  Directory get directory => _directory;

  File fileFor(int questionId) =>
      File('${_directory.path}/q_$questionId${kind.fileSuffix}.opus');

  /// ETag 旁挂文件：与音频同名加 `.etag` 后缀，避免改音频文件名。
  File etagFor(int questionId) =>
      File('${_directory.path}/q_$questionId${kind.fileSuffix}.etag');

  Future<String?> _readEtag(int questionId) async {
    try {
      final file = etagFor(questionId);
      if (!await file.exists()) return null;
      final text = (await file.readAsString()).trim();
      return text.isEmpty ? null : text;
    } catch (_) {
      return null;
    }
  }

  Future<void> _writeEtag(int questionId, String? etag) async {
    try {
      final file = etagFor(questionId);
      if (etag == null || etag.isEmpty) {
        if (await file.exists()) await file.delete();
        return;
      }
      await file.parent.create(recursive: true);
      await file.writeAsString(etag, flush: true);
    } catch (_) {
      // ETag 落盘失败只影响下次是否重下，不影响播放
    }
  }

  /// 返回可播放文件；下载失败（404 未就绪 / 429 / 离线）返回 null，由调用方回退系统 TTS。
  ///
  /// [revalidate] 为 true 且有条件请求通道时，即使本地已有文件也先问服务端一次：
  /// 这样可以发现「服务端已重合成」的情况，不必只靠资产版本号人工递增。
  Future<File?> ensure(
    int questionId, {
    bool revalidate = false,
  }) async {
    final file = fileFor(questionId);
    var hasLocal = false;
    try {
      if (await file.exists()) {
        if (await file.length() > 0) {
          hasLocal = true;
        } else {
          await file.delete();
        }
      }
    } catch (_) {
      // 缓存读失败按未命中处理
    }

    final conditional = _conditionalFetch;
    if (conditional != null && (revalidate || !hasLocal)) {
      final etag = hasLocal ? await _readEtag(questionId) : null;
      try {
        final binary = await conditional(questionId, ifNoneMatch: etag);
        if (binary.notModified) {
          if (hasLocal) {
            await file.setLastModified(DateTime.now());
            return file;
          }
          // 本地没文件却回 304：说明 ETag 与本地状态错位，落到下面的普通下载
        } else if (binary.bytes.isNotEmpty) {
          await file.parent.create(recursive: true);
          await file.writeAsBytes(binary.bytes, flush: true);
          await _writeEtag(questionId, binary.etag);
          await trim();
          return file;
        }
      } catch (_) {
        // 网络异常/限流：本地有文件就继续用，没有则退回普通下载通道
        if (hasLocal) {
          await file.setLastModified(DateTime.now());
          return file;
        }
      }
    }

    if (hasLocal) {
      await file.setLastModified(DateTime.now());
      return file;
    }

    final Uint8List bytes;
    try {
      bytes = await fetch(questionId);
    } catch (_) {
      return null;
    }
    if (bytes.isEmpty) return null;
    try {
      await file.parent.create(recursive: true);
      await file.writeAsBytes(bytes, flush: true);
    } catch (_) {
      return null;
    }
    await trim();
    return file;
  }

  /// LRU 淘汰：按最后访问时间升序删除，直到总量不超过上限。
  Future<void> trim() async {
    try {
      final files = <File>[];
      await for (final entity in _directory.list(recursive: true)) {
        if (entity is File && entity.path.endsWith('.opus')) {
          files.add(entity);
        }
      }
      final sizes = <File, int>{};
      var total = 0;
      for (final file in files) {
        try {
          final size = await file.length();
          sizes[file] = size;
          total += size;
        } catch (_) {
          continue;
        }
      }
      if (total <= _maxBytes) return;
      final ordered = files.toList()
        ..sort((a, b) {
          try {
            return a.lastModifiedSync().compareTo(b.lastModifiedSync());
          } catch (_) {
            return 0;
          }
        });
      for (final file in ordered) {
        if (total <= _maxBytes) break;
        final size = sizes[file] ?? 0;
        try {
          await file.delete();
          total -= size;
        } catch (_) {
          // 删除失败不阻断其他条目
        }
      }
    } catch (_) {
      // 目录不存在/不可读时忽略淘汰
    }
  }
}

/// 播放抽象：便于单测替换为假实现（不依赖平台插件）。
abstract class QuestionAudioPlayer {
  ValueListenable<bool> get playing;

  /// 播放进度 0–1（TT-06 句级高亮用）；未播放或未知时长时为 null。
  ValueListenable<double?> get progress;

  Future<void> play(File file, {double speed = 1.0});

  Future<void> stop();

  Future<void> dispose();
}

/// just_audio 实现（Android 用 ExoPlayer，支持 Ogg/Opus）。
class JustAudioQuestionPlayer implements QuestionAudioPlayer {
  JustAudioQuestionPlayer({AudioPlayer? player}) : _player = player ?? AudioPlayer() {
    _subscription = _player.playerStateStream.listen((state) {
      final active =
          state.playing && state.processingState != ProcessingState.completed;
      if (_playing.value != active) _playing.value = active;
      if (!active) _progress.value = null;
    });
    _positionSubscription = _player.positionStream.listen((position) {
      final total = _player.duration;
      if (total == null || total.inMilliseconds <= 0) return;
      final ratio = position.inMilliseconds / total.inMilliseconds;
      _progress.value = ratio.clamp(0.0, 1.0);
    });
  }

  final AudioPlayer _player;
  final ValueNotifier<bool> _playing = ValueNotifier<bool>(false);
  final ValueNotifier<double?> _progress = ValueNotifier<double?>(null);
  late final StreamSubscription<PlayerState> _subscription;
  late final StreamSubscription<Duration> _positionSubscription;

  @override
  ValueListenable<bool> get playing => _playing;

  @override
  ValueListenable<double?> get progress => _progress;

  @override
  Future<void> play(File file, {double speed = 1.0}) async {
    await _player.setFilePath(file.path);
    await _player.setSpeed(speed);
    unawaited(_player.play());
  }

  @override
  Future<void> stop() async {
    try {
      await _player.stop();
    } finally {
      _playing.value = false;
      _progress.value = null;
    }
  }

  @override
  Future<void> dispose() async {
    await _subscription.cancel();
    await _positionSubscription.cancel();
    await _player.dispose();
    _playing.dispose();
    _progress.dispose();
  }
}

/// 读题音频服务：优先播放服务端预生成音频，失败时由调用方回退系统 TTS。
class QuestionAudioService {
  QuestionAudioService({
    required ApiClient api,
    QuestionAudioPlayer? player,
    QuestionAudioFetcher? fetcher,
    ConditionalAudioFetcher? conditionalFetcher,
    Future<Directory> Function()? directoryResolver,
    int maxBytes = questionAudioCacheBytes,
    this.kind = QuestionAudioKind.reading,
  })  : _api = api,
        _player = player ?? JustAudioQuestionPlayer(),
        _ownsPlayer = player == null,
        _fetcher = fetcher,
        _directoryResolver = directoryResolver ?? _defaultDirectory,
        _maxBytes = maxBytes {
    // 注入了 fetcher 说明走替身（单测/离线包），此时不再发真实条件请求，
    // 否则单测会去打真实网络；生产路径不注入 fetcher，默认接真实通道。
    _conditionalFetcher = conditionalFetcher ?? (fetcher == null ? _conditionalDownload : null);
  }

  final ApiClient _api;
  final QuestionAudioPlayer _player;
  final bool _ownsPlayer;
  final QuestionAudioFetcher? _fetcher;
  late final ConditionalAudioFetcher? _conditionalFetcher;
  final Future<Directory> Function() _directoryResolver;
  final int _maxBytes;

  /// 该实例负责的音频类型；听力材料请用 `listeningAudioServiceProvider`。
  final QuestionAudioKind kind;

  /// 本次启动内已经做过 ETag 条件校验的题目。
  /// 一次校验之后同一题再播放就不必再问服务端，避免连点喇叭打满限流。
  final Set<int> _revalidated = <int>{};

  QuestionAudioCache? _cache;

  ValueListenable<bool> get playing => _player.playing;

  /// 预生成音频的播放进度；系统 TTS 播放时为 null（不做句级高亮）。
  ValueListenable<double?> get progress => _player.progress;

  Future<QuestionAudioCache> _cacheInstance() async {
    return _cache ??= QuestionAudioCache(
      fetch: _fetcher ?? _download,
      conditionalFetch: _conditionalFetcher,
      directory: await _directoryResolver(),
      maxBytes: _maxBytes,
      kind: kind,
    );
  }

  Future<ApiBinary> _conditionalDownload(
    int questionId, {
    String? ifNoneMatch,
  }) {
    // 注意：这里刻意不传 attempt_id。试卷听力额度由 takeListeningPlay 单独记账，
    // 音频接口若也带 attempt_id 会重复扣额度。
    return _api.getBytes(
      '/api/learn/questions/$questionId/audio',
      query: {
        'speed': questionAudioGeneratedSpeed,
        if (kind != QuestionAudioKind.reading) 'kind': kind.wire,
      },
      ifNoneMatch: ifNoneMatch,
    );
  }

  Future<Uint8List> _download(int questionId) async {
    // 固定按生成倍速取音频，实际语速由播放器变速，避免多倍速重复合成。
    final binary = await _api.getBytes(
      '/api/learn/questions/$questionId/audio',
      query: {
        'speed': questionAudioGeneratedSpeed,
        if (kind != QuestionAudioKind.reading) 'kind': kind.wire,
      },
    );
    return binary.bytes;
  }

  /// true 表示已开始播放预生成音频；false 表示调用方应回退系统 TTS。
  Future<bool> play(int questionId, {double speed = 1.0}) async {
    try {
      final cache = await _cacheInstance();
      // 本次启动内该题第一次播放时做一次 ETag 条件校验：服务端重合成过就换新音频，
      // 没变则 304 复用本地文件。之后的重复播放直接命中缓存，不再打扰服务端。
      final firstThisRun = _revalidated.add(questionId);
      final file = await cache.ensure(questionId, revalidate: firstThisRun);
      if (file == null) return false;
      await _player.play(file, speed: speed);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> stop() => _player.stop();

  Future<void> dispose() async {
    if (_ownsPlayer) await _player.dispose();
  }

  static Future<Directory> _defaultDirectory() async {
    try {
      final base = await getApplicationSupportDirectory();
      return _versionedDirectory(base);
    } catch (_) {
      final base = await getTemporaryDirectory();
      return _versionedDirectory(base);
    }
  }

  /// 目录名带资产版本；顺带清掉其它版本的缓存目录，避免旧读音长期占空间。
  static Directory _versionedDirectory(Directory base) {
    final current = Directory(
      '${base.path}/question_audio_v$questionAudioAssetVersion',
    );
    try {
      for (final entity in base.listSync()) {
        if (entity is! Directory) continue;
        final name = entity.path.split(Platform.pathSeparator).last;
        final isAudioDir =
            name == 'question_audio' ||
            (name.startsWith('question_audio_v') && entity.path != current.path);
        if (isAudioDir) entity.delete(recursive: true).ignore();
      }
    } catch (_) {
      // 清理失败不影响播放：新目录照常使用
    }
    return current;
  }
}
