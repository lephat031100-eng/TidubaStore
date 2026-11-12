import 'package:flutter/material.dart';

import 'auth_page.dart';
import 'splash_screen.dart';

void main() {
  runApp(const TidubaFlutterPreviewApp());
}

class TidubaFlutterPreviewApp extends StatelessWidget {
  const TidubaFlutterPreviewApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Tiduba Store',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(useMaterial3: true),
      home: const TidubaSplashScreen(
        nextScreen: TidubaAuthPage(),
      ),
    );
  }
}
