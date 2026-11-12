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
  static const _animationDuration = Duration(milliseconds: 3200);
  static const _completionHold = Duration(milliseconds: 800);

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
      curve: const Interval(2.3 / 3.2, 2.95 / 3.2, curve: Curves.easeOut),
    );
    _titleSlide = Tween<Offset>(
      begin: const Offset(0, .18),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: const Interval(2.3 / 3.2, 2.95 / 3.2, curve: Curves.easeOutCubic),
    ));
    _taglineOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(2.72 / 3.2, 1, curve: Curves.easeIn),
    );
    _playIntro();
  }

  Future<void> _playIntro() async {
    await _controller.forward();
    await Future<void>.delayed(_completionHold);
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
        backgroundColor: const Color(0xFFF3EFE6),
        body: DecoratedBox(
          decoration: const BoxDecoration(
            gradient: RadialGradient(
              center: Alignment(0, -.12),
              radius: 1.05,
              colors: [Color(0xFFFFFFFF), Color(0xFFF6F2EA), Color(0xFFF3EFE6)],
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
                                              text: 'tiduba',
                                              style: TextStyle(
                                                  color: Color(0xFF18181B)),
                                            ),
                                            TextSpan(
                                              text: 'Store',
                                              style: TextStyle(
                                                  color: Color(0xFF0284C7)),
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
                                        color: Color(0xFF6B7280),
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
                      foregroundColor: const Color(0xFF18181B),
                      backgroundColor: const Color(0xFFEAE5DC),
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
  static const _strokeEnd = 1.5 / 3.2;
  static const _fillEnd = 2.3 / 3.2;

  static final Path _outerPath = Path()
    ..moveTo(28, 24)
    ..lineTo(190, 24)
    ..lineTo(182, 68)
    ..lineTo(136, 68)
    ..lineTo(112, 176)
    ..lineTo(55, 176)
    ..lineTo(76, 68)
    ..lineTo(20, 68)
    ..close();

  static final Path _crossbarPath = Path()
    ..moveTo(28, 24)
    ..lineTo(190, 24)
    ..lineTo(182, 68)
    ..lineTo(20, 68)
    ..close();

  static final Path _stemPath = Path()
    ..moveTo(76, 66)
    ..lineTo(137, 66)
    ..lineTo(112, 176)
    ..lineTo(55, 176)
    ..close();

  static final List<Path> _guides = [
    _outerPath,
    Path()
      ..moveTo(37, 34)
      ..lineTo(182, 34),
    Path()
      ..moveTo(27, 59)
      ..lineTo(178, 59),
    Path()
      ..moveTo(84, 78)
      ..lineTo(67, 160),
    Path()
      ..moveTo(128, 78)
      ..lineTo(109, 160),
    Path()
      ..moveTo(76, 68)
      ..lineTo(136, 68),
  ];

  static const List<Offset> _anchors = [
    Offset(28, 24),
    Offset(190, 24),
    Offset(182, 68),
    Offset(136, 68),
    Offset(112, 176),
    Offset(55, 176),
    Offset(76, 68),
    Offset(20, 68),
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

    final fillProgress = ((progress - _strokeEnd) / (_fillEnd - _strokeEnd))
        .clamp(0.0, 1.0)
        .toDouble();
    final wireOpacity = 1 - fillProgress;

    if (fillProgress > 0) {
      final fade = Curves.easeInOutCubic.transform(fillProgress);
      final barPaint = Paint()
        ..style = PaintingStyle.fill
        ..shader = ui.Gradient.linear(
          const Offset(20, 24),
          const Offset(190, 68),
          [
            Color.fromRGBO(56, 189, 248, fade),
            Color.fromRGBO(2, 132, 199, fade),
          ],
        );
      canvas.drawPath(_crossbarPath, barPaint);

      final stemPaint = Paint()
        ..style = PaintingStyle.fill
        ..color = const Color(0xFF1E293B).withOpacity(fade);
      canvas.drawPath(_stemPath, stemPaint);
    }

    if (wireOpacity > 0) {
      final strokeProgress = (progress / _strokeEnd).clamp(0.0, 1.0).toDouble();
      final wirePaint = Paint()
        ..color = const Color(0xFF8C857B).withOpacity(.55 * wireOpacity)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round;
      _drawGuides(canvas, strokeProgress, wirePaint);

      final dotPaint = Paint()
        ..color = const Color(0xFF8C857B).withOpacity(.55 * wireOpacity)
        ..style = PaintingStyle.fill;
      for (var i = 0; i < _anchors.length; i++) {
        final revealAt = i / (_anchors.length - 1);
        if (strokeProgress >= revealAt) {
          canvas.drawCircle(_anchors[i], 2.1, dotPaint);
        }
      }
    }

    canvas.restore();
  }

  void _drawGuides(Canvas canvas, double progress, Paint paint) {
    var totalLength = 0.0;
    final metricsByPath = <List<ui.PathMetric>>[];
    for (final path in _guides) {
      final metrics = path.computeMetrics().toList();
      metricsByPath.add(metrics);
      totalLength +=
          metrics.fold<double>(0, (sum, metric) => sum + metric.length);
    }

    var remaining = totalLength * progress;
    for (final metrics in metricsByPath) {
      for (final metric in metrics) {
        if (remaining <= 0) return;
        final segmentLength = math.min(remaining, metric.length).toDouble();
        canvas.drawPath(metric.extractPath(0, segmentLength), paint);
        remaining -= segmentLength;
      }
    }
  }

  @override
  bool shouldRepaint(covariant _TidubaTLogoPainter oldDelegate) =>
      oldDelegate.progress != progress;
}
