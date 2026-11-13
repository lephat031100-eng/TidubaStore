import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Animated Tiduba intro. Supply [nextScreen] to replace this route after the
/// animation, or [onAnimationComplete] when navigation is managed by the app.
class TidubaSplashScreen extends StatefulWidget {
  const TidubaSplashScreen({
    super.key,
    this.onAnimationComplete,
    this.nextScreen,
  });

  final VoidCallback? onAnimationComplete;
  final Widget? nextScreen;

  @override
  State<TidubaSplashScreen> createState() => _TidubaSplashScreenState();
}

typedef SplashScreen = TidubaSplashScreen;

class _TidubaSplashScreenState extends State<TidubaSplashScreen>
    with SingleTickerProviderStateMixin {
  static const _duration = Duration(milliseconds: 3200);
  static const _crestAsset = 'assets/images/tiduba_crest.png';

  late final AnimationController _controller;
  late final _BlueprintGeometry _blueprint;
  late final Animation<double> _crestOpacity;
  late final Animation<double> _crestScale;
  late final Animation<double> _titleOpacity;
  late final Animation<Offset> _titleSlide;
  late final Animation<double> _storeOpacity;
  late final Animation<Offset> _storeSlide;
  late final Animation<double> _taglineOpacity;
  late final Animation<Offset> _taglineSlide;
  bool _didPrecache = false;
  bool _didComplete = false;

  @override
  void initState() {
    super.initState();
    _blueprint = _BlueprintGeometry();
    _controller = AnimationController(vsync: this, duration: _duration);
    _crestOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(.375, .65625, curve: Curves.easeOutCubic),
    );
    _crestScale = Tween<double>(begin: .94, end: 1).animate(CurvedAnimation(
      parent: _controller,
      curve: const Interval(.375, .65625, curve: Curves.easeOutCubic),
    ));
    _titleOpacity = _fade(.625, .79);
    _titleSlide = _slide(.625, .79);
    _storeOpacity = _fade(.67, .84);
    _storeSlide = _slide(.67, .84);
    _taglineOpacity = _fade(.72, .91);
    _taglineSlide = _slide(.72, .91);
    _playIntro();
  }

  Animation<double> _fade(double start, double end) => CurvedAnimation(
        parent: _controller,
        curve: Interval(start, end, curve: Curves.easeOutCubic),
      );

  Animation<Offset> _slide(double start, double end) => Tween<Offset>(
        begin: const Offset(0, .25),
        end: Offset.zero,
      ).animate(CurvedAnimation(
        parent: _controller,
        curve: Interval(start, end, curve: Curves.easeOutCubic),
      ));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_didPrecache) return;
    _didPrecache = true;
    precacheImage(
      ResizeImage(const AssetImage(_crestAsset), width: 600),
      context,
    );
  }

  Future<void> _playIntro() async {
    await _controller.forward();
    _complete();
  }

  void _complete() {
    if (!mounted || _didComplete) return;
    _didComplete = true;
    final nextScreen = widget.nextScreen;
    if (nextScreen != null) {
      Navigator.of(context).pushReplacement<void, void>(
        PageRouteBuilder<void>(
          transitionDuration: const Duration(milliseconds: 420),
          pageBuilder: (_, animation, __) => FadeTransition(
            opacity: animation,
            child: nextScreen,
          ),
        ),
      );
    } else {
      widget.onAnimationComplete?.call();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.dark,
      child: Scaffold(
        backgroundColor: const Color(0xFFF8FAFC),
        body: DecoratedBox(
          decoration: const BoxDecoration(
            gradient: RadialGradient(
              center: Alignment(0, -.08),
              radius: 1.12,
              colors: [Color(0xFFFFFFFF), Color(0xFFF8FAFC), Color(0xFFE2E8F0)],
              stops: [0, .56, 1],
            ),
          ),
          child: SafeArea(
            child: Stack(
              children: [
                const Positioned.fill(
                  child: RepaintBoundary(
                    child: CustomPaint(painter: _CornerMeshPainter()),
                  ),
                ),
                Positioned.fill(
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final compact = constraints.maxHeight < 560;
                      final crestWidth = math.min(
                        170.0,
                        constraints.maxWidth * .54,
                      );
                      final crestHeight = crestWidth * .86;
                      return SingleChildScrollView(
                        child: ConstrainedBox(
                          constraints: BoxConstraints(
                            minHeight: constraints.maxHeight,
                          ),
                          child: Center(
                            child: Padding(
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 24),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  RepaintBoundary(
                                    child: SizedBox(
                                      width: crestWidth,
                                      height: crestHeight,
                                      child: Stack(
                                        alignment: Alignment.center,
                                        children: [
                                          CustomPaint(
                                            size: Size(crestWidth, crestHeight),
                                            painter: _BlueprintPainter(
                                              progress: _controller,
                                              geometry: _blueprint,
                                            ),
                                          ),
                                          FadeTransition(
                                            opacity: _crestOpacity,
                                            child: ScaleTransition(
                                              scale: _crestScale,
                                              child: RepaintBoundary(
                                                child: Image.asset(
                                                  _crestAsset,
                                                  width: crestWidth,
                                                  height: crestHeight,
                                                  cacheWidth: 600,
                                                  fit: BoxFit.contain,
                                                  filterQuality:
                                                      FilterQuality.medium,
                                                ),
                                              ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                  SizedBox(height: compact ? 8 : 14),
                                  FadeTransition(
                                    opacity: _titleOpacity,
                                    child: SlideTransition(
                                      position: _titleSlide,
                                      child: const Text(
                                        'TIDUBA',
                                        textAlign: TextAlign.center,
                                        style: TextStyle(
                                          color: Color(0xFF475569),
                                          fontSize: 32,
                                          height: 1.04,
                                          fontWeight: FontWeight.w900,
                                          letterSpacing: 3.5,
                                        ),
                                      ),
                                    ),
                                  ),
                                  FadeTransition(
                                    opacity: _storeOpacity,
                                    child: SlideTransition(
                                      position: _storeSlide,
                                      child: const Text(
                                        'STORE',
                                        textAlign: TextAlign.center,
                                        style: TextStyle(
                                          color: Color(0xFF64748B),
                                          fontSize: 17,
                                          height: 1.3,
                                          fontWeight: FontWeight.w500,
                                          letterSpacing: 6,
                                        ),
                                      ),
                                    ),
                                  ),
                                  SizedBox(height: compact ? 8 : 13),
                                  FadeTransition(
                                    opacity: _taglineOpacity,
                                    child: SlideTransition(
                                      position: _taglineSlide,
                                      child: const FittedBox(
                                        fit: BoxFit.scaleDown,
                                        child: Text(
                                          'QUALITY | SERVICE | INNOVATION',
                                          textAlign: TextAlign.center,
                                          style: TextStyle(
                                            color: Color(0xFF94A3B8),
                                            fontSize: 10,
                                            fontWeight: FontWeight.w600,
                                            letterSpacing: 2,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
                Positioned(
                  right: 16,
                  bottom: 14,
                  child: TextButton(
                    onPressed: _complete,
                    style: TextButton.styleFrom(
                      foregroundColor: const Color(0xFF334155),
                      backgroundColor: const Color(0xFFE2E8F0).withOpacity(.88),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 19,
                        vertical: 11,
                      ),
                      minimumSize: const Size(0, 44),
                      shape: const StadiumBorder(),
                      textStyle: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    child: const Text('Bỏ qua'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _BlueprintGeometry {
  _BlueprintGeometry() {
    strokes = [
      _BlueprintStroke(
          _closed([
            const Offset(50, 2),
            const Offset(67, 21),
            const Offset(97, 17),
            const Offset(83, 40),
            const Offset(98, 52),
            const Offset(76, 65),
            const Offset(50, 85),
            const Offset(24, 65),
            const Offset(2, 52),
            const Offset(17, 40),
            const Offset(3, 17),
            const Offset(33, 21),
          ]),
          const Color(0xFF64748B)),
      _BlueprintStroke(
          _closed([
            const Offset(50, 12),
            const Offset(85, 49),
            const Offset(50, 81),
            const Offset(15, 49),
          ]),
          const Color(0xFF0EA5E9)),
      _BlueprintStroke(
          _closed([
            const Offset(12, 45),
            const Offset(33, 36),
            const Offset(69, 36),
            const Offset(90, 45),
            const Offset(76, 59),
            const Offset(60, 53),
            const Offset(50, 48),
            const Offset(39, 53),
            const Offset(23, 59),
          ]),
          const Color(0xFF64748B)),
      _BlueprintStroke(
          _closed([
            const Offset(39, 45),
            const Offset(61, 45),
            const Offset(61, 72),
            const Offset(50, 84),
            const Offset(39, 72),
          ]),
          const Color(0xFF0EA5E9)),
      _BlueprintStroke(
          _open([
            const Offset(20, 53),
            const Offset(50, 70),
            const Offset(80, 53),
          ]),
          const Color(0xFF0EA5E9)),
    ];
    anchors = const [
      Offset(50, 2),
      Offset(97, 17),
      Offset(98, 52),
      Offset(50, 85),
      Offset(2, 52),
      Offset(3, 17),
      Offset(50, 12),
      Offset(85, 49),
      Offset(15, 49),
      Offset(50, 48),
      Offset(50, 84),
    ];
  }

  late final List<_BlueprintStroke> strokes;
  late final List<Offset> anchors;

  static Path _closed(List<Offset> points) => Path()..addPolygon(points, true);

  static Path _open(List<Offset> points) => Path()
    ..moveTo(points.first.dx, points.first.dy)
    ..lineTo(points[1].dx, points[1].dy)
    ..lineTo(points.last.dx, points.last.dy);
}

class _BlueprintStroke {
  factory _BlueprintStroke(Path path, Color color) {
    final metrics = path.computeMetrics().toList(growable: false);
    final metric = metrics.first;
    return _BlueprintStroke._(
      path,
      metric,
      color,
      _sampleEnds(metric),
    );
  }

  const _BlueprintStroke._(this.path, this.metric, this.color, this.sampleEnds);

  final Path path;
  final ui.PathMetric metric;
  final Color color;
  final List<double> sampleEnds;

  static List<double> _sampleEnds(ui.PathMetric metric) {
    final count = math.max(1, (metric.length / 5).ceil());
    return List<double>.generate(
      count,
      (index) => metric.length * (index + 1) / count,
      growable: false,
    );
  }
}

class _BlueprintPainter extends CustomPainter {
  _BlueprintPainter({required this.progress, required this.geometry})
      : super(repaint: progress);

  final Animation<double> progress;
  final _BlueprintGeometry geometry;

  static final Paint _linePaint = Paint()
    ..style = PaintingStyle.stroke
    ..strokeWidth = 1.5
    ..strokeCap = StrokeCap.round
    ..strokeJoin = StrokeJoin.round;
  static final Paint _solidNodePaint = Paint()..style = PaintingStyle.fill;
  static final Paint _ringNodePaint = Paint()
    ..style = PaintingStyle.stroke
    ..strokeWidth = 1.2;
  static final Paint _tickPaint = Paint()..strokeWidth = 1;

  @override
  void paint(Canvas canvas, Size size) {
    final value = progress.value;
    final sketch = (value / (1.4 / 3.2)).clamp(0.0, 1.0).toDouble();
    final fade =
        (1 - ((value - .375) / (.65625 - .375))).clamp(0.0, 1.0).toDouble();
    if (fade <= 0) return;

    canvas.save();
    canvas.scale(size.width / 100, size.height / 86);
    final strokeCount = geometry.strokes.length;
    for (var index = 0; index < strokeCount; index++) {
      final stroke = geometry.strokes[index];
      final local = ((sketch * strokeCount) - index).clamp(0.0, 1.0).toDouble();
      if (local <= 0) continue;
      final target = stroke.metric.length * local;
      _linePaint.color = stroke.color.withOpacity(.92 * fade);
      var from = 0.0;
      for (final end in stroke.sampleEnds) {
        if (from >= target) break;
        final visibleEnd = math.min(end, target);
        final a = stroke.metric.getTangentForOffset(from)?.position;
        final b = stroke.metric.getTangentForOffset(visibleEnd)?.position;
        if (a != null && b != null) canvas.drawLine(a, b, _linePaint);
        from = end;
      }
    }

    for (var index = 0; index < geometry.anchors.length; index++) {
      final threshold = index / geometry.anchors.length;
      if (sketch < threshold) continue;
      final point = geometry.anchors[index];
      _ringNodePaint.color = const Color(0xFF64748B).withOpacity(.9 * fade);
      _solidNodePaint.color = const Color(0xFF0EA5E9).withOpacity(.9 * fade);
      canvas.drawCircle(point, 2.5, _ringNodePaint);
      if (index.isEven) canvas.drawCircle(point, 1.05, _solidNodePaint);
    }

    _tickPaint.color = const Color(0xFF94A3B8).withOpacity(.68 * fade);
    for (final tick in const [
      Offset(11, 25),
      Offset(89, 25),
      Offset(16, 73),
      Offset(84, 73)
    ]) {
      canvas.drawLine(
          tick + const Offset(-2, 0), tick + const Offset(2, 0), _tickPaint);
      canvas.drawLine(
          tick + const Offset(0, -2), tick + const Offset(0, 2), _tickPaint);
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _BlueprintPainter oldDelegate) => false;
}

class _CornerMeshPainter extends CustomPainter {
  const _CornerMeshPainter();

  static final List<Path> _paths = [
    Path()
      ..moveTo(0, 0)
      ..lineTo(25, 0)
      ..lineTo(18, 13)
      ..lineTo(4, 22)
      ..lineTo(0, 17)
      ..moveTo(18, 13)
      ..lineTo(30, 21)
      ..lineTo(4, 22),
    Path()
      ..moveTo(100, 0)
      ..lineTo(75, 0)
      ..lineTo(82, 13)
      ..lineTo(96, 22)
      ..lineTo(100, 17)
      ..moveTo(82, 13)
      ..lineTo(70, 21)
      ..lineTo(96, 22),
    Path()
      ..moveTo(0, 100)
      ..lineTo(25, 100)
      ..lineTo(18, 87)
      ..lineTo(4, 78)
      ..lineTo(0, 83)
      ..moveTo(18, 87)
      ..lineTo(30, 79)
      ..lineTo(4, 78),
    Path()
      ..moveTo(100, 100)
      ..lineTo(75, 100)
      ..lineTo(82, 87)
      ..lineTo(96, 78)
      ..lineTo(100, 83)
      ..moveTo(82, 87)
      ..lineTo(70, 79)
      ..lineTo(96, 78),
  ];
  static final Path _starPath = Path()
    ..moveTo(91, 79)
    ..lineTo(93, 85)
    ..lineTo(99, 87)
    ..lineTo(93, 89)
    ..lineTo(91, 95)
    ..lineTo(89, 89)
    ..lineTo(83, 87)
    ..lineTo(89, 85)
    ..close();

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF94A3B8).withOpacity(.25)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..strokeCap = StrokeCap.round;
    canvas.save();
    canvas.scale(size.width / 100, size.height / 100);
    for (final path in _paths) {
      canvas.drawPath(path, paint);
    }
    canvas.drawPath(_starPath, paint..style = PaintingStyle.fill);
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _CornerMeshPainter oldDelegate) => false;
}
