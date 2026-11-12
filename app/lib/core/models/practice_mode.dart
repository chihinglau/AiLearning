/// 三种练习模式的配置语义（前端配置页与后端组卷策略一一对应）。
///
/// 后端 `app/services/practice.py::MODE_POLICIES` 决定实际组卷行为，
/// 这里只负责展示差异与给出各模式的默认配置；两边 key 必须保持一致。
class PracticeModeSpec {
  const PracticeModeSpec({
    required this.key,
    required this.label,
    required this.tagline,
    required this.description,
    required this.points,
    required this.defaultCount,
    required this.defaultQTypes,
    this.preferredScope,
  });

  final String key;
  final String label;
  final String tagline;
  final String description;
  final List<String> points;
  final int defaultCount;
  final Set<String> defaultQTypes;

  /// 切到该模式时优先选用的范围（若入口没有提供该范围则保持原范围）。
  final String? preferredScope;
}

const List<String> kPracticeModeOrder = ['special', 'sync', 'pre_exam'];

const Map<String, PracticeModeSpec> kPracticeModes = {
  'special': PracticeModeSpec(
    key: 'special',
    label: '专项突破',
    tagline: '薄弱点集中练',
    description: '把题目集中在还没掌握的知识点与到期错题上，短平快补短板。',
    points: [
      '优先取掌握度低于 60 的知识点',
      '到期错题最多占 25%，且不重复练近 7 天做过的题',
      '默认 10 题，题型按学段常规配比',
    ],
    defaultCount: 10,
    defaultQTypes: {'choice', 'multiple', 'fill', 'judge'},
  ),
  'sync': PracticeModeSpec(
    key: 'sync',
    label: '同步巩固',
    tagline: '跟着教材进度练',
    description: '按教材章节顺序由易到难推进，用来巩固刚学完的内容。',
    points: [
      '题目按章节 → 知识点顺序排列，同章内由易到难',
      '均衡覆盖范围内知识点，到期错题只少量插入',
      '默认 15 题，优先练本单元',
    ],
    defaultCount: 15,
    defaultQTypes: {'choice', 'multiple', 'fill', 'judge'},
    preferredScope: 'chapter',
  ),
  'pre_exam': PracticeModeSpec(
    key: 'pre_exam',
    label: '考前速练',
    tagline: '全范围模拟卷',
    description: '按考试蓝图组一套覆盖全范围的卷子，先易后难，检验综合掌握情况。',
    points: [
      '考试题型配比（含解答题），知识点要求 100% 覆盖',
      '难度递进，不排重近期做过的题',
      '默认 20 题，优先练整册教材',
    ],
    defaultCount: 20,
    defaultQTypes: {'choice', 'multiple', 'fill', 'judge', 'answer'},
    preferredScope: 'textbook',
  ),
};

PracticeModeSpec practiceModeOf(String? key) =>
    kPracticeModes[key] ?? kPracticeModes['special']!;
