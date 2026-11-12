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

class _TidubaSplashScreenState extends State<TidubaSplashScreen>
    with SingleTickerProviderStateMixin {
  static const _animationDuration = Duration(milliseconds: 4000);

  late final AnimationController _controller;
  late final Animation<double> _titleOpacity;
  late final Animation<Offset> _titleSlide;
  late final Animation<double> _taglineOpacity;
  bool _didComplete = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: _animationDuration,
    );
    _titleOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(2.82 / 4, 3.42 / 4, curve: Curves.easeOut),
    );
    _titleSlide = Tween<Offset>(
      begin: const Offset(0, .18),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: const Interval(2.82 / 4, 3.42 / 4, curve: Curves.easeOutBack),
    ));
    _taglineOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(3.05 / 4, 3.5 / 4, curve: Curves.easeIn),
    );
    _playIntro();
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
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: const Color(0xFF0E1117),
        body: DecoratedBox(
          decoration: const BoxDecoration(
            gradient: RadialGradient(
              center: Alignment(0, -.12),
              radius: 1.05,
              colors: [Color(0xFF171B22), Color(0xFF0E1117), Color(0xFF0A0C10)],
              stops: [0, .58, 1],
            ),
          ),
          child: SafeArea(
            child: Stack(
              children: [
                Positioned.fill(
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final compact = constraints.maxHeight < 560;
                      return SingleChildScrollView(
                        child: ConstrainedBox(
                          constraints:
                              BoxConstraints(minHeight: constraints.maxHeight),
                          child: Center(
                            child: Padding(
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 24),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  AnimatedBuilder(
                                    animation: _controller,
                                    builder: (context, _) => CustomPaint(
                                      size: Size(
                                        math
                                            .min(constraints.maxWidth - 48, 236)
                                            .toDouble(),
                                        compact ? 174 : 196,
                                      ),
                                      painter: _TidubaTLogoPainter(
                                        progress: _controller.value,
                                      ),
                                    ),
                                  ),
                                  SizedBox(height: compact ? 8 : 18),
                                  FadeTransition(
                                    opacity: _titleOpacity,
                                    child: SlideTransition(
                                      position: _titleSlide,
                                      child: RichText(
                                        textAlign: TextAlign.center,
                                        text: const TextSpan(
                                          style: TextStyle(
                                            fontSize: 28,
                                            fontWeight: FontWeight.w700,
                                            letterSpacing: -.6,
                                          ),
                                          children: [
                                            TextSpan(
                                              text: 'Tiduba',
                                              style: TextStyle(
                                                  color: Colors.white),
                                            ),
                                            TextSpan(
                                              text: 'Store',
                                              style: TextStyle(
                                                  color: Color(0xFFEAD8B1)),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 9),
                                  FadeTransition(
                                    opacity: _taglineOpacity,
                                    child: const Text(
                                      'Camera, Equipment & Outfit Rental',
                                      textAlign: TextAlign.center,
                                      style: TextStyle(
                                        color: Color(0xFFA8A29E),
                                        fontSize: 13,
                                        letterSpacing: .25,
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
                  right: 12,
                  bottom: 12,
                  child: TextButton(
                    onPressed: _complete,
                    style: TextButton.styleFrom(
                      foregroundColor: const Color(0xFFFAF3E0),
                      backgroundColor: const Color(0xFF2C2A26),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 18, vertical: 11),
                      minimumSize: const Size(0, 44),
                      shape: const StadiumBorder(),
                      textStyle: const TextStyle(
                          fontSize: 13, fontWeight: FontWeight.w600),
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

class _TidubaTLogoPainter extends CustomPainter {
  const _TidubaTLogoPainter({required this.progress});

  final double progress;

  static const _designSize = 200.0;
  static const _hudEnd = .25;
  static const _assemblyStart = .25;
  static const _assemblyEnd = .575;
  static const _shineStart = .575;
  static const _shineEnd = .825;

  static final Path _leftWing = Path()
    ..moveTo(28, 24)
    ..lineTo(105, 24)
    ..lineTo(113, 39)
    ..lineTo(100, 68)
    ..lineTo(20, 68)
    ..close();

  static final Path _rightWing = Path()
    ..moveTo(105, 24)
    ..lineTo(190, 24)
    ..lineTo(182, 68)
    ..lineTo(100, 68)
    ..lineTo(113, 39)
    ..close();

  static final Path _keystone = Path()
    ..moveTo(94, 31)
    ..lineTo(112, 31)
    ..lineTo(124, 47)
    ..lineTo(112, 64)
    ..lineTo(94, 64)
    ..lineTo(82, 47)
    ..close();

  static final Path _pillar = Path()
    ..moveTo(78, 63)
    ..lineTo(126, 63)
    ..lineTo(113, 176)
    ..lineTo(93, 176)
    ..close();

  static final Path _outerPath = Path()
    ..moveTo(28, 24)
    ..lineTo(190, 24)
    ..lineTo(182, 68)
    ..lineTo(126, 68)
    ..lineTo(111, 176)
    ..lineTo(93, 176)
    ..lineTo(56, 68)
    ..lineTo(20, 68)
    ..close();

  static const List<Offset> _anchors = [
    Offset(28, 24),
    Offset(190, 24),
    Offset(182, 68),
    Offset(20, 68),
    Offset(95, 176),
    Offset(111, 176),
    Offset(82, 47),
    Offset(124, 47),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final scale = math
        .min(size.width / _designSize, size.height / _designSize)
        .toDouble();
    final dx = (size.width - _designSize * scale) / 2;
    final dy = (size.height - _designSize * scale) / 2;
    canvas.save();
    canvas.translate(dx, dy);
    canvas.scale(scale);

    final hudProgress = (progress / _hudEnd).clamp(0.0, 1.0).toDouble();
    final hudOpacity = progress < _assemblyEnd
        ? (1 - ((progress - _assemblyStart) / (_assemblyEnd - _assemblyStart)))
            .clamp(0.0, 1.0)
            .toDouble()
        : 0.0;
    if (hudOpacity > 0) _drawHud(canvas, hudProgress, hudOpacity);

    final assemble = Curves.easeOutExpo.transform(
      ((progress - _assemblyStart) / (_assemblyEnd - _assemblyStart))
          .clamp(0.0, 1.0)
          .toDouble(),
    );
    if (assemble > 0) _drawAssembly(canvas, assemble);

    final impact = ((progress - .525) / .085).clamp(0.0, 1.0).toDouble();
    if (impact > 0 && impact < 1) _drawImpact(canvas, impact);

    final shine = ((progress - _shineStart) / (_shineEnd - _shineStart))
        .clamp(0.0, 1.0)
        .toDouble();
    if (shine > 0 && shine < 1) _drawShine(canvas, shine);

    canvas.restore();
  }

  void _drawHud(Canvas canvas, double progress, double opacity) {
    final hud = Paint()
      ..color = const Color(0xFFFAF3E0).withOpacity(.25 * opacity)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.1
      ..strokeCap = StrokeCap.square;
    final center = Offset(105, 98);
    final reveal = Curves.easeOutCubic.transform(progress);
    canvas.drawLine(Offset(8, 98), Offset(42 + 25 * reveal, 98), hud);
    canvas.drawLine(Offset(158, 98), Offset(198, 98), hud);
    canvas.drawLine(Offset(104, 7), Offset(104, 19 + 12 * reveal), hud);
    canvas.drawLine(Offset(104, 181), Offset(104, 194), hud);
    canvas.drawCircle(center, 43 * reveal, hud);
    _drawBracket(canvas, const Rect.fromLTWH(12, 10, 176, 178), 15, hud);

    final wire = Paint()
      ..color = const Color(0xFFFAF3E0).withOpacity(.72 * opacity)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.8
      ..strokeJoin = StrokeJoin.miter
      ..strokeCap = StrokeCap.square;
    final metrics = _outerPath.computeMetrics().toList();
    if (metrics.isNotEmpty) {
      canvas.drawPath(
          metrics.first.extractPath(0, metrics.first.length * progress), wire);
    }
    final node = Paint()
      ..color = const Color(0xFFFAF3E0).withOpacity(.8 * opacity)
      ..style = PaintingStyle.fill;
    for (var i = 0; i < _anchors.length; i++) {
      if (progress >= i / (_anchors.length - 1))
        canvas.drawCircle(_anchors[i], 2, node);
    }
  }

  void _drawBracket(Canvas canvas, Rect rect, double corner, Paint paint) {
    for (final signX in [-1.0, 1.0]) {
      for (final signY in [-1.0, 1.0]) {
        final x = signX < 0 ? rect.left : rect.right;
        final y = signY < 0 ? rect.top : rect.bottom;
        canvas.drawLine(Offset(x, y + signY * corner), Offset(x, y), paint);
        canvas.drawLine(Offset(x, y), Offset(x + signX * corner, y), paint);
      }
    }
    canvas.drawLine(const Offset(24, 164), const Offset(48, 140), paint);
    canvas.drawLine(const Offset(162, 58), const Offset(184, 36), paint);
  }

  void _drawAssembly(Canvas canvas, double t) {
    final leftT = Curves.easeOutBack.transform(t);
    final rightT = Curves.easeOutBack.transform(t);
    final pillarT = Curves.easeOutExpo.transform(t);
    final lockT =
        Curves.easeOutBack.transform(((t - .58) / .42).clamp(0.0, 1.0));
    _drawPiece(
        canvas, _leftWing, Offset(-72 * (1 - leftT), -12 * (1 - leftT)), t);
    _drawPiece(
        canvas, _rightWing, Offset(72 * (1 - rightT), -12 * (1 - rightT)), t);
    _drawPiece(
      canvas,
      _pillar,
      Offset(0, 112 * (1 - pillarT)),
      t,
      white: true,
    );
    _drawPiece(canvas, _keystone, Offset(0, 26 * (1 - lockT)), lockT);
  }

  void _drawPiece(
    Canvas canvas,
    Path path,
    Offset offset,
    double opacity, {
    bool white = false,
  }) {
    canvas.save();
    canvas.translate(offset.dx, offset.dy);
    final alpha = opacity.clamp(0.0, 1.0).toDouble();
    final shadow = Paint()
      ..color = const Color(0xFF000000).withOpacity(.38 * alpha)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5);
    canvas.save();
    canvas.translate(0, 5);
    canvas.drawPath(path, shadow);
    canvas.restore();

    final fill = Paint()
      ..style = PaintingStyle.fill
      ..shader = ui.Gradient.linear(
        const Offset(36, 20),
        const Offset(170, 180),
        white
            ? const [Colors.white, Color(0xFFFAF3E0)]
            : const [Color(0xFFFAF3E0), Color(0xFFE6D5B8)],
        [0.0, 1.0],
        TileMode.clamp,
      )
      ..colorFilter = ColorFilter.mode(
        Colors.white.withOpacity(alpha),
        BlendMode.modulate,
      );
    canvas.drawPath(path, fill);

    final edge = Paint()
      ..color = Colors.white.withOpacity(.92 * alpha)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.35
      ..strokeJoin = StrokeJoin.miter;
    canvas.drawPath(path, edge);
    final bevel = Paint()
      ..color = const Color(0xFFB99D72).withOpacity(.75 * alpha)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5
      ..strokeJoin = StrokeJoin.miter;
    canvas.drawPath(path, bevel);
    canvas.restore();
  }

  void _drawImpact(Canvas canvas, double t) {
    final eased = Curves.easeOutCubic.transform(t);
    final paint = Paint()
      ..color = const Color(0xFFFAF3E0).withOpacity((1 - t) * .8)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5 * (1 - t) + .5;
    canvas.drawCircle(const Offset(104, 48), 5 + eased * 37, paint);
    final flash = Paint()
      ..color = Colors.white.withOpacity((1 - t) * .72)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12);
    canvas.drawCircle(const Offset(104, 48), 12 * (1 - t), flash);
  }

  void _drawShine(Canvas canvas, double t) {
    canvas.save();
    canvas.clipPath(_outerPath);
    final x = -120 + 420 * Curves.easeInOutCubic.transform(t);
    final shine = Paint()
      ..shader = ui.Gradient.linear(
        Offset(x - 34, 10),
        Offset(x + 34, 186),
        [
          Colors.white.withOpacity(0),
          Colors.white.withOpacity(.58),
          const Color(0xFFFAF3E0).withOpacity(0),
        ],
        const [0, .5, 1],
      );
    canvas.drawRect(const Rect.fromLTWH(0, 0, 200, 200), shine);
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _TidubaTLogoPainter oldDelegate) =>
      oldDelegate.progress != progress;
}
