"""Stealth configuration for search engine testing.
All pydoll levers in one place — tune here, test with 27_stealth_test.py"""

from dataclasses import dataclass, field


@dataclass
class StealthConfig:
    # --- Browser Launch Args ---
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.7680.154 Safari/537.36"
    )
    window_size: str = "1920,1080"
    headless: bool = True           # False for debugging
    headless_new: bool = False      # --headless=new (modern, harder to detect)
    lang: str = "en-US"
    accept_lang: str = "en-US,en;q=0.9"
    disable_blink_features: str = "AutomationControlled"
    disable_features: list[str] = field(default_factory=lambda: [
        "IsolateOrigins", "site-per-process"
    ])
    webrtc_leak_protection: bool = True
    use_gl: str | None = None       # "swiftshader" for software WebGL, None for real GPU
    no_first_run: bool = True
    no_default_browser_check: bool = True
    disable_reading_from_canvas: bool = False  # canvas fingerprint mitigation

    # --- Browser Preferences ---
    browser_preferences: dict = field(default_factory=lambda: {
        "profile": {
            "exit_type": "Normal",
            "exited_cleanly": True,
        },
        "safebrowsing": {"enabled": True},
        "autofill": {"enabled": True},
        "search": {"suggest_enabled": True},
        "enable_do_not_track": False,
        "credentials_enable_service": True,
        "credentials_enable_autosignin": True,
        "dns_prefetching": {"enabled": True},
    })

    # --- JS Fingerprint Patches ---
    screen_width: int = 1920
    screen_height: int = 1080
    color_depth: int = 30
    pixel_depth: int = 30
    device_pixel_ratio: float = 2.0
    toolbar_height: int = 85
    navigator_languages: list[str] = field(default_factory=lambda: ["en-US", "en"])
    navigator_platform: str = "MacIntel"
    navigator_hardware_concurrency: int = 10
    navigator_device_memory: int = 8
    patch_computed_style: bool = True   # fix headless CSS color detection

    # --- Rate Limiter (per-engine overrides) ---
    rate_limits: dict = field(default_factory=lambda: {
        "google": {"max_requests": 5, "window_seconds": 60},
        "google scholar": {"max_requests": 3, "window_seconds": 60},
        "bing": {"max_requests": 10, "window_seconds": 60},
        "brave": {"max_requests": 8, "window_seconds": 60},
        "startpage": {"max_requests": 10, "window_seconds": 60},
        "mojeek": {"max_requests": 10, "window_seconds": 60},
        "duckduckgo": {"max_requests": 10, "window_seconds": 60},
        "semantic scholar": {"max_requests": 6, "window_seconds": 60},
        "crossref": {"max_requests": 10, "window_seconds": 60},
    })

    # --- Request delay between engines in test scripts ---
    delay_between_engines: float = 3.0
    delay_between_queries: float = 5.0


# Singleton default config
DEFAULT_CONFIG = StealthConfig()


def build_chrome_args(config: StealthConfig) -> list[str]:
    """Convert StealthConfig into list of Chrome CLI arguments."""
    args = [
        f"--user-agent={config.user_agent}",
        f"--window-size={config.window_size}",
        f"--lang={config.lang}",
        f"--accept-lang={config.accept_lang}",
    ]
    if config.disable_blink_features:
        args.append(f"--disable-blink-features={config.disable_blink_features}")
    if config.disable_features:
        args.append(f"--disable-features={','.join(config.disable_features)}")
    if config.no_first_run:
        args.append("--no-first-run")
    if config.no_default_browser_check:
        args.append("--no-default-browser-check")
    if config.use_gl:
        args.append(f"--use-gl={config.use_gl}")
    if config.disable_reading_from_canvas:
        args.append("--disable-reading-from-canvas")
    if config.headless and config.headless_new:
        args.append("--headless=new")
    return args


def build_js_patches(config: StealthConfig) -> str:
    """Generate JS fingerprint patch script from config."""
    avail_height = config.screen_height - 23
    languages_json = str(config.navigator_languages).replace("'", '"')

    parts = [
        "(function() {",
        f"    Object.defineProperty(screen, 'width', {{ get: () => {config.screen_width} }});",
        f"    Object.defineProperty(screen, 'height', {{ get: () => {config.screen_height} }});",
        f"    Object.defineProperty(screen, 'availWidth', {{ get: () => {config.screen_width} }});",
        f"    Object.defineProperty(screen, 'availHeight', {{ get: () => {avail_height} }});",
        f"    Object.defineProperty(screen, 'colorDepth', {{ get: () => {config.color_depth} }});",
        f"    Object.defineProperty(screen, 'pixelDepth', {{ get: () => {config.pixel_depth} }});",
        f"    Object.defineProperty(window, 'devicePixelRatio', {{ get: () => {config.device_pixel_ratio} }});",
        f"    Object.defineProperty(window, 'outerWidth', {{ get: () => window.innerWidth }});",
        f"    Object.defineProperty(window, 'outerHeight', {{ get: () => window.innerHeight + {config.toolbar_height} }});",
        f"    Object.defineProperty(navigator, 'platform', {{ get: () => '{config.navigator_platform}' }});",
        f"    Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {config.navigator_hardware_concurrency} }});",
        f"    Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {config.navigator_device_memory} }});",
        f"    Object.defineProperty(navigator, 'languages', {{ get: () => {languages_json} }});",
    ]

    if config.patch_computed_style:
        parts += [
            "    var _origGCS = window.getComputedStyle;",
            "    window.getComputedStyle = function(element, pseudoElt) {",
            "        var style = _origGCS.apply(this, arguments);",
            "        return new Proxy(style, {",
            "            get: function(target, name) {",
            "                var value = target[name];",
            "                if (name === 'color' && value === 'rgb(255, 0, 0)') {",
            "                    return 'rgb(0, 102, 204)';",
            "                }",
            "                return typeof value === 'function' ? value.bind(target) : value;",
            "            }",
            "        });",
            "    };",
        ]

    parts.append("})();")
    return "\n".join(parts)
