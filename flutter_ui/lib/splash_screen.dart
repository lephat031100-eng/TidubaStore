import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:vector_math/vector_math_64.dart' show Matrix4;

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

/// Short alias for apps that prefer the generic widget name.
typedef SplashScreen = TidubaSplashScreen;

class _TidubaSplashScreenState extends State<TidubaSplashScreen>
    with TickerProviderStateMixin {
  static const _duration = Duration(milliseconds: 3600);

  late final AnimationController _controller;
  late final AnimationController _breathController;
  late final Animation<double> _logoOpacity;
  late final Animation<double> _logoScale;
  late final Animation<double> _logoTilt;
  late final Animation<double> _titleOpacity;
  late final Animation<Offset> _titleSlide;
  late final Animation<double> _storeOpacity;
  late final Animation<Offset> _storeSlide;
  late final Animation<double> _taglineOpacity;
  late final Animation<Offset> _taglineSlide;
  bool _didComplete = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: _duration);
    _breathController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _logoOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(.22, .32, curve: Curves.easeOut),
    );
    _logoScale = Tween<double>(begin: 1.62, end: 1).animate(CurvedAnimation(
      parent: _controller,
      curve: const Interval(.22, .56, curve: Curves.easeOutBack),
    ));
    _logoTilt = Tween<double>(begin: -.14, end: 0).animate(CurvedAnimation(
      parent: _controller,
      curve: const Interval(.22, .56, curve: Curves.easeOutExpo),
    ));
    _titleOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(.56, .72, curve: Curves.easeOut),
    );
    _titleSlide = _slide(.56, .72);
    _storeOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(.62, .77, curve: Curves.easeOut),
    );
    _storeSlide = _slide(.62, .77);
    _taglineOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(.69, .84, curve: Curves.easeOut),
    );
    _taglineSlide = _slide(.69, .84);
    _playIntro();
  }

  Animation<Offset> _slide(double start, double end) => Tween<Offset>(
        begin: const Offset(0, .22),
        end: Offset.zero,
      ).animate(CurvedAnimation(
        parent: _controller,
        curve: Interval(start, end, curve: Curves.easeOutCubic),
      ));

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

  double _impactShake(double progress) {
    const impactAt = .445;
    final distance = (progress - impactAt).abs();
    if (distance > .035) return 0;
    final strength = 1 - distance / .035;
    return math.sin((progress - impactAt) * 850) * 3 * strength;
  }

  @override
  void dispose() {
    _controller.dispose();
    _breathController.dispose();
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
                Positioned.fill(
                  child: AnimatedBuilder(
                    animation: _controller,
                    builder: (context, _) => CustomPaint(
                      painter: _CornerMeshPainter(progress: _controller.value),
                    ),
                  ),
                ),
                Positioned.fill(
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final compact = constraints.maxHeight < 600;
                      final crestSize = math.min(
                        compact ? 188.0 : 224.0,
                        constraints.maxWidth * .56,
                      );
                      return SingleChildScrollView(
                        child: ConstrainedBox(
                          constraints: BoxConstraints(
                            minHeight: constraints.maxHeight,
                          ),
                          child: Center(
                            child: Padding(
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 24),
                              child: AnimatedBuilder(
                                animation: _controller,
                                builder: (context, child) =>
                                    Transform.translate(
                                  offset: Offset(
                                      _impactShake(_controller.value), 0),
                                  child: child,
                                ),
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    AnimatedBuilder(
                                      animation: Listenable.merge(
                                          [_controller, _breathController]),
                                      builder: (context, _) {
                                        final glow =
                                            .2 + _breathController.value * .27;
                                        final shineProgress =
                                            Curves.easeInOutCubic.transform(
                                                ((_controller.value - .56) /
                                                        .22)
                                                    .clamp(0.0, 1.0));
                                        return Opacity(
                                          opacity: _logoOpacity.value,
                                          child: Transform(
                                            alignment: Alignment.center,
                                            transform: Matrix4.identity()
                                              ..setEntry(3, 2, .0012)
                                              ..rotateX(_logoTilt.value),
                                            child: ScaleTransition(
                                              scale: _logoScale,
                                              child: SizedBox(
                                                width: crestSize,
                                                height: crestSize * .86,
                                                child: Stack(
                                                  alignment: Alignment.center,
                                                  children: [
                                                    Container(
                                                      width: crestSize * .62,
                                                      height: crestSize * .52,
                                                      decoration: BoxDecoration(
                                                        shape: BoxShape.circle,
                                                        gradient:
                                                            RadialGradient(
                                                          colors: [
                                                            const Color(
                                                                    0xFF22D3EE)
                                                                .withOpacity(
                                                                    glow),
                                                            const Color(
                                                                    0xFF38BDF8)
                                                                .withOpacity(
                                                                    glow * .5),
                                                            Colors.transparent,
                                                          ],
                                                        ),
                                                      ),
                                                    ),
                                                    Image.asset(
                                                      'assets/images/tiduba_crest.png',
                                                      width: crestSize,
                                                      height: crestSize * .86,
                                                      fit: BoxFit.contain,
                                                      filterQuality:
                                                          FilterQuality.high,
                                                      errorBuilder:
                                                          (_, __, ___) =>
                                                              const Icon(
                                                        Icons.diamond_outlined,
                                                        size: 120,
                                                        color:
                                                            Color(0xFFB88975),
                                                      ),
                                                    ),
                                                    if (_controller.value >=
                                                            .56 &&
                                                        _controller.value <=
                                                            .78)
                                                      Positioned.fill(
                                                        child: ShaderMask(
                                                          blendMode:
                                                              BlendMode.screen,
                                                          shaderCallback:
                                                              (bounds) =>
                                                                  LinearGradient(
                                                            begin: Alignment(
                                                                -1.5 +
                                                                    3 * shineProgress,
                                                                -1),
                                                            end: Alignment(
                                                                -.5 +
                                                                    3 * shineProgress,
                                                                1),
                                                            colors: [
                                                              Colors
                                                                  .transparent,
                                                              Colors.white
                                                                  .withOpacity(
                                                                      .78),
                                                              Colors
                                                                  .transparent,
                                                            ],
                                                            stops: const [
                                                              0,
                                                              .5,
                                                              1,
                                                            ],
                                                          ).createShader(
                                                                      bounds),
                                                          child: Image.asset(
                                                            'assets/images/tiduba_crest.png',
                                                            width: crestSize,
                                                            height:
                                                                crestSize * .86,
                                                            fit: BoxFit.contain,
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
                                    SizedBox(height: compact ? 8 : 17),
                                    FadeTransition(
                                      opacity: _titleOpacity,
                                      child: SlideTransition(
                                        position: _titleSlide,
                                        child: ShaderMask(
                                          blendMode: BlendMode.srcIn,
                                          shaderCallback: (bounds) =>
                                              const LinearGradient(
                                            colors: [
                                              Color(0xFF64748B),
                                              Color(0xFF94A3B8),
                                              Color(0xFF64748B),
                                            ],
                                          ).createShader(bounds),
                                          child: const Text(
                                            'TIDUBA',
                                            textAlign: TextAlign.center,
                                            style: TextStyle(
                                              color: Colors.white,
                                              fontSize: 34,
                                              height: 1.04,
                                              fontWeight: FontWeight.w900,
                                              letterSpacing: 3.5,
                                            ),
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
                                            fontSize: 18,
                                            height: 1.3,
                                            fontWeight: FontWeight.w500,
                                            letterSpacing: 6.5,
                                          ),
                                        ),
                                      ),
                                    ),
                                    SizedBox(height: compact ? 10 : 16),
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
                                              fontSize: 10.5,
                                              fontWeight: FontWeight.w600,
                                              letterSpacing: 2.2,
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

class _CornerMeshPainter extends CustomPainter {
  const _CornerMeshPainter({required this.progress});

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final fade = (1 - ((progress - .55) / .2).clamp(0.0, 1.0))
        .clamp(0.0, 1.0)
        .toDouble();
    final line = Paint()
      ..color = const Color(0xFF94A3B8).withOpacity(.30 * fade)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final meshPaths = <Path>[
      Path()
        ..moveTo(0, 0)
        ..lineTo(size.width * .27, 0)
        ..lineTo(size.width * .19, size.height * .14)
        ..lineTo(size.width * .06, size.height * .22)
        ..lineTo(0, size.height * .17)
        ..moveTo(size.width * .19, size.height * .14)
        ..lineTo(size.width * .31, size.height * .21)
        ..lineTo(size.width * .06, size.height * .22)
        ..moveTo(size.width * .06, size.height * .22)
        ..lineTo(size.width * .14, size.height * .34)
        ..lineTo(size.width * .19, size.height * .14),
      Path()
        ..moveTo(size.width, 0)
        ..lineTo(size.width * .74, 0)
        ..lineTo(size.width * .83, size.height * .13)
        ..lineTo(size.width * .96, size.height * .20)
        ..lineTo(size.width, size.height * .16)
        ..moveTo(size.width * .83, size.height * .13)
        ..lineTo(size.width * .68, size.height * .22)
        ..lineTo(size.width * .96, size.height * .20)
        ..moveTo(size.width * .96, size.height * .20)
        ..lineTo(size.width * .89, size.height * .34)
        ..lineTo(size.width * .83, size.height * .13),
      Path()
        ..moveTo(0, size.height)
        ..lineTo(size.width * .25, size.height)
        ..lineTo(size.width * .17, size.height * .85)
        ..lineTo(size.width * .05, size.height * .78)
        ..lineTo(0, size.height * .83)
        ..moveTo(size.width * .17, size.height * .85)
        ..lineTo(size.width * .31, size.height * .78)
        ..lineTo(size.width * .05, size.height * .78)
        ..moveTo(size.width * .05, size.height * .78)
        ..lineTo(size.width * .13, size.height * .65)
        ..lineTo(size.width * .17, size.height * .85),
      Path()
        ..moveTo(size.width, size.height)
        ..lineTo(size.width * .75, size.height)
        ..lineTo(size.width * .83, size.height * .85)
        ..lineTo(size.width * .96, size.height * .78)
        ..lineTo(size.width, size.height * .83)
        ..moveTo(size.width * .83, size.height * .85)
        ..lineTo(size.width * .68, size.height * .78)
        ..lineTo(size.width * .96, size.height * .78)
        ..moveTo(size.width * .96, size.height * .78)
        ..lineTo(size.width * .89, size.height * .65)
        ..lineTo(size.width * .83, size.height * .85),
    ];

    final drawProgress = Curves.easeOutCubic
        .transform((progress / .25).clamp(0.0, 1.0).toDouble());
    for (var i = 0; i < meshPaths.length; i++) {
      final metrics = meshPaths[i].computeMetrics();
      for (final metric in metrics) {
        final local = ((drawProgress * 4) - i).clamp(0.0, 1.0);
        if (local > 0) {
          canvas.drawPath(metric.extractPath(0, metric.length * local), line);
        }
      }
    }

    final center = Offset(size.width * .5, size.height * .40);
    final lock = Curves.easeOutCubic
        .transform((progress / .24).clamp(0.0, 1.0).toDouble());
    final reticle = Paint()
      ..color = const Color(0xFF38BDF8).withOpacity(.52 * fade)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    final radius = 54 * (1 - lock) + 5;
    final diamond = Path()
      ..moveTo(center.dx, center.dy - radius)
      ..lineTo(center.dx + radius * .9, center.dy)
      ..lineTo(center.dx, center.dy + radius)
      ..lineTo(center.dx - radius * .9, center.dy)
      ..close();
    final diamondMetric = diamond.computeMetrics().first;
    canvas.drawPath(
        diamondMetric.extractPath(0, diamondMetric.length * lock), reticle);

    final impactT = ((progress - .445) / .12).clamp(0.0, 1.0).toDouble();
    if (impactT > 0 && impactT < 1) {
      final ringPaint = Paint()
        ..color = const Color(0xFF22D3EE).withOpacity((1 - impactT) * .65)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.2 * (1 - impactT) + .3;
      canvas.drawCircle(
          center, 12 + 92 * Curves.easeOutCubic.transform(impactT), ringPaint);
    }

    final starCenter = Offset(size.width * .91, size.height * .87);
    final star = Paint()
      ..color = const Color(0xFF94A3B8).withOpacity(.28 * fade)
      ..style = PaintingStyle.fill;
    final starPath = Path()
      ..moveTo(starCenter.dx, starCenter.dy - 9)
      ..lineTo(starCenter.dx + 2, starCenter.dy - 2)
      ..lineTo(starCenter.dx + 9, starCenter.dy)
      ..lineTo(starCenter.dx + 2, starCenter.dy + 2)
      ..lineTo(starCenter.dx, starCenter.dy + 9)
      ..lineTo(starCenter.dx - 2, starCenter.dy + 2)
      ..lineTo(starCenter.dx - 9, starCenter.dy)
      ..lineTo(starCenter.dx - 2, starCenter.dy - 2)
      ..close();
    canvas.drawPath(starPath, star);
  }

  @override
  bool shouldRepaint(covariant _CornerMeshPainter oldDelegate) =>
      oldDelegate.progress != progress;
}
