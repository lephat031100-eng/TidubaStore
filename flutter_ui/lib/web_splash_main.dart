import 'dart:html' as html;

import 'package:flutter/material.dart';

import 'splash_screen.dart';

void main() {
  runApp(const TidubaWebSplashApp());
}

class TidubaWebSplashApp extends StatelessWidget {
  const TidubaWebSplashApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: TidubaSplashScreen(onAnimationComplete: _notifyParent),
    );
  }
}

void _notifyParent() {
  html.window.parent?.postMessage('tiduba:flutter-splash-complete', '*');
}
