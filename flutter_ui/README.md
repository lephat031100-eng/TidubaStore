# Tiduba Store Flutter UI

This Flutter project contains the Tiduba splash and sign-in screens.

Run the preview locally:

```powershell
flutter run -d chrome
```

The public website uses `lib/web_splash_main.dart`, compiled into
`../static/flutter_splash` and shown as the site's opening overlay. Rebuild it
with:

```powershell
flutter build web --release --no-wasm-dry-run --target lib/web_splash_main.dart --base-href /static/flutter_splash/
```
