import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// ============================================================================
/// TIDUBA STORE - FLUTTER AUTH PAGE (LUXURY CREAM & WHITE THEME)
/// Thiết kế chuẩn Flutter UI phỏng theo DailyFlutterUI:
/// - Tone màu: Trắng, Kem (#FAF7F2, #F2EDE4, #FFFFFF) kết hợp Dark Hero (#18181B)
/// - Typography: Tương phản cao, chữ sắc nét, không bị chìm với nền
/// - Animation: Trượt mượt mà (Sliding Segmented Control, Page Slide, Scale-in)
/// ============================================================================

enum AuthMode { signIn, signUp }

class TidubaAuthPage extends StatefulWidget {
  const TidubaAuthPage({super.key});

  @override
  State<TidubaAuthPage> createState() => _TidubaAuthPageState();
}

class _TidubaAuthPageState extends State<TidubaAuthPage>
    with SingleTickerProviderStateMixin {
  AuthMode _authMode = AuthMode.signIn;
  bool _obscurePassword = true;
  bool _rememberMe = true;

  late final AnimationController _enterController;
  late final Animation<double> _fadeAnim;
  late final Animation<Offset> _slideAnim;

  // Form Controllers
  final _loginUserCtrl = TextEditingController();
  final _loginPassCtrl = TextEditingController();
  final _regUserCtrl = TextEditingController();
  final _regNameCtrl = TextEditingController();
  final _regEmailCtrl = TextEditingController();
  final _regPhoneCtrl = TextEditingController();
  final _regPassCtrl = TextEditingController();

  // Bảng màu Tone Trắng - Kem chuẩn Luxury & Tương phản cao
  static const Color _bgHero = Color(0xFF18181B);
  static const Color _cardCream = Color(0xFFFAF7F2);
  static const Color _inputCream = Color(0xFFF2EDE4);
  static const Color _borderBeige = Color(0xFFDFD7CC);
  static const Color _textDark = Color(0xFF1C1917);
  static const Color _textMuted = Color(0xFF78716C);
  static const Color _primaryBlue = Color(0xFF2563EB);
  static const Color _accentGold = Color(0xFFFBBF24);

  @override
  void initState() {
    super.initState();
    _enterController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );

    _fadeAnim = CurvedAnimation(
      parent: _enterController,
      curve: Curves.easeOut,
    );

    _slideAnim = Tween<Offset>(
      begin: const Offset(0, 0.08),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _enterController,
      curve: Curves.easeOutCubic,
    ));

    _enterController.forward();
  }

  @override
  void dispose() {
    _enterController.dispose();
    _loginUserCtrl.dispose();
    _loginPassCtrl.dispose();
    _regUserCtrl.dispose();
    _regNameCtrl.dispose();
    _regEmailCtrl.dispose();
    _regPhoneCtrl.dispose();
    _regPassCtrl.dispose();
    super.dispose();
  }

  void _switchTab(AuthMode mode) {
    if (_authMode == mode) return;
    HapticFeedback.lightImpact();
    setState(() {
      _authMode = mode;
    });
  }

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: _bgHero,
        body: SafeArea(
          bottom: false,
          child: Column(
            children: [
              // 1. TOP HERO HEADER (Logo + Welcome Back / Create Account)
              _buildHeroHeader(),

              // 2. BOTTOM SHEET CARD (Tone Trắng Kem)
              Expanded(
                child: SlideTransition(
                  position: _slideAnim,
                  child: FadeTransition(
                    opacity: _fadeAnim,
                    child: Container(
                      width: double.infinity,
                      decoration: const BoxDecoration(
                        color: _cardCream,
                        borderRadius: BorderRadius.vertical(
                          top: Radius.circular(32),
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black26,
                            blurRadius: 30,
                            offset: Offset(0, -10),
                          ),
                        ],
                      ),
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
                        physics: const BouncingScrollPhysics(),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            // SEGMENTED SWITCH (Sign In / Sign Up Pill)
                            _buildSegmentedSwitch(),
                            const SizedBox(height: 20),

                            // FORM NỘI DUNG (Animated CrossFade)
                            AnimatedCrossFade(
                              duration: const Duration(milliseconds: 250),
                              crossFadeState: _authMode == AuthMode.signIn
                                  ? CrossFadeState.showFirst
                                  : CrossFadeState.showSecond,
                              firstChild: _buildSignInForm(),
                              secondChild: _buildSignUpForm(),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Top Hero Header với logo máy ảnh & typography sang trọng
  Widget _buildHeroHeader() {
    final isSignIn = _authMode == AuthMode.signIn;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Column(
        children: [
          // Logo Icon
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF2A2622), Color(0xFF18181B)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: _accentGold.withOpacity(0.35)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.4),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: const Icon(
              Icons.camera_alt_outlined,
              color: _accentGold,
              size: 24,
            ),
          ),
          const SizedBox(height: 10),
          const Text(
            'TIDUBA STORE',
            style: TextStyle(
              color: _accentGold,
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 2,
            ),
          ),
          const SizedBox(height: 4),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 200),
            child: Text(
              isSignIn ? 'Welcome back.' : 'Create account.',
              key: ValueKey(isSignIn),
              style: const TextStyle(
                fontFamily: 'serif',
                color: Colors.white,
                fontSize: 26,
                fontWeight: FontWeight.w900,
                letterSpacing: -0.5,
              ),
            ),
          ),
          const SizedBox(height: 4),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 200),
            child: Text(
              isSignIn
                  ? 'Pick up where you left off — your kits are waiting.'
                  : 'Join Tiduba Store — Start renting premium gear.',
              key: ValueKey(isSignIn),
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Color(0xFFA8A29E),
                fontSize: 12,
                fontWeight: FontWeight.w400,
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Segmented Control Pill chuyển đổi giữa Đăng Nhập & Đăng Ký
  Widget _buildSegmentedSwitch() {
    final isSignIn = _authMode == AuthMode.signIn;
    return Container(
      height: 44,
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: const Color(0xFFE8E2D8),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Stack(
        children: [
          // Sliding indicator
          AnimatedAlign(
            duration: const Duration(milliseconds: 250),
            curve: Curves.fastOutSlowIn,
            alignment: isSignIn ? Alignment.centerLeft : Alignment.centerRight,
            child: FractionallySizedBox(
              widthFactor: 0.5,
              child: Container(
                decoration: BoxDecoration(
                  color: _textDark,
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: const [
                    BoxShadow(
                      color: Colors.black12,
                      blurRadius: 4,
                      offset: Offset(0, 2),
                    ),
                  ],
                ),
              ),
            ),
          ),
          Row(
            children: [
              Expanded(
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => _switchTab(AuthMode.signIn),
                  child: Center(
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.login_rounded,
                          size: 14,
                          color: isSignIn ? Colors.white : _textMuted,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          'Đăng Nhập',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: isSignIn ? Colors.white : _textDark,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              Expanded(
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => _switchTab(AuthMode.signUp),
                  child: Center(
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.person_add_alt_1_rounded,
                          size: 14,
                          color: !isSignIn ? Colors.white : _textMuted,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          'Đăng Ký',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: !isSignIn ? Colors.white : _textDark,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// Form Đăng Nhập
  Widget _buildSignInForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Username / Email Input
        _buildTextField(
          controller: _loginUserCtrl,
          label: 'Tên đăng nhập hoặc Email:',
          hint: 'Email or username',
          prefixIcon: Icons.alternate_email_rounded,
        ),
        const SizedBox(height: 14),

        // Password Input
        _buildTextField(
          controller: _loginPassCtrl,
          label: 'Mật khẩu:',
          hint: 'Password',
          prefixIcon: Icons.lock_outline_rounded,
          obscureText: _obscurePassword,
          suffixIcon: IconButton(
            icon: Icon(
              _obscurePassword
                  ? Icons.visibility_outlined
                  : Icons.visibility_off_outlined,
              color: _textMuted,
              size: 20,
            ),
            onPressed: () {
              setState(() {
                _obscurePassword = !_obscurePassword;
              });
            },
          ),
        ),
        const SizedBox(height: 8),

        // Remember Me & Forgot Password Row
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                SizedBox(
                  width: 24,
                  height: 24,
                  child: Checkbox(
                    value: _rememberMe,
                    activeColor: _primaryBlue,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6),
                    ),
                    onChanged: (val) {
                      setState(() {
                        _rememberMe = val ?? true;
                      });
                    },
                  ),
                ),
                const SizedBox(width: 8),
                const Text(
                  'Ghi nhớ đăng nhập',
                  style: TextStyle(
                    color: Color(0xFF44403C),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            TextButton(
              onPressed: () {
                // Xử lý quên mật khẩu
              },
              style: TextButton.styleFrom(
                padding: EdgeInsets.zero,
                minimumSize: Size.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: const Text(
                'Quên mật khẩu?',
                style: TextStyle(
                  color: _primaryBlue,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 18),

        // Primary Blue Submit Button (chuẩn DailyFlutterUI)
        ElevatedButton(
          onPressed: () {
            // Gọi API đăng nhập Tiduba
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: _primaryBlue,
            foregroundColor: Colors.white,
            elevation: 3,
            shadowColor: _primaryBlue.withOpacity(0.4),
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
          ),
          child: const Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'Đăng Nhập Ngay',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              SizedBox(width: 6),
              Icon(Icons.arrow_forward_rounded, size: 16),
            ],
          ),
        ),
        const SizedBox(height: 18),

        // Divider
        _buildDivider('HOẶC TIẾP TỤC VỚI'),
        const SizedBox(height: 16),

        // Social Buttons
        Row(
          children: [
            Expanded(
              child: _buildSocialButton(
                icon: Icons.g_mobiledata_rounded,
                label: 'Google',
                onPressed: () {},
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildSocialButton(
                icon: Icons.apple_rounded,
                label: 'Apple',
                onPressed: () {},
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),

        // Switch to Sign Up
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'Chưa có tài khoản Tiduba? ',
              style: TextStyle(color: _textMuted, fontSize: 12),
            ),
            GestureDetector(
              onTap: () => _switchTab(AuthMode.signUp),
              child: const Text(
                'Đăng ký ngay',
                style: TextStyle(
                  color: _primaryBlue,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// Form Đăng Ký
  Widget _buildSignUpForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _buildTextField(
          controller: _regUserCtrl,
          label: 'Tên đăng nhập (*):',
          hint: 'nguyenvan_a',
          prefixIcon: Icons.alternate_email_rounded,
        ),
        const SizedBox(height: 12),
        _buildTextField(
          controller: _regNameCtrl,
          label: 'Họ và tên đầy đủ (*):',
          hint: 'Nguyễn Văn A',
          prefixIcon: Icons.person_outline_rounded,
        ),
        const SizedBox(height: 12),
        _buildTextField(
          controller: _regEmailCtrl,
          label: 'Email nhận OTP (*):',
          hint: 'yourname@gmail.com',
          prefixIcon: Icons.mail_outline_rounded,
        ),
        const SizedBox(height: 12),
        _buildTextField(
          controller: _regPhoneCtrl,
          label: 'Số điện thoại (*):',
          hint: '0977078981',
          prefixIcon: Icons.phone_iphone_rounded,
        ),
        const SizedBox(height: 12),
        _buildTextField(
          controller: _regPassCtrl,
          label: 'Mật khẩu (*):',
          hint: '••••••••',
          prefixIcon: Icons.lock_outline_rounded,
          obscureText: _obscurePassword,
        ),
        const SizedBox(height: 18),
        ElevatedButton(
          onPressed: () {},
          style: ElevatedButton.styleFrom(
            backgroundColor: _primaryBlue,
            foregroundColor: Colors.white,
            elevation: 3,
            padding: const EdgeInsets.symmetric(vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
          ),
          child: const Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'Đăng Ký Tài Khoản',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              SizedBox(width: 6),
              Icon(Icons.check_rounded, size: 16),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'Đã có tài khoản Tiduba? ',
              style: TextStyle(color: _textMuted, fontSize: 12),
            ),
            GestureDetector(
              onTap: () => _switchTab(AuthMode.signIn),
              child: const Text(
                'Đăng nhập ngay',
                style: TextStyle(
                  color: _primaryBlue,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  /// Component Input Field tone kem với viền và shadow sắc nét
  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required String hint,
    required IconData prefixIcon,
    bool obscureText = false,
    Widget? suffixIcon,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w700,
            color: Color(0xFF292524),
          ),
        ),
        const SizedBox(height: 6),
        Container(
          decoration: BoxDecoration(
            color: _inputCream,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: _borderBeige),
          ),
          child: TextField(
            controller: controller,
            obscureText: obscureText,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: _textDark,
            ),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: const TextStyle(
                color: _textMuted,
                fontWeight: FontWeight.w400,
              ),
              prefixIcon: Icon(prefixIcon, color: _textMuted, size: 18),
              suffixIcon: suffixIcon,
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 14,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDivider(String text) {
    return Row(
      children: [
        const Expanded(child: Divider(color: _borderBeige, thickness: 1)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Text(
            text,
            style: const TextStyle(
              color: _textMuted,
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.5,
            ),
          ),
        ),
        const Expanded(child: Divider(color: _borderBeige, thickness: 1)),
      ],
    );
  }

  Widget _buildSocialButton({
    required IconData icon,
    required String label,
    required VoidCallback onPressed,
  }) {
    return InkWell(
      onTap: onPressed,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        height: 44,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: _borderBeige),
          boxShadow: const [
            BoxShadow(
              color: Colors.black12,
              blurRadius: 2,
              offset: Offset(0, 1),
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 20, color: _textDark),
            const SizedBox(width: 8),
            Text(
              label,
              style: const TextStyle(
                color: _textDark,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
