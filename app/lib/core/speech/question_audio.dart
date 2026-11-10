import 'dart:async';
import 'dart:io';

import 'package:ai_learning/core/services/api_client.dart';
import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';

/// 预生成音频的本地缓存上限（TT-04：按教材 LRU 200 MB）。
const int questionAudioCacheBytes = 200 * 1024 * 1024;

/// 生成音频统一按 1.0 倍速合成；客户端用播放器变速，避免为每个语速重复生成。
const double questionAudioGeneratedSpeed = 1.0;

typedef QuestionAudioFetcher = Future<Uint8List> Function(int questionId);

/// 单题音频文件缓存：命中直接返回；未命中下载落盘；超限按最后访问时间淘汰。
class QuestionAudioCache {
  QuestionAudioCache({
    required this.fetch,
    required Directory directory,
    int maxBytes = questionAudioCacheBytes,
  })  : _directory = directory,
        _maxBytes = maxBytes;

  final QuestionAudioFetcher fetch;
  final Directory _directory;
  final int _maxBytes;

  Directory get directory => _directory;

  File fileFor(int questionId) => File('${_directory.path}/q_$questionId.opus');

  /// 返回可播放文件；下载失败（404 未就绪 / 429 / 离线）返回 null，由调用方回退系统 TTS。
  Future<File?> ensure(int questionId) async {
    final file = fileFor(questionId);
    try {
      if (await file.exists()) {
        if (await file.length() > 0) {
          await file.setLastModified(DateTime.now());
          return file;
        }
        await file.delete();
      }
    } catch (_) {
      // 缓存读失败按未命中处理
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
    Future<Directory> Function()? directoryResolver,
    int maxBytes = questionAudioCacheBytes,
  })  : _api = api,
        _player = player ?? JustAudioQuestionPlayer(),
        _ownsPlayer = player == null,
        _fetcher = fetcher,
        _directoryResolver = directoryResolver ?? _defaultDirectory,
        _maxBytes = maxBytes;

  final ApiClient _api;
  final QuestionAudioPlayer _player;
  final bool _ownsPlayer;
  final QuestionAudioFetcher? _fetcher;
  final Future<Directory> Function() _directoryResolver;
  final int _maxBytes;

  QuestionAudioCache? _cache;

  ValueListenable<bool> get playing => _player.playing;

  /// 预生成音频的播放进度；系统 TTS 播放时为 null（不做句级高亮）。
  ValueListenable<double?> get progress => _player.progress;

  Future<QuestionAudioCache> _cacheInstance() async {
    return _cache ??= QuestionAudioCache(
      fetch: _fetcher ?? _download,
      directory: await _directoryResolver(),
      maxBytes: _maxBytes,
    );
  }

  Future<Uint8List> _download(int questionId) async {
    // 固定按生成倍速取音频，实际语速由播放器变速，避免多倍速重复合成。
    final binary = await _api.getBytes(
      '/api/learn/questions/$questionId/audio',
      query: {'speed': questionAudioGeneratedSpeed},
    );
    return binary.bytes;
  }

  /// true 表示已开始播放预生成音频；false 表示调用方应回退系统 TTS。
  Future<bool> play(int questionId, {double speed = 1.0}) async {
    try {
      final cache = await _cacheInstance();
      final file = await cache.ensure(questionId);
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
      return Directory('${base.path}/question_audio');
    } catch (_) {
      final base = await getTemporaryDirectory();
      return Directory('${base.path}/question_audio');
    }
  }
}
