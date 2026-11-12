import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Tiduba authentication screen inspired by the supplied mobile UI video.
///
/// The page is intentionally self-contained so it can be mounted in an
/// existing Flutter app without adding packages. Pass callbacks to connect it
/// to the app's current authentication flow.
enum AuthMode { signIn, signUp }

class TidubaAuthPage extends StatefulWidget {
  const TidubaAuthPage({
    super.key,
    this.onLogin,
    this.onRegister,
    this.onForgotPassword,
  });

  final ValueChanged<Map<String, String>>? onLogin;
  final ValueChanged<Map<String, String>>? onRegister;
  final VoidCallback? onForgotPassword;

  @override
  State<TidubaAuthPage> createState() => _TidubaAuthPageState();
}

class _TidubaAuthPageState extends State<TidubaAuthPage>
    with SingleTickerProviderStateMixin {
  static const _ink = Color(0xFF111827);
  static const _muted = Color(0xFF667085);
  static const _blue = Color(0xFF3478F6);
  static const _line = Color(0xFFE5E8EF);
  static const _field = Color(0xFFF5F6F8);
  static const _night = Color(0xFF0B101A);

  AuthMode _mode = AuthMode.signIn;
  bool _hidePassword = true;
  bool _rememberMe = true;
  final _formKey = GlobalKey<FormState>();
  final _loginUser = TextEditingController();
  final _loginPassword = TextEditingController();
  final _registerName = TextEditingController();
  final _registerEmail = TextEditingController();
  final _registerPhone = TextEditingController();
  final _registerPassword = TextEditingController();
  late final AnimationController _intro;

  @override
  void initState() {
    super.initState();
    _intro = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 520),
    )..forward();
  }

  @override
  void dispose() {
    _intro.dispose();
    _loginUser.dispose();
    _loginPassword.dispose();
    _registerName.dispose();
    _registerEmail.dispose();
    _registerPhone.dispose();
    _registerPassword.dispose();
    super.dispose();
  }

  void _changeMode(AuthMode mode) {
    if (_mode == mode) return;
    HapticFeedback.selectionClick();
    _formKey.currentState?.reset();
    setState(() => _mode = mode);
  }

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.of(context);
    final horizontalPadding = media.size.width < 360 ? 18.0 : 24.0;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
        systemNavigationBarColor: Color(0xFFFFFEFC),
        systemNavigationBarIconBrightness: Brightness.dark,
      ),
      child: Scaffold(
        resizeToAvoidBottomInset: true,
        backgroundColor: _night,
        body: DecoratedBox(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFF151B28), _night, Color(0xFF090D14)],
            ),
          ),
          child: SafeArea(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final compact =
                    constraints.maxHeight < 740 || constraints.maxWidth < 360;
                return SingleChildScrollView(
                  keyboardDismissBehavior:
                      ScrollViewKeyboardDismissBehavior.onDrag,
                  physics: const ClampingScrollPhysics(),
                  padding: EdgeInsets.fromLTRB(
                    horizontalPadding,
                    compact ? 12 : 22,
                    horizontalPadding,
                    compact ? 18 : 28,
                  ),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 460),
                      child: FadeTransition(
                        opacity: CurvedAnimation(
                          parent: _intro,
                          curve: Curves.easeOut,
                        ),
                        child: SlideTransition(
                          position: Tween<Offset>(
                            begin: const Offset(0, .035),
                            end: Offset.zero,
                          ).animate(CurvedAnimation(
                            parent: _intro,
                            curve: Curves.easeOutCubic,
                          )),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              _buildHero(compact),
                              SizedBox(height: compact ? 20 : 30),
                              _buildFormCard(compact),
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
        ),
      ),
    );
  }

  Widget _buildHero(bool compact) {
    final isSignIn = _mode == AuthMode.signIn;
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: 8, vertical: compact ? 4 : 8),
      child: Column(
        children: [
          Container(
            width: compact ? 44 : 50,
            height: compact ? 44 : 50,
            decoration: BoxDecoration(
              color: const Color(0xFF1C2432),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF303A4A)),
            ),
            child: const Icon(Icons.camera_alt_rounded, color: Colors.white),
          ),
          const SizedBox(height: 10),
          const Text(
            'TIDUBA STORE',
            style: TextStyle(
              color: Color(0xFFB9C2D0),
              fontSize: 10,
              fontWeight: FontWeight.w700,
              letterSpacing: 2.4,
            ),
          ),
          SizedBox(height: compact ? 8 : 12),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 220),
            child: Text(
              isSignIn ? 'Chào mừng trở lại.' : 'Tạo tài khoản.',
              key: ValueKey(isSignIn),
              textAlign: TextAlign.center,
              style: TextStyle(
                fontFamily: 'serif',
                color: Colors.white,
                fontSize: compact ? 27 : 32,
                fontWeight: FontWeight.w700,
                letterSpacing: -.6,
              ),
            ),
          ),
          const SizedBox(height: 6),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 220),
            child: Text(
              isSignIn
                  ? 'Đăng nhập để tiếp tục thuê thiết bị yêu thích.'
                  : 'Tạo tài khoản Tiduba Store trong vài bước.',
              key: ValueKey('subtitle-$isSignIn'),
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Color(0xFFABB4C2),
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFormCard(bool compact) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFFFFEFC),
        borderRadius: BorderRadius.circular(28),
        boxShadow: const [
          BoxShadow(
            color: Color(0x55000000),
            blurRadius: 32,
            offset: Offset(0, 14),
          ),
        ],
      ),
      padding: EdgeInsets.fromLTRB(
        compact ? 18 : 24,
        compact ? 18 : 22,
        compact ? 18 : 24,
        compact ? 20 : 24,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildModeSwitch(),
            SizedBox(height: compact ? 18 : 22),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 240),
              switchInCurve: Curves.easeOutCubic,
              switchOutCurve: Curves.easeInCubic,
              child: _mode == AuthMode.signIn
                  ? _buildSignInForm(compact)
                  : _buildSignUpForm(compact),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildModeSwitch() {
    final isSignIn = _mode == AuthMode.signIn;
    return Container(
      height: 48,
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: const Color(0xFFF0F1F4),
        borderRadius: BorderRadius.circular(15),
      ),
      child: Row(
        children: [
          _modeButton('Đăng nhập', AuthMode.signIn, isSignIn),
          _modeButton('Đăng ký', AuthMode.signUp, !isSignIn),
        ],
      ),
    );
  }

  Widget _modeButton(String label, AuthMode mode, bool selected) {
    return Expanded(
      child: Semantics(
        button: true,
        selected: selected,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () => _changeMode(mode),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOut,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: selected ? _ink : Colors.transparent,
              borderRadius: BorderRadius.circular(11),
            ),
            child: Text(
              label,
              style: TextStyle(
                color: selected ? Colors.white : _muted,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSignInForm(bool compact) {
    return Column(
      key: const ValueKey('sign-in-form'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _buildField(
          controller: _loginUser,
          label: 'Email hoặc tên đăng nhập',
          hint: 'Nhập email hoặc tên đăng nhập',
          icon: Icons.mail_outline_rounded,
          keyboardType: TextInputType.emailAddress,
          autofillHints: const [AutofillHints.username, AutofillHints.email],
          validator: (value) => (value == null || value.trim().isEmpty)
              ? 'Vui lòng nhập email hoặc tên đăng nhập.'
              : null,
        ),
        SizedBox(height: compact ? 14 : 17),
        _buildField(
          controller: _loginPassword,
          label: 'Mật khẩu',
          hint: 'Nhập mật khẩu',
          icon: Icons.lock_outline_rounded,
          obscureText: _hidePassword,
          autofillHints: const [AutofillHints.password],
          textInputAction: TextInputAction.done,
          suffix: _visibilityButton(),
          validator: (value) => (value == null || value.isEmpty)
              ? 'Vui lòng nhập mật khẩu.'
              : null,
        ),
        const SizedBox(height: 12),
        _buildRememberRow(),
        SizedBox(height: compact ? 18 : 22),
        _primaryButton(
          label: 'Đăng nhập',
          icon: Icons.arrow_forward_rounded,
          onPressed: _submitLogin,
        ),
        const SizedBox(height: 18),
        _accountSwitch(
          prompt: 'Chưa có tài khoản?',
          action: 'Đăng ký ngay',
          onTap: () => _changeMode(AuthMode.signUp),
        ),
      ],
    );
  }

  Widget _buildSignUpForm(bool compact) {
    return Column(
      key: const ValueKey('sign-up-form'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _buildField(
          controller: _registerName,
          label: 'Họ và tên',
          hint: 'Nguyễn Văn A',
          icon: Icons.person_outline_rounded,
          textCapitalization: TextCapitalization.words,
          autofillHints: const [AutofillHints.name],
          validator: (value) => (value == null || value.trim().isEmpty)
              ? 'Vui lòng nhập họ và tên.'
              : null,
        ),
        const SizedBox(height: 12),
        _buildField(
          controller: _registerEmail,
          label: 'Email',
          hint: 'ban@email.com',
          icon: Icons.mail_outline_rounded,
          keyboardType: TextInputType.emailAddress,
          autofillHints: const [AutofillHints.email],
          validator: (value) => (value == null || !value.contains('@'))
              ? 'Vui lòng nhập email hợp lệ.'
              : null,
        ),
        const SizedBox(height: 12),
        _buildField(
          controller: _registerPhone,
          label: 'Số điện thoại',
          hint: '09xxxxxxxx',
          icon: Icons.phone_iphone_rounded,
          keyboardType: TextInputType.phone,
          autofillHints: const [AutofillHints.telephoneNumber],
          validator: (value) => (value == null || value.trim().isEmpty)
              ? 'Vui lòng nhập số điện thoại.'
              : null,
        ),
        const SizedBox(height: 12),
        _buildField(
          controller: _registerPassword,
          label: 'Mật khẩu',
          hint: 'Tối thiểu 6 ký tự',
          icon: Icons.lock_outline_rounded,
          obscureText: _hidePassword,
          autofillHints: const [AutofillHints.newPassword],
          suffix: _visibilityButton(),
          validator: (value) => (value == null || value.length < 6)
              ? 'Mật khẩu cần có ít nhất 6 ký tự.'
              : null,
        ),
        SizedBox(height: compact ? 18 : 22),
        _primaryButton(
          label: 'Tạo tài khoản',
          icon: Icons.check_rounded,
          onPressed: _submitRegister,
        ),
        const SizedBox(height: 16),
        _accountSwitch(
          prompt: 'Đã có tài khoản?',
          action: 'Đăng nhập',
          onTap: () => _changeMode(AuthMode.signIn),
        ),
      ],
    );
  }

  Widget _buildRememberRow() {
    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      runSpacing: 6,
      children: [
        InkWell(
          onTap: () => setState(() => _rememberMe = !_rememberMe),
          borderRadius: BorderRadius.circular(8),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 2),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                SizedBox(
                  width: 24,
                  height: 24,
                  child: Checkbox(
                    value: _rememberMe,
                    activeColor: _blue,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(5),
                    ),
                    onChanged: (value) =>
                        setState(() => _rememberMe = value ?? false),
                  ),
                ),
                const SizedBox(width: 7),
                const Text(
                  'Ghi nhớ đăng nhập',
                  style: TextStyle(
                    color: Color(0xFF475467),
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
        TextButton(
          onPressed: widget.onForgotPassword,
          style: TextButton.styleFrom(
            foregroundColor: _blue,
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
            minimumSize: const Size(48, 40),
            tapTargetSize: MaterialTapTargetSize.padded,
          ),
          child: const Text(
            'Quên mật khẩu?',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
          ),
        ),
      ],
    );
  }

  Widget _buildField({
    required TextEditingController controller,
    required String label,
    required String hint,
    required IconData icon,
    String? Function(String?)? validator,
    TextInputType? keyboardType,
    TextInputAction? textInputAction,
    TextCapitalization textCapitalization = TextCapitalization.none,
    List<String>? autofillHints,
    bool obscureText = false,
    Widget? suffix,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 2, bottom: 7),
          child: Text(
            label,
            style: const TextStyle(
              color: _ink,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        TextFormField(
          controller: controller,
          validator: validator,
          keyboardType: keyboardType,
          textInputAction: textInputAction ?? TextInputAction.next,
          textCapitalization: textCapitalization,
          autofillHints: autofillHints,
          obscureText: obscureText,
          enableSuggestions: !obscureText,
          autocorrect: !obscureText,
          style: const TextStyle(
            color: _ink,
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: const TextStyle(
              color: Color(0xFF98A2B3),
              fontSize: 13,
              fontWeight: FontWeight.w400,
            ),
            prefixIcon: Icon(icon, color: _muted, size: 19),
            suffixIcon: suffix,
            filled: true,
            fillColor: _field,
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 15),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: _line),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: _line),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: _blue, width: 1.5),
            ),
            errorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: Color(0xFFD92D20)),
            ),
            focusedErrorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(color: Color(0xFFD92D20), width: 1.5),
            ),
            errorStyle: const TextStyle(
              color: Color(0xFFB42318),
              fontSize: 11,
              height: 1.3,
            ),
          ),
        ),
      ],
    );
  }

  Widget _visibilityButton() {
    return IconButton(
      tooltip: _hidePassword ? 'Hiện mật khẩu' : 'Ẩn mật khẩu',
      onPressed: () => setState(() => _hidePassword = !_hidePassword),
      icon: Icon(
        _hidePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
        color: _muted,
        size: 19,
      ),
      constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
    );
  }

  Widget _primaryButton({
    required String label,
    required IconData icon,
    required VoidCallback onPressed,
  }) {
    return SizedBox(
      height: 50,
      child: ElevatedButton(
        onPressed: onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: _blue,
          foregroundColor: Colors.white,
          elevation: 1,
          shadowColor: _blue.withOpacity(.24),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(label),
            const SizedBox(width: 8),
            Icon(icon, size: 18),
          ],
        ),
      ),
    );
  }

  Widget _accountSwitch({
    required String prompt,
    required String action,
    required VoidCallback onTap,
  }) {
    return Wrap(
      alignment: WrapAlignment.center,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Text(prompt, style: const TextStyle(color: _muted, fontSize: 12)),
        TextButton(
          onPressed: onTap,
          style: TextButton.styleFrom(
            foregroundColor: _blue,
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 8),
            minimumSize: const Size(44, 40),
            tapTargetSize: MaterialTapTargetSize.padded,
          ),
          child: Text(
            action,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
          ),
        ),
      ],
    );
  }

  void _submitLogin() {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    widget.onLogin?.call({
      'username': _loginUser.text.trim(),
      'password': _loginPassword.text,
      'remember': _rememberMe.toString(),
    });
  }

  void _submitRegister() {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    widget.onRegister?.call({
      'full_name': _registerName.text.trim(),
      'email': _registerEmail.text.trim(),
      'phone': _registerPhone.text.trim(),
      'password': _registerPassword.text,
    });
  }
}
