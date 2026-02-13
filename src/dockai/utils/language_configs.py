"""
DockAI Language Configuration Module.

This module defines language-specific patterns and detection rules in a 
configuration-driven way, making it easy to add new languages and frameworks
without modifying the core AST analysis logic.

Architecture:
    Language Config → Pattern Matchers → AST Analyzer
                              ↓
                    Extracted Intelligence
"""

from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional
import re


@dataclass
class FrameworkPattern:
    """
    Pattern for detecting a framework from imports or file contents.
    
    Attributes:
        name: Display name of the framework (e.g., "FastAPI", "Express")
        import_patterns: Regex patterns to match in import statements
        content_patterns: Regex patterns to match in file content
        file_indicators: Specific files that indicate this framework
        priority: Detection priority (higher = checked first)
    """
    name: str
    import_patterns: List[str] = field(default_factory=list)
    content_patterns: List[str] = field(default_factory=list)
    file_indicators: List[str] = field(default_factory=list)
    priority: int = 0


@dataclass
class LanguageConfig:
    """
    Complete configuration for a programming language.
    
    Attributes:
        name: Language name (e.g., "Python", "JavaScript")
        extensions: File extensions for this language
        frameworks: List of detectable frameworks
        env_var_patterns: Regex patterns to match environment variable usage
        port_patterns: Regex patterns to match port bindings
        import_patterns: Regex patterns to extract imports
        entry_point_patterns: Regex patterns to detect entry points
        comment_patterns: Patterns for single-line and multi-line comments
    """
    name: str
    extensions: List[str]
    frameworks: List[FrameworkPattern] = field(default_factory=list)
    env_var_patterns: List[str] = field(default_factory=list)
    port_patterns: List[str] = field(default_factory=list)
    import_patterns: List[str] = field(default_factory=list)
    entry_point_patterns: List[str] = field(default_factory=list)
    comment_patterns: Dict[str, str] = field(default_factory=dict)


# ============================================================================
# PYTHON CONFIGURATION
# ============================================================================

PYTHON_FRAMEWORKS = [
    FrameworkPattern(
        name="FastAPI",
        import_patterns=[r'\bfastapi\b', r'from\s+fastapi\s+import'],
        content_patterns=[r'FastAPI\s*\(', r'@app\.(get|post|put|delete)'],
        priority=10
    ),
    FrameworkPattern(
        name="Flask",
        import_patterns=[r'\bflask\b', r'from\s+flask\s+import'],
        content_patterns=[r'Flask\s*\(', r'@app\.route'],
        priority=10
    ),
    FrameworkPattern(
        name="Django",
        import_patterns=[r'\bdjango\b', r'from\s+django'],
        file_indicators=["manage.py", "wsgi.py", "asgi.py"],
        priority=10
    ),
    FrameworkPattern(
        name="Starlette",
        import_patterns=[r'\bstarlette\b'],
        priority=8
    ),
    FrameworkPattern(
        name="Tornado",
        import_patterns=[r'\btornado\b'],
        priority=8
    ),
    FrameworkPattern(
        name="aiohttp",
        import_patterns=[r'\baiohttp\b'],
        priority=8
    ),
    FrameworkPattern(
        name="Sanic",
        import_patterns=[r'\bsanic\b'],
        priority=8
    ),
    FrameworkPattern(
        name="Pyramid",
        import_patterns=[r'\bpyramid\b'],
        priority=7
    ),
    FrameworkPattern(
        name="Bottle",
        import_patterns=[r'\bbottle\b'],
        priority=7
    ),
    FrameworkPattern(
        name="Falcon",
        import_patterns=[r'\bfalcon\b'],
        priority=7
    ),
    FrameworkPattern(
        name="Litestar",
        import_patterns=[r'\blitestar\b'],
        priority=7
    ),
    FrameworkPattern(
        name="Quart",
        import_patterns=[r'\bquart\b'],
        priority=7
    ),
    FrameworkPattern(
        name="Streamlit",
        import_patterns=[r'\bstreamlit\b'],
        content_patterns=[r'st\.'],
        priority=9
    ),
    FrameworkPattern(
        name="Gradio",
        import_patterns=[r'\bgradio\b'],
        priority=8
    ),
    FrameworkPattern(
        name="Dash",
        import_patterns=[r'\bdash\b'],
        priority=7
    ),
    FrameworkPattern(
        name="Uvicorn",
        import_patterns=[r'\buvicorn\b'],
        priority=6
    ),
    FrameworkPattern(
        name="Gunicorn",
        import_patterns=[r'\bgunicorn\b'],
        priority=6
    ),
    FrameworkPattern(
        name="Celery",
        import_patterns=[r'\bcelery\b'],
        priority=7
    ),
    FrameworkPattern(
        name="Dramatiq",
        import_patterns=[r'\bdramatiq\b'],
        priority=6
    ),
]

PYTHON_CONFIG = LanguageConfig(
    name="Python",
    extensions=[".py", ".pyw"],
    frameworks=PYTHON_FRAMEWORKS,
    env_var_patterns=[
        r'os\.getenv\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'os\.environ\s*\[\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'os\.environ\.get\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'environ\s*\[\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'config\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',  # Django-style
    ],
    port_patterns=[
        r'\.run\s*\(\s*[^)]*port\s*=\s*(\d+)',
        r'\.listen\s*\(\s*(\d+)',
        r'\.bind\s*\(\s*[\'"][^\'\"]*[\'"],?\s*(\d+)',
        r'serve\s*\(\s*[^)]*port\s*=\s*(\d+)',
        r'PORT\s*=\s*(\d+)',
    ],
    entry_point_patterns=[
        r'if\s+__name__\s*==\s*[\'"]__main__[\'"]',
        r'def\s+main\s*\(',
        r'app\s*=\s*(?:FastAPI|Flask|Starlette)\s*\(',
    ],
    comment_patterns={
        "single_line": r'#.*$',
        "multi_line": r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'',
    }
)

# ============================================================================
# JAVASCRIPT/TYPESCRIPT CONFIGURATION
# ============================================================================

JS_FRAMEWORKS = [
    FrameworkPattern(
        name="Next.js",
        import_patterns=[r'\bnext\b', r'from\s+[\'"]next'],
        file_indicators=["next.config.js", "next.config.ts", "next.config.mjs"],
        priority=10
    ),
    FrameworkPattern(
        name="NestJS",
        import_patterns=[r'@nestjs/(core|common|platform)', r'from\s+[\'"]@nestjs'],
        content_patterns=[r'NestFactory\.create', r'@Module\s*\(', r'@Controller\s*\('],
        priority=10
    ),
    FrameworkPattern(
        name="Express",
        import_patterns=[r'\bexpress\b', r'from\s+[\'"]express[\'"]'],
        content_patterns=[r'express\s*\(\)', r'app\.listen\s*\('],
        priority=10
    ),
    FrameworkPattern(
        name="Fastify",
        import_patterns=[r'\bfastify\b'],
        content_patterns=[r'fastify\s*\('],
        priority=9
    ),
    FrameworkPattern(
        name="Koa",
        import_patterns=[r'\bkoa\b'],
        priority=9
    ),
    FrameworkPattern(
        name="Hapi",
        import_patterns=[r'@hapi/', r'\bhapi\b'],
        priority=9
    ),
    FrameworkPattern(
        name="React",
        import_patterns=[r'\breact\b', r'from\s+[\'"]react[\'"]'],
        content_patterns=[r'React\.', r'useState\s*\(', r'useEffect\s*\('],
        priority=9
    ),
    FrameworkPattern(
        name="Vue",
        import_patterns=[r'\bvue\b'],
        priority=9
    ),
    FrameworkPattern(
        name="Angular",
        import_patterns=[r'@angular/'],
        priority=9
    ),
    FrameworkPattern(
        name="Svelte",
        import_patterns=[r'\bsvelte\b'],
        priority=9
    ),
    FrameworkPattern(
        name="SvelteKit",
        import_patterns=[r'@sveltejs/kit'],
        file_indicators=["svelte.config.js"],
        priority=10
    ),
    FrameworkPattern(
        name="Nuxt.js",
        import_patterns=[r'\bnuxt\b'],
        file_indicators=["nuxt.config.js", "nuxt.config.ts"],
        priority=10
    ),
    FrameworkPattern(
        name="Remix",
        import_patterns=[r'@remix-run/'],
        priority=9
    ),
    FrameworkPattern(
        name="Astro",
        import_patterns=[r'\bastro\b'],
        file_indicators=["astro.config.mjs"],
        priority=9
    ),
    FrameworkPattern(
        name="Meteor",
        import_patterns=[r'\bmeteor\b'],
        priority=8
    ),
    FrameworkPattern(
        name="AdonisJS",
        import_patterns=[r'@adonisjs/'],
        priority=8
    ),
]

JS_CONFIG = LanguageConfig(
    name="JavaScript",
    extensions=[".js", ".jsx", ".mjs", ".cjs"],
    frameworks=JS_FRAMEWORKS,
    env_var_patterns=[
        r'process\.env\.([A-Z_][A-Z0-9_]*)',
        r'process\.env\[[\'"]([ A-Z_][A-Z0-9_]*)[\'"]',
        r'import\.meta\.env\.([A-Z_][A-Z0-9_]*)',
        r'ConfigService\.get\s*\(\s*[\'"]([ A-Z_][A-Z0-9_]*)[\'"]',  # NestJS
        r'Deno\.env\.get\s*\(\s*[\'"]([ A-Z_][A-Z0-9_]*)[\'"]',  # Deno
    ],
    port_patterns=[
        r'\.listen\s*\(\s*(\d+)',
        r'port:\s*(\d+)',
        r'PORT\s*=\s*(\d+)',
        r'const\s+PORT\s*=\s*(\d+)',
        r'process\.env\.PORT\s*\|\|\s*(\d+)',
        r'\.listen\s*\(\s*process\.env\.PORT\s*\|\|\s*(\d+)',
    ],
    entry_point_patterns=[
        r'app\.listen|server\.listen|createServer',
        r'NestFactory\.create',
        r'fastify\s*\(',
    ],
    import_patterns=[
        r'import\s+(?:[\w\s{},*]+\s+)?from\s+[\'"]([^\'"]+)[\'"]',
        r'import\s+[\'"]([^\'"]+)[\'"]',
        r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
        r'import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
    ],
    comment_patterns={
        "single_line": r'//.*$',
        "multi_line": r'/\*[\s\S]*?\*/',
    }
)

TS_CONFIG = LanguageConfig(
    name="TypeScript",
    extensions=[".ts", ".tsx"],
    frameworks=JS_FRAMEWORKS,  # Same frameworks as JS
    env_var_patterns=JS_CONFIG.env_var_patterns,
    port_patterns=JS_CONFIG.port_patterns,
    entry_point_patterns=JS_CONFIG.entry_point_patterns,
    import_patterns=JS_CONFIG.import_patterns,
    comment_patterns=JS_CONFIG.comment_patterns,
)

# ============================================================================
# GO CONFIGURATION
# ============================================================================

GO_FRAMEWORKS = [
    FrameworkPattern(
        name="Gin",
        import_patterns=[r'github\.com/gin-gonic/gin'],
        content_patterns=[r'gin\.', r'router\.Run'],
        priority=10
    ),
    FrameworkPattern(
        name="Echo",
        import_patterns=[r'github\.com/labstack/echo'],
        priority=10
    ),
    FrameworkPattern(
        name="Fiber",
        import_patterns=[r'github\.com/gofiber/fiber'],
        priority=10
    ),
    FrameworkPattern(
        name="Chi",
        import_patterns=[r'github\.com/go-chi/chi'],
        priority=9
    ),
    FrameworkPattern(
        name="Gorilla Mux",
        import_patterns=[r'github\.com/gorilla/mux'],
        priority=9
    ),
    FrameworkPattern(
        name="Iris",
        import_patterns=[r'github\.com/kataras/iris'],
        priority=8
    ),
    FrameworkPattern(
        name="Beego",
        import_patterns=[r'github\.com/beego/beego'],
        priority=8
    ),
    FrameworkPattern(
        name="Revel",
        import_patterns=[r'github\.com/revel/revel'],
        priority=8
    ),
    FrameworkPattern(
        name="net/http",
        import_patterns=[r'\bnet/http\b'],
        priority=5
    ),
]

GO_CONFIG = LanguageConfig(
    name="Go",
    extensions=[".go"],
    frameworks=GO_FRAMEWORKS,
    env_var_patterns=[
        r'os\.Getenv\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'os\.LookupEnv\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'viper\.GetString\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'viper\.Get\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
    ],
    port_patterns=[
        r'ListenAndServe\s*\(\s*[\'"]?:(\d+)',
        r'\.Run\s*\(\s*[\'"]?:(\d+)',
        r'\.Listen\s*\(\s*[\'"]?:(\d+)',
        r'const\s+\w*[Pp]ort\s*=\s*"?(\d+)',
    ],
    entry_point_patterns=[
        r'func\s+main\s*\(',
    ],
    import_patterns=[
        r'import\s*\(([\s\S]*?)\)',  # Block imports
        r'import\s+[\'"]([^\'"]+)[\'"]',  # Single imports
    ],
    comment_patterns={
        "single_line": r'//.*$',
        "multi_line": r'/\*[\s\S]*?\*/',
    }
)

# ============================================================================
# RUST CONFIGURATION
# ============================================================================

RUST_FRAMEWORKS = [
    FrameworkPattern(
        name="Actix Web",
        import_patterns=[r'actix_web::', r'use\s+actix_web'],
        priority=10
    ),
    FrameworkPattern(
        name="Rocket",
        import_patterns=[r'rocket::', r'use\s+rocket'],
        priority=10
    ),
    FrameworkPattern(
        name="Axum",
        import_patterns=[r'axum::', r'use\s+axum'],
        priority=10
    ),
    FrameworkPattern(
        name="Warp",
        import_patterns=[r'warp::', r'use\s+warp'],
        priority=9
    ),
    FrameworkPattern(
        name="Tide",
        import_patterns=[r'tide::', r'use\s+tide'],
        priority=9
    ),
]

RUST_CONFIG = LanguageConfig(
    name="Rust",
    extensions=[".rs"],
    frameworks=RUST_FRAMEWORKS,
    env_var_patterns=[
        r'env::var\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'std::env::var\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
    ],
    port_patterns=[
        r'\.bind\s*\(\s*[\'"]?[^:]+:(\d+)',
        r'port:\s*(\d+)',
    ],
    entry_point_patterns=[
        r'fn\s+main\s*\(',
        r'#\[actix_web::main\]',
        r'#\[tokio::main\]',
    ],
    comment_patterns={
        "single_line": r'//.*$',
        "multi_line": r'/\*[\s\S]*?\*/',
    }
)

# ============================================================================
# RUBY CONFIGURATION
# ============================================================================

RUBY_FRAMEWORKS = [
    FrameworkPattern(
        name="Ruby on Rails",
        file_indicators=["config.ru", "Gemfile"],
        content_patterns=[r'Rails\.application', r'class\s+\w+\s*<\s*ApplicationController'],
        priority=10
    ),
    FrameworkPattern(
        name="Sinatra",
        import_patterns=[r'require\s+[\'"]sinatra[\'"]'],
        priority=9
    ),
    FrameworkPattern(
        name="Hanami",
        import_patterns=[r'require\s+[\'"]hanami[\'"]'],
        priority=8
    ),
]

RUBY_CONFIG = LanguageConfig(
    name="Ruby",
    extensions=[".rb"],
    frameworks=RUBY_FRAMEWORKS,
    env_var_patterns=[
        r'ENV\s*\[\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'ENV\.fetch\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
    ],
    port_patterns=[
        r'port:\s*(\d+)',
        r'PORT\s*=\s*(\d+)',
    ],
    comment_patterns={
        "single_line": r'#.*$',
    }
)

# ============================================================================
# PHP CONFIGURATION
# ============================================================================

PHP_FRAMEWORKS = [
    FrameworkPattern(
        name="Laravel",
        file_indicators=["artisan", "composer.json"],
        content_patterns=[r'use\s+Illuminate\\\\'],
        priority=10
    ),
    FrameworkPattern(
        name="Symfony",
        file_indicators=["bin/console", "composer.json"],
        content_patterns=[r'use\s+Symfony\\\\'],
        priority=10
    ),
    FrameworkPattern(
        name="CodeIgniter",
        file_indicators=["system/CodeIgniter.php"],
        priority=9
    ),
]

PHP_CONFIG = LanguageConfig(
    name="PHP",
    extensions=[".php"],
    frameworks=PHP_FRAMEWORKS,
    env_var_patterns=[
        r'\$_ENV\s*\[\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'getenv\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'env\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
    ],
    port_patterns=[
        r'PORT\s*=\s*(\d+)',
    ],
    comment_patterns={
        "single_line": r'//.*$',
        "multi_line": r'/\*[\s\S]*?\*/',
    }
)

# ============================================================================
# JAVA CONFIGURATION
# ============================================================================

JAVA_FRAMEWORKS = [
    FrameworkPattern(
        name="Spring Boot",
        import_patterns=[r'org\.springframework\.boot'],
        content_patterns=[r'@SpringBootApplication', r'SpringApplication\.run'],
        priority=10
    ),
    FrameworkPattern(
        name="Micronaut",
        import_patterns=[r'io\.micronaut'],
        priority=9
    ),
    FrameworkPattern(
        name="Quarkus",
        import_patterns=[r'io\.quarkus'],
        priority=9
    ),
]

JAVA_CONFIG = LanguageConfig(
    name="Java",
    extensions=[".java"],
    frameworks=JAVA_FRAMEWORKS,
    env_var_patterns=[
        r'System\.getenv\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
    ],
    port_patterns=[
        r'server\.port\s*=\s*(\d+)',
        r'@Value\s*\(\s*[\'"]?\$\{server\.port:(\d+)\}',
    ],
    entry_point_patterns=[
        r'public\s+static\s+void\s+main\s*\(',
    ],
    comment_patterns={
        "single_line": r'//.*$',
        "multi_line": r'/\*[\s\S]*?\*/',
    }
)

# ============================================================================
# C# / .NET CONFIGURATION
# ============================================================================

CSHARP_FRAMEWORKS = [
    FrameworkPattern(
        name="ASP.NET Core",
        import_patterns=[r'using\s+Microsoft\.AspNetCore'],
        content_patterns=[r'WebApplication\.CreateBuilder', r'\.MapControllers\s*\('],
        priority=10
    ),
    FrameworkPattern(
        name="ASP.NET MVC",
        import_patterns=[r'using\s+System\.Web\.Mvc'],
        priority=9
    ),
    FrameworkPattern(
        name="Blazor",
        import_patterns=[r'using\s+Microsoft\.AspNetCore\.Components'],
        priority=9
    ),
    FrameworkPattern(
        name=".NET Minimal APIs",
        content_patterns=[r'app\.Map(Get|Post|Put|Delete)\s*\('],
        priority=9
    ),
]

CSHARP_CONFIG = LanguageConfig(
    name="C#",
    extensions=[".cs", ".csx"],
    frameworks=CSHARP_FRAMEWORKS,
    env_var_patterns=[
        r'Environment\.GetEnvironmentVariable\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'Environment\[[\'"]([ A-Z_][A-Z0-9_]*)[\'"]',
        r'configuration\[[\'"]([A-Z_][A-Z0-9_:]*)[\'"]',  # .NET configuration
    ],
    port_patterns=[
        r'\.UseUrls\s*\(\s*[\'"]https?://[^:]+:(\d+)',
        r'applicationUrl[\'"]?\s*:\s*[\'"]https?://[^:]+:(\d+)',
    ],
    entry_point_patterns=[
        r'static\s+void\s+Main\s*\(',
        r'static\s+async\s+Task\s+Main\s*\(',
    ],
    comment_patterns={
        "single_line": r'//.*$',
        "multi_line": r'/\*[\s\S]*?\*/',
    }
)

# ============================================================================
# KOTLIN CONFIGURATION
# ============================================================================

KOTLIN_FRAMEWORKS = [
    FrameworkPattern(
        name="Ktor",
        import_patterns=[r'io\.ktor'],
        content_patterns=[r'embeddedServer\s*\(', r'routing\s*\{'],
        priority=10
    ),
    FrameworkPattern(
        name="Spring Boot (Kotlin)",
        import_patterns=[r'org\.springframework\.boot'],
        content_patterns=[r'@SpringBootApplication'],
        priority=10
    ),
    FrameworkPattern(
        name="Micronaut (Kotlin)",
        import_patterns=[r'io\.micronaut'],
        priority=9
    ),
    FrameworkPattern(
        name="Http4k",
        import_patterns=[r'org\.http4k'],
        priority=8
    ),
]

KOTLIN_CONFIG = LanguageConfig(
    name="Kotlin",
    extensions=[".kt", ".kts"],
    frameworks=KOTLIN_FRAMEWORKS,
    env_var_patterns=[
        r'System\.getenv\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'System\.getenv\([\'"]([A-Z_][A-Z0-9_]*)[\'"]',
    ],
    port_patterns=[
        r'embeddedServer\s*\([^,]*,\s*port\s*=\s*(\d+)',
        r'server\.port\s*=\s*(\d+)',
        r'port:\s*(\d+)',
    ],
    entry_point_patterns=[
        r'fun\s+main\s*\(',
    ],
    comment_patterns={
        "single_line": r'//.*$',
        "multi_line": r'/\*[\s\S]*?\*/',
    }
)

# ============================================================================
# SCALA CONFIGURATION
# ============================================================================

SCALA_FRAMEWORKS = [
    FrameworkPattern(
        name="Play Framework",
        import_patterns=[r'play\.api', r'import\s+play\.'],
        priority=10
    ),
    FrameworkPattern(
        name="Akka HTTP",
        import_patterns=[r'akka\.http'],
        priority=10
    ),
    FrameworkPattern(
        name="Http4s",
        import_patterns=[r'org\.http4s'],
        priority=9
    ),
    FrameworkPattern(
        name="Finch",
        import_patterns=[r'io\.finch'],
        priority=8
    ),
]

SCALA_CONFIG = LanguageConfig(
    name="Scala",
    extensions=[".scala", ".sc"],
    frameworks=SCALA_FRAMEWORKS,
    env_var_patterns=[
        r'sys\.env\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'System\.getenv\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
    ],
    port_patterns=[
        r'port\s*=\s*(\d+)',
        r'\.bindAndHandle\s*\([^,]*,\s*[\'"][^\'\"]*[\'"],\s*(\d+)',
    ],
    entry_point_patterns=[
        r'def\s+main\s*\(',
        r'object\s+\w+\s+extends\s+App',
    ],
    comment_patterns={
        "single_line": r'//.*$',
        "multi_line": r'/\*[\s\S]*?\*/',
    }
)

# ============================================================================
# ELIXIR CONFIGURATION
# ============================================================================

ELIXIR_FRAMEWORKS = [
    FrameworkPattern(
        name="Phoenix",
        import_patterns=[r'use\s+Phoenix', r'Phoenix\.'],
        file_indicators=["mix.exs", "config/config.exs"],
        content_patterns=[r'Phoenix\.Endpoint', r'Phoenix\.Router'],
        priority=10
    ),
    FrameworkPattern(
        name="Plug",
        import_patterns=[r'use\s+Plug', r'import\s+Plug'],
        priority=8
    ),
]

ELIXIR_CONFIG = LanguageConfig(
    name="Elixir",
    extensions=[".ex", ".exs"],
    frameworks=ELIXIR_FRAMEWORKS,
    env_var_patterns=[
        r'System\.get_env\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
    ],
    port_patterns=[
        r'port:\s*(\d+)',
        r'http:\s*\[[^\]]*port:\s*(\d+)',
    ],
    entry_point_patterns=[
        r'def\s+start\s*\(',
    ],
    comment_patterns={
        "single_line": r'#.*$',
    }
)

# ============================================================================
# HASKELL CONFIGURATION
# ============================================================================

HASKELL_FRAMEWORKS = [
    FrameworkPattern(
        name="Scotty",
        import_patterns=[r'Web\.Scotty'],
        priority=9
    ),
    FrameworkPattern(
        name="Servant",
        import_patterns=[r'Servant'],
        priority=10
    ),
    FrameworkPattern(
        name="Yesod",
        import_patterns=[r'Yesod'],
        priority=10
    ),
    FrameworkPattern(
        name="Spock",
        import_patterns=[r'Web\.Spock'],
        priority=9
    ),
]

HASKELL_CONFIG = LanguageConfig(
    name="Haskell",
    extensions=[".hs", ".lhs"],
    frameworks=HASKELL_FRAMEWORKS,
    env_var_patterns=[
        r'getEnv\s+[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'lookupEnv\s+[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
    ],
    port_patterns=[
        r'scotty\s+(\d+)',
        r'run\s+(\d+)',
    ],
    entry_point_patterns=[
        r'main\s*::\s*IO',
    ],
    comment_patterns={
        "single_line": r'--.*$',
        "multi_line": r'\{-[\s\S]*?-\}',
    }
)

# ============================================================================
# DART CONFIGURATION
# ============================================================================

DART_FRAMEWORKS = [
    FrameworkPattern(
        name="Flutter",
        import_patterns=[r'package:flutter/'],
        content_patterns=[r'runApp\s*\(', r'MaterialApp\s*\('],
        priority=10
    ),
    FrameworkPattern(
        name="Shelf",
        import_patterns=[r'package:shelf/'],
        priority=9
    ),
    FrameworkPattern(
        name="Angel3",
        import_patterns=[r'package:angel3'],
        priority=8
    ),
]

DART_CONFIG = LanguageConfig(
    name="Dart",
    extensions=[".dart"],
    frameworks=DART_FRAMEWORKS,
    env_var_patterns=[
        r'Platform\.environment\[[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
    ],
    port_patterns=[
        r'\.bind\s*\([^,]*,\s*(\d+)',
        r'port:\s*(\d+)',
    ],
    entry_point_patterns=[
        r'void\s+main\s*\(',
        r'Future<void>\s+main\s*\(',
    ],
    comment_patterns={
        "single_line": r'//.*$',
        "multi_line": r'/\*[\s\S]*?\*/',
    }
)

# ============================================================================
# SWIFT CONFIGURATION
# ============================================================================

SWIFT_FRAMEWORKS = [
    FrameworkPattern(
        name="Vapor",
        import_patterns=[r'import\s+Vapor'],
        content_patterns=[r'Application\s*\(', r'routes\s*\('],
        priority=10
    ),
    FrameworkPattern(
        name="Kitura",
        import_patterns=[r'import\s+Kitura'],
        priority=9
    ),
    FrameworkPattern(
        name="Perfect",
        import_patterns=[r'import\s+Perfect'],
        priority=8
    ),
]

SWIFT_CONFIG = LanguageConfig(
    name="Swift",
    extensions=[".swift"],
    frameworks=SWIFT_FRAMEWORKS,
    env_var_patterns=[
        r'ProcessInfo\.processInfo\.environment\[[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
        r'getenv\s*\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]',
    ],
    port_patterns=[
        r'\.listen\s*\(\s*port:\s*(\d+)',
        r'hostname:\s*[\'"][^\'\"]*[\'"],\s*port:\s*(\d+)',
    ],
    entry_point_patterns=[
        r'@main',
        r'func\s+main\s*\(',
    ],
    comment_patterns={
        "single_line": r'//.*$',
        "multi_line": r'/\*[\s\S]*?\*/',
    }
)

# ============================================================================
# REGISTRY: Map extensions to configurations
# ============================================================================

LANGUAGE_REGISTRY: Dict[str, LanguageConfig] = {}

# Register all languages
for config in [
    PYTHON_CONFIG, 
    JS_CONFIG, 
    TS_CONFIG, 
    GO_CONFIG, 
    RUST_CONFIG, 
    RUBY_CONFIG, 
    PHP_CONFIG, 
    JAVA_CONFIG,
    CSHARP_CONFIG,
    KOTLIN_CONFIG,
    SCALA_CONFIG,
    ELIXIR_CONFIG,
    HASKELL_CONFIG,
    DART_CONFIG,
    SWIFT_CONFIG
]:
    for ext in config.extensions:
        LANGUAGE_REGISTRY[ext.lower()] = config


def get_language_config(file_extension: str) -> Optional[LanguageConfig]:
    """
    Get the language configuration for a file extension.
    
    Args:
        file_extension: File extension (e.g., ".py", ".js")
        
    Returns:
        LanguageConfig if found, None otherwise
    """
    return LANGUAGE_REGISTRY.get(file_extension.lower())


def get_all_supported_extensions() -> List[str]:
    """Get all supported file extensions."""
    return list(LANGUAGE_REGISTRY.keys())


def get_all_supported_languages() -> List[str]:
    """Get all supported language names."""
    return list(set(config.name for config in LANGUAGE_REGISTRY.values()))
