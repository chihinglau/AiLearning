import 'package:ai_learning/core/services/server_config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('规范化服务地址：补齐校验并去掉末尾斜杠', () {
    expect(
      ServerConfig.normalize(' http://192.168.1.10:18080/ '),
      'http://192.168.1.10:18080',
    );
    expect(ServerConfig.normalize('https://api.example.com'), 'https://api.example.com');
  });

  test('非法服务地址返回 null', () {
    expect(ServerConfig.normalize(''), isNull);
    expect(ServerConfig.normalize('192.168.1.10:18080'), isNull);
    expect(ServerConfig.normalize('ftp://example.com'), isNull);
    expect(ServerConfig.normalize('http://'), isNull);
  });
}
