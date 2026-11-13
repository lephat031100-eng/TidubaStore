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
  static const _duration = Duration(milliseconds: 4200);

  late final AnimationController _controller;
  late final AnimationController _breathController;
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

    _titleOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(.69, .83, curve: Curves.easeOut),
    );
    _titleSlide = _slide(.69, .83);
    _storeOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(.74, .87, curve: Curves.easeOut),
    );
    _storeSlide = _slide(.74, .87);
    _taglineOpacity = CurvedAnimation(
      parent: _controller,
      curve: const Interval(.80, .92, curve: Curves.easeOut),
    );
    _taglineSlide = _slide(.80, .92);
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
    const impactAt = .619;
    final distance = (progress - impactAt).abs();
    if (distance > .026) return 0;
    final strength = 1 - distance / .026;
    return math.sin((progress - impactAt) * 1050) * 2.5 * strength;
  }

  double _phase(double start, double end, {Curve curve = Curves.linear}) =>
      curve.transform(
        ((_controller.value - start) / (end - start))
            .clamp(0.0, 1.0)
            .toDouble(),
      );

  Widget _crestPiece({
    required _CrestPiece piece,
    required double start,
    required double end,
    required Offset origin,
    required Curve curve,
    required double size,
  }) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final raw = ((_controller.value - start) / (end - start))
            .clamp(0.0, 1.0)
            .toDouble();
        final t = curve.transform(raw);
        return Opacity(
          opacity: raw,
          child: Transform.translate(
            offset: Offset.lerp(origin, Offset.zero, t)!,
            child: Transform.scale(
              scale: .90 + .10 * t,
              child: ClipPath(
                clipper: _CrestPieceClipper(piece),
                child: Image.asset(
                  'assets/images/tiduba_crest.png',
                  width: size,
                  height: size * .86,
                  fit: BoxFit.contain,
                  filterQuality: FilterQuality.high,
                ),
              ),
            ),
          ),
        );
      },
    );
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
                                        final shineProgress = _phase(
                                          .64,
                                          .86,
                                          curve: Curves.easeInOutCubic,
                                        );
                                        final assemble = _phase(
                                          .33,
                                          .67,
                                          curve: Curves.easeOutExpo,
                                        );
                                        final shineActive =
                                            _controller.value >= .64 &&
                                                _controller.value <= .86;
                                        return Transform(
                                          alignment: Alignment.center,
                                          transform: Matrix4.identity()
                                            ..setEntry(3, 2, .0012)
                                            ..rotateX((1 - assemble) * -.035),
                                          child: SizedBox(
                                            width: crestSize,
                                            height: crestSize * .86,
                                            child: Stack(
                                              alignment: Alignment.center,
                                              children: [
                                                Container(
                                                  width: crestSize * .68,
                                                  height: crestSize * .58,
                                                  decoration: BoxDecoration(
                                                    shape: BoxShape.circle,
                                                    gradient: RadialGradient(
                                                      colors: [
                                                        const Color(0xFF22D3EE)
                                                            .withOpacity(glow *
                                                                assemble),
                                                        const Color(0xFF38BDF8)
                                                            .withOpacity(glow *
                                                                assemble *
                                                                .48),
                                                        Colors.transparent,
                                                      ],
                                                    ),
                                                  ),
                                                ),
                                                _crestPiece(
                                                  piece: _CrestPiece.upper,
                                                  start: 1.40 / 4.2,
                                                  end: 2.12 / 4.2,
                                                  origin: const Offset(0, -60),
                                                  curve: Curves.easeOutBack,
                                                  size: crestSize,
                                                ),
                                                _crestPiece(
                                                  piece: _CrestPiece.lower,
                                                  start: 1.58 / 4.2,
                                                  end: 2.34 / 4.2,
                                                  origin: const Offset(0, 60),
                                                  curve: Curves.easeOutExpo,
                                                  size: crestSize,
                                                ),
                                                _crestPiece(
                                                  piece: _CrestPiece.wing,
                                                  start: 1.82 / 4.2,
                                                  end: 2.52 / 4.2,
                                                  origin: const Offset(70, -20),
                                                  curve: Curves.easeOutBack,
                                                  size: crestSize,
                                                ),
                                                _crestPiece(
                                                  piece: _CrestPiece.stem,
                                                  start: 2.04 / 4.2,
                                                  end: 2.80 / 4.2,
                                                  origin: const Offset(-40, 60),
                                                  curve: Curves.easeOutExpo,
                                                  size: crestSize,
                                                ),
                                                Positioned.fill(
                                                  child: CustomPaint(
                                                    painter:
                                                        _CrestBlueprintPainter(
                                                      progress:
                                                          _controller.value,
                                                    ),
                                                  ),
                                                ),
                                                if (shineActive)
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
                                                          Colors.transparent,
                                                          Colors.white
                                                              .withOpacity(.78),
                                                          Colors.transparent,
                                                        ],
                                                        stops: const [0, .5, 1],
                                                      ).createShader(bounds),
                                                      child: Image.asset(
                                                        'assets/images/tiduba_crest.png',
                                                        width: crestSize,
                                                        height: crestSize * .86,
                                                        fit: BoxFit.contain,
                                                      ),
                                                    ),
                                                  ),
                                              ],
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

enum _CrestPiece { upper, lower, wing, stem }

class _CrestPieceClipper extends CustomClipper<Path> {
  const _CrestPieceClipper(this.piece);

  final _CrestPiece piece;

  @override
  Path getClip(Size size) {
    Offset p(double x, double y) => Offset(size.width * x, size.height * y);
    final path = Path();
    switch (piece) {
      case _CrestPiece.upper:
        path
          ..moveTo(p(.03, .42).dx, p(.03, .42).dy)
          ..lineTo(p(.14, .20).dx, p(.14, .20).dy)
          ..lineTo(p(.50, .05).dx, p(.50, .05).dy)
          ..lineTo(p(.68, .22).dx, p(.68, .22).dy)
          ..lineTo(p(.98, .18).dx, p(.98, .18).dy)
          ..lineTo(p(.86, .42).dx, p(.86, .42).dy)
          ..lineTo(p(.95, .52).dx, p(.95, .52).dy)
          ..lineTo(p(.78, .61).dx, p(.78, .61).dy)
          ..lineTo(p(.50, .45).dx, p(.50, .45).dy)
          ..lineTo(p(.24, .61).dx, p(.24, .61).dy)
          ..lineTo(p(.06, .54).dx, p(.06, .54).dy)
          ..close();
      case _CrestPiece.lower:
        path
          ..moveTo(p(.10, .50).dx, p(.10, .50).dy)
          ..lineTo(p(.28, .55).dx, p(.28, .55).dy)
          ..lineTo(p(.50, .43).dx, p(.50, .43).dy)
          ..lineTo(p(.73, .55).dx, p(.73, .55).dy)
          ..lineTo(p(.90, .50).dx, p(.90, .50).dy)
          ..lineTo(p(.80, .73).dx, p(.80, .73).dy)
          ..lineTo(p(.50, .99).dx, p(.50, .99).dy)
          ..lineTo(p(.20, .73).dx, p(.20, .73).dy)
          ..close();
      case _CrestPiece.wing:
        path
          ..moveTo(p(.12, .40).dx, p(.12, .40).dy)
          ..lineTo(p(.87, .34).dx, p(.87, .34).dy)
          ..lineTo(p(.99, .49).dx, p(.99, .49).dy)
          ..lineTo(p(.78, .63).dx, p(.78, .63).dy)
          ..lineTo(p(.60, .56).dx, p(.60, .56).dy)
          ..lineTo(p(.50, .49).dx, p(.50, .49).dy)
          ..lineTo(p(.39, .56).dx, p(.39, .56).dy)
          ..lineTo(p(.20, .63).dx, p(.20, .63).dy)
          ..lineTo(p(.04, .50).dx, p(.04, .50).dy)
          ..close();
      case _CrestPiece.stem:
        path
          ..moveTo(p(.39, .43).dx, p(.39, .43).dy)
          ..lineTo(p(.62, .43).dx, p(.62, .43).dy)
          ..lineTo(p(.62, .72).dx, p(.62, .72).dy)
          ..lineTo(p(.50, .99).dx, p(.50, .99).dy)
          ..lineTo(p(.38, .72).dx, p(.38, .72).dy)
          ..close();
    }
    return path;
  }

  @override
  bool shouldReclip(covariant _CrestPieceClipper oldClipper) =>
      oldClipper.piece != piece;
}

class _CrestBlueprintPainter extends CustomPainter {
  const _CrestBlueprintPainter({required this.progress});

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final fade = (1 - ((progress - .34) / .34).clamp(0.0, 1.0))
        .clamp(0.0, 1.0)
        .toDouble();
    if (fade <= 0) return;
    Offset p(double x, double y) => Offset(size.width * x, size.height * y);
    final paths = <(Path, Color)>[
      (
        Path()
          ..moveTo(p(.50, .04).dx, p(.50, .04).dy)
          ..lineTo(p(.68, .22).dx, p(.68, .22).dy)
          ..lineTo(p(.98, .18).dx, p(.98, .18).dy)
          ..lineTo(p(.84, .43).dx, p(.84, .43).dy)
          ..lineTo(p(.96, .53).dx, p(.96, .53).dy)
          ..lineTo(p(.75, .67).dx, p(.75, .67).dy)
          ..lineTo(p(.50, .98).dx, p(.50, .98).dy)
          ..lineTo(p(.25, .67).dx, p(.25, .67).dy)
          ..lineTo(p(.04, .53).dx, p(.04, .53).dy)
          ..lineTo(p(.16, .43).dx, p(.16, .43).dy)
          ..lineTo(p(.02, .18).dx, p(.02, .18).dy)
          ..lineTo(p(.32, .22).dx, p(.32, .22).dy)
          ..close(),
        const Color(0xFFC89F86),
      ),
      (
        Path()
          ..moveTo(p(.32, .22).dx, p(.32, .22).dy)
          ..lineTo(p(.50, .10).dx, p(.50, .10).dy)
          ..lineTo(p(.68, .22).dx, p(.68, .22).dy)
          ..lineTo(p(.50, .40).dx, p(.50, .40).dy)
          ..close(),
        const Color(0xFF06B6D4),
      ),
      (
        Path()
          ..moveTo(p(.13, .47).dx, p(.13, .47).dy)
          ..lineTo(p(.31, .38).dx, p(.31, .38).dy)
          ..lineTo(p(.70, .38).dx, p(.70, .38).dy)
          ..lineTo(p(.89, .47).dx, p(.89, .47).dy)
          ..lineTo(p(.77, .61).dx, p(.77, .61).dy)
          ..lineTo(p(.60, .54).dx, p(.60, .54).dy)
          ..lineTo(p(.50, .48).dx, p(.50, .48).dy)
          ..lineTo(p(.39, .54).dx, p(.39, .54).dy)
          ..lineTo(p(.22, .61).dx, p(.22, .61).dy)
          ..close(),
        const Color(0xFFC89F86),
      ),
      (
        Path()
          ..moveTo(p(.39, .44).dx, p(.39, .44).dy)
          ..lineTo(p(.61, .44).dx, p(.61, .44).dy)
          ..lineTo(p(.61, .73).dx, p(.61, .73).dy)
          ..lineTo(p(.50, .94).dx, p(.50, .94).dy)
          ..lineTo(p(.39, .73).dx, p(.39, .73).dy)
          ..close(),
        const Color(0xFF06B6D4),
      ),
      (
        Path()
          ..moveTo(p(.20, .52).dx, p(.20, .52).dy)
          ..lineTo(p(.50, .70).dx, p(.50, .70).dy)
          ..lineTo(p(.80, .52).dx, p(.80, .52).dy),
        const Color(0xFF06B6D4),
      ),
    ];
    final sketch = Curves.easeOutCubic
        .transform((progress / (1.5 / 4.2)).clamp(0.0, 1.0).toDouble());

    for (var index = 0; index < paths.length; index++) {
      final (path, color) = paths[index];
      final metric = path.computeMetrics().first;
      final t = ((sketch * paths.length) - index).clamp(0.0, 1.0).toDouble();
      if (t <= 0) continue;
      final trace = metric.extractPath(0, metric.length * t);
      final glow = Paint()
        ..color = color.withOpacity(.24 * fade)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 5
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
      final stroke = Paint()
        ..color = color.withOpacity(.88 * fade)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.35
        ..strokeJoin = StrokeJoin.round
        ..strokeCap = StrokeCap.round;
      canvas.drawPath(trace, glow);
      canvas.drawPath(trace, stroke);
      final tangent = metric.getTangentForOffset(metric.length * t);
      if (tangent != null && t < 1) {
        final tipGlow = Paint()
          ..color = color.withOpacity(.65 * fade)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
        final tip = Paint()..color = Colors.white.withOpacity(.95 * fade);
        canvas.drawCircle(tangent.position, 4, tipGlow);
        canvas.drawCircle(tangent.position, 1.8, tip);
      }
    }

    final ticks = Paint()
      ..color = const Color(0xFFC89F86).withOpacity(.62 * fade)
      ..strokeWidth = 1;
    for (final point in [p(.15, .25), p(.85, .25), p(.18, .74), p(.82, .74)]) {
      canvas.drawLine(
          point - const Offset(3, 0), point + const Offset(3, 0), ticks);
      canvas.drawLine(
          point - const Offset(0, 3), point + const Offset(0, 3), ticks);
    }

    final impact = ((progress - .619) / .15).clamp(0.0, 1.0).toDouble();
    if (impact > 0 && impact < 1) {
      final ring = Paint()
        ..color = const Color(0xFF22D3EE).withOpacity((1 - impact) * .68)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.1 * (1 - impact) + .3;
      canvas.drawCircle(p(.5, .48), size.width * (.04 + .46 * impact), ring);
    }
  }

  @override
  bool shouldRepaint(covariant _CrestBlueprintPainter oldDelegate) =>
      oldDelegate.progress != progress;
}

class _CornerMeshPainter extends CustomPainter {
  const _CornerMeshPainter({required this.progress});

  final double progress;

  @override
  void paint(Canvas canvas, Size size) {
    final line = Paint()
      ..color = const Color(0xFF94A3B8).withOpacity(.30)
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

    final starCenter = Offset(size.width * .91, size.height * .87);
    final star = Paint()
      ..color = const Color(0xFF94A3B8).withOpacity(.28)
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
