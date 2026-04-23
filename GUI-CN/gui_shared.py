import ctypes
import glob
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
BATCH_DIR = os.path.join(BASE_DIR, "batch")
REQUEST_CACHE_FILE = os.path.join(BASE_DIR, ".sqlmap_gui_last_request.txt")
FRAMEWORK_CONFIG_FILE = os.path.join(PROJECT_ROOT, "config", "framework.yaml")
FRAMEWORK_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "artifacts", "security-assessment")
INTEGRATED_SQLMAP_SCRIPT = os.path.join(PROJECT_ROOT, "sqlmap", "sqlmap.py")
SQLMAP_ENV = {
    **os.environ,
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "PYTHONUNBUFFERED": "1",
}

BG = "#f3f7fc"
SURFACE = "#ffffff"
SURFACE_ALT = "#f8fbff"
SURFACE_MUTED = "#eef4ff"
SURFACE_PANEL = "#e9f1ff"
BORDER = "#d7e3f4"
BORDER_STRONG = "#c0d1ea"
ACCENT = "#2563eb"
ACCENT_SOFT = "#dbeafe"
ACCENT_STRONG = "#1d4ed8"
ACCENT_SUCCESS = "#0f766e"
TEXT = "#0f172a"
TEXT_MUTED = "#64748b"
TEXT_SOFT = "#94a3b8"
DANGER = "#dc2626"

FONT_FAMILIES = {
    "ui": ("Microsoft YaHei UI", "PingFang SC", "Segoe UI", "Helvetica Neue", "Arial"),
    "mono": ("Consolas", "Cascadia Mono", "JetBrains Mono", "Courier New"),
    "text": ("Microsoft YaHei UI", "PingFang SC", "Segoe UI", "Arial"),
}

SCALE_OPTIONS = {
    "90%": 0.92,
    "100%": 1.0,
    "110%": 1.08,
    "125%": 1.18,
    "140%": 1.28,
}

TECHNIQUES = {
    "全部": "BESUTQ",
    "布尔盲注": "B",
    "报错注入": "E",
    "堆叠注入": "S",
    "联合注入": "U",
    "时间盲注": "T",
    "内联查询": "Q",
}

DBMS_OPTIONS = [
    "", "Altibase", "Amazon Redshift", "Apache Derby", "Apache Ignite", "Aurora", "ClickHouse",
    "CockroachDB", "CrateDB", "Cubrid", "Drizzle", "EnterpriseDB", "eXtremeDB", "Firebird",
    "FrontBase", "Greenplum", "H2", "HSQLDB", "IBM DB2", "Informix", "InterSystems Cache",
    "Iris", "MariaDB", "Mckoi", "MemSQL", "Microsoft Access", "Microsoft SQL Server", "MimerSQL",
    "MonetDB", "MySQL", "OpenGauss", "Oracle", "Percona", "PostgreSQL", "Presto",
    "Raima Database Manager", "SAP MaxDB", "SQLite", "Sybase", "TiDB", "Vertica", "Virtuoso",
    "Yellowbrick", "YugabyteDB",
]

TAMPER_PRESETS = {
    "关闭": [],
    "通用绕过": ["between", "randomcase", "space2comment"],
    "编码绕过": ["charencode", "chardoubleencode", "charunicodeencode"],
    "WAF 强化": ["between", "randomcase", "randomcomments", "space2comment", "charencode"],
    "MySQL 定向": ["space2mysqlblank", "space2mysqldash", "versionedkeywords"],
    "MSSQL 定向": ["space2mssqlblank", "space2mssqlhash", "between"],
}

PROFILE_NAMES = ["平衡测试", "深度测试", "WAF 绕过"]

DEFAULT_RUNTIME_FLAGS = [
    "--keep-alive",
    "--parse-errors",
    "--eta",
]

HELP_TEXT = """使用说明

1. 主输入区支持三种内容：
   - 单个 URL：自动使用 -u
   - 原始 HTTP 请求：自动写入临时文件并使用 -r
   - 多个 URL（每行一个）：自动按批量 URL 并发执行

2. 现在不再提供大量零散的请求头字段输入框。
   - 直接把原始数据包粘贴到主输入区即可
   - 也可以将 .txt 请求包拖拽到主输入区
   - 如果要传高级参数，可直接写在“附加参数”里

3. 批量模式：
   - 勾选“批量 URL”后，主输入区按每行一条 URL 执行
   - 勾选“批量请求包”后，会读取 batch 目录中的所有 .txt 文件
   - 选择或拖入多个 .txt 文件时，会自动复制到 batch 目录并切换到批量请求包模式

4. 界面已做精简：
   - 常用项保留在左侧卡片
   - 复杂少用项统一通过“附加参数”补充
   - 右侧保留主输入、命令预览与运行日志
"""

REQUEST_EXAMPLE = """POST /vul/sqli/sqli_id.php HTTP/1.1
Host: 127.0.0.1
User-Agent: Mozilla/5.0
Content-Type: application/x-www-form-urlencoded
Cookie: PHPSESSID=test

id=1&submit=查询
"""

URL_EXAMPLE = "http://127.0.0.1/vul/sqli/sqli_id.php?id=1"

if sys.platform.startswith("win"):
    from ctypes import wintypes

    GWL_WNDPROC = -4
    WM_DROPFILES = 0x0233
    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


def list_tamper_scripts():
    scripts = []
    tamper_dir = os.path.join(PROJECT_ROOT, "sqlmap", "tamper")
    for path in sorted(glob.glob(os.path.join(tamper_dir, "*.py"))):
        name = os.path.splitext(os.path.basename(path))[0]
        if not name.startswith("__"):
            scripts.append(name)
    return scripts


def safe_int(value, default=0, minimum=None, maximum=None):
    try:
        parsed = int(str(value).strip())
    except Exception:
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def split_custom_args(raw_value):
    raw_value = (raw_value or "").strip()
    if not raw_value:
        return []
    try:
        return shlex.split(raw_value, posix=(os.name != "nt"))
    except ValueError:
        return raw_value.split()


def format_command(args):
    args = [str(item) for item in args]
    if os.name == "nt":
        return subprocess.list2cmdline(args)
    return " ".join(shlex.quote(item) for item in args)


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)
    return path


def open_path(path):
    if not os.path.exists(path):
        messagebox.showinfo("提示", f"路径不存在：\n{path}")
        return
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def copy_tree_merge(source_path, dest_path):
    ensure_directory(dest_path)
    for entry in os.listdir(source_path):
        src = os.path.join(source_path, entry)
        dst = os.path.join(dest_path, entry)
        if os.path.isdir(src):
            copy_tree_merge(src, dst)
        else:
            shutil.copy2(src, dst)


def copy_folders_with_log_files(source_path, dest_path):
    if not os.path.isdir(source_path):
        return 0
    ensure_directory(dest_path)
    copied = 0
    for root, _dirs, files in os.walk(source_path):
        if "log" not in files:
            continue
        log_file_path = os.path.join(root, "log")
        if not os.path.getsize(log_file_path):
            continue
        folder_name = os.path.basename(root)
        dest_folder_path = os.path.join(dest_path, folder_name)
        copy_tree_merge(root, dest_folder_path)
        copied += 1
    return copied


def safe_output_name(value):
    text = re.sub(r"[^0-9A-Za-z._-]+", "-", (value or "").strip())
    text = text.strip("-._")
    return text or "run"


def build_framework_output_dir(label=None):
    base_dir = ensure_directory(FRAMEWORK_OUTPUT_DIR)
    if not label:
        return base_dir
    return os.path.join(base_dir, safe_output_name(label))


def read_framework_report_summary(output_dir):
    base_path = Path(output_dir)
    report_files = []
    primary = base_path / "assessment.json"
    if primary.is_file():
        report_files.append(primary)
    if base_path.is_dir():
        report_files.extend(sorted(base_path.glob("*/assessment.json")))

    summary = {
        "reports": 0,
        "findings": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
    seen = set()
    for report_path in report_files:
        normalized = str(report_path.resolve())
        if normalized in seen:
            continue
        seen.add(normalized)
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        summary["reports"] += 1
        for finding in payload.get("findings", []):
            summary["findings"] += 1
            risk_level = str(finding.get("risk_level") or "").lower()
            if risk_level == "high":
                summary["high"] += 1
            elif risk_level == "medium":
                summary["medium"] += 1
            elif risk_level == "low":
                summary["low"] += 1
    return summary


def get_sqlmap_result_dirs():
    output_dir = FRAMEWORK_OUTPUT_DIR
    return output_dir, output_dir


def read_text_file(path):
    for encoding in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as handle:
                return handle.read()
        except Exception:
            continue
    with open(path, "rb") as handle:
        return handle.read().decode("utf-8", errors="replace")


def normalize_request_payload(text):
    if not text:
        return text

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if lines:
        lines[0] = re.sub(r"\s+HTTP/2(?:\.0)?\s*$", " HTTP/1.1", lines[0], flags=re.I)
    return "\r\n".join(lines)


def unique_copy_to_batch(source_path):
    ensure_directory(BATCH_DIR)
    base_name = os.path.basename(source_path)
    target_path = os.path.join(BATCH_DIR, base_name)
    if not os.path.exists(target_path):
        shutil.copy2(source_path, target_path)
        return target_path

    stem, ext = os.path.splitext(base_name)
    index = 1
    while True:
        candidate = os.path.join(BATCH_DIR, f"{stem}_{index}{ext}")
        if not os.path.exists(candidate):
            shutil.copy2(source_path, candidate)
            return candidate
        index += 1


def get_candidate_sqlmap_scripts():
    preferred = [
        INTEGRATED_SQLMAP_SCRIPT,
    ]
    seen = set()
    candidates = []
    for path in preferred:
        normalized = os.path.normpath(path)
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(normalized)
    return candidates


def get_default_sqlmap_script():
    for candidate in get_candidate_sqlmap_scripts():
        if os.path.isfile(candidate):
            return candidate
    return get_candidate_sqlmap_scripts()[0]


def read_sqlmap_version(script_path):
    settings_path = os.path.join(os.path.dirname(script_path), "lib", "core", "settings.py")
    if not os.path.isfile(settings_path):
        return "未知版本"
    try:
        content = read_text_file(settings_path)
    except Exception:
        return "未知版本"
    match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', content, re.M)
    return match.group(1) if match else "未知版本"


class ScrollableFrame(ttk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="Page.TFrame")
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_inner_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)


class SqlmapGuiApp:
    def __init__(self, root, python_command):
        self.root = root
        self.python_command = python_command
        self.tamper_scripts = list_tamper_scripts()
        self.console_queue = queue.Queue()
        self.process = None
        self.batch_processes = set()
        self.process_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.preview_signature = None
        self.status_var = tk.StringVar(value="就绪")
        self.mode_var = tk.StringVar(value="等待输入目标")
        self.profile_var = tk.StringVar(value=PROFILE_NAMES[0])
        self.interactive_input_var = tk.StringVar()
        self.process_accepts_stdin = False
        self.drop_hint_var = tk.StringVar(value="支持直接粘贴数据包，或拖拽 .txt 请求包")
        self.window_scale_var = tk.StringVar(value="100%")
        self._drop_old_proc = None
        self._drop_callback = None
        self._drop_hwnd = None
        self._layout_mode = None
        self._fonts_ready = False
        self._parse_state = None
        self._current_output_db = None
        self._current_output_table = None
        self.output_parse_buffer = ""

        self.create_variables()
        self.setup_window()
        self.setup_fonts()
        self.setup_styles()
        self.build_layout()
        self.enable_drop_support()
        self.start_console_pump()
        self.start_preview_watcher()
        self.root.after(80, lambda: self.apply_responsive_layout("split"))

    def create_variables(self):
        self.level_var = tk.StringVar(value="1")
        self.risk_var = tk.StringVar(value="1")
        self.threads_var = tk.StringVar(value="10")
        self.batch_workers_var = tk.StringVar(value="5")
        self.technique_var = tk.StringVar(value="全部")
        self.dbms_var = tk.StringVar(value="")
        self.sqlmap_script_var = tk.StringVar(value=get_default_sqlmap_script())
        self.sqlmap_version_var = tk.StringVar(value="")
        self.test_parameter_var = tk.StringVar(value="")
        self.skip_parameter_var = tk.StringVar(value="")
        self.param_exclude_var = tk.StringVar(value="")
        self.param_filter_var = tk.StringVar(value="")
        self.prefix_var = tk.StringVar(value="")
        self.suffix_var = tk.StringVar(value="")
        self.string_var = tk.StringVar(value="")
        self.not_string_var = tk.StringVar(value="")
        self.regexp_var = tk.StringVar(value="")
        self.code_var = tk.StringVar(value="")
        self.time_sec_var = tk.StringVar(value="")
        self.union_cols_var = tk.StringVar(value="")
        self.union_char_var = tk.StringVar(value="")
        self.union_from_var = tk.StringVar(value="")
        self.union_values_var = tk.StringVar(value="")
        self.test_filter_var = tk.StringVar(value="")
        self.test_skip_var = tk.StringVar(value="")
        self.custom_db_var = tk.StringVar(value="")
        self.custom_table_var = tk.StringVar(value="")
        self.custom_column_var = tk.StringVar(value="")
        self.custom_param_var = tk.StringVar(value="")
        self.tamper_preset_var = tk.StringVar(value="通用绕过")
        self.reuse_injection_var = tk.BooleanVar(value=True)
        self.detected_technique_codes = []
        self.detected_parameter_name = ""
        self.detected_injection_summary_var = tk.StringVar(value="尚未生成风险结论")
        self.discovered_dbs = []
        self.discovered_tables = {}
        self.discovered_columns = {}
        self.scope_summary_var = tk.StringVar(value="尚未枚举到数据库 / 表 / 列")
        self.current_enum_db = None
        self.current_enum_table = None
        self.current_database_name = ""

        self.current_db_var = tk.BooleanVar(value=False)
        self.current_user_var = tk.BooleanVar(value=False)
        self.dbs_var = tk.BooleanVar(value=False)
        self.tables_var = tk.BooleanVar(value=False)
        self.columns_var = tk.BooleanVar(value=False)
        self.dump_var = tk.BooleanVar(value=False)
        self.dump_all_var = tk.BooleanVar(value=False)
        self.batch_url_var = tk.BooleanVar(value=False)
        self.batch_data_var = tk.BooleanVar(value=False)
        self.batch_var = tk.BooleanVar(value=True)
        self.random_agent_var = tk.BooleanVar(value=True)
        self.force_ssl_var = tk.BooleanVar(value=False)
        self.text_only_var = tk.BooleanVar(value=False)
        self.skip_waf_var = tk.BooleanVar(value=False)
        self.skip_static_var = tk.BooleanVar(value=False)
        self.smart_var = tk.BooleanVar(value=False)
        self.titles_var = tk.BooleanVar(value=False)
        self.skip_heuristics_var = tk.BooleanVar(value=False)
        self.no_cast_var = tk.BooleanVar(value=False)
        self.no_escape_var = tk.BooleanVar(value=False)
        self.invalid_bignum_var = tk.BooleanVar(value=False)
        self.invalid_logical_var = tk.BooleanVar(value=False)
        self.invalid_string_var = tk.BooleanVar(value=False)
        self.flush_session_var = tk.BooleanVar(value=False)

        self.watch_vars = [
            self.level_var, self.risk_var, self.threads_var, self.batch_workers_var,
            self.technique_var, self.dbms_var, self.sqlmap_script_var, self.test_parameter_var,
            self.skip_parameter_var, self.param_exclude_var, self.param_filter_var,
            self.prefix_var, self.suffix_var, self.string_var, self.not_string_var,
            self.regexp_var, self.code_var, self.time_sec_var, self.union_cols_var,
            self.union_char_var, self.union_from_var, self.union_values_var,
            self.test_filter_var, self.test_skip_var,
            self.custom_db_var, self.custom_table_var, self.custom_column_var,
            self.custom_param_var, self.tamper_preset_var,
            self.current_db_var, self.current_user_var, self.dbs_var,
            self.tables_var, self.columns_var, self.dump_var, self.dump_all_var,
            self.batch_url_var, self.batch_data_var, self.batch_var, self.random_agent_var,
            self.force_ssl_var, self.text_only_var, self.skip_waf_var,
            self.skip_static_var, self.smart_var, self.titles_var, self.skip_heuristics_var,
            self.no_cast_var, self.no_escape_var, self.invalid_bignum_var,
            self.invalid_logical_var, self.invalid_string_var, self.flush_session_var,
        ]

    def setup_window(self):
        self.root.title("SQLmap GUI")
        self.root.geometry("1520x960")
        self.root.minsize(1180, 760)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Configure>", self.on_window_resize)

    def resolve_font_family(self, candidates):
        try:
            available = set(tkfont.families())
        except Exception:
            available = set()
        for candidate in candidates:
            if not available or candidate in available:
                return candidate
        return candidates[0]

    def setup_fonts(self):
        self.ui_font_family = self.resolve_font_family(FONT_FAMILIES["ui"])
        self.mono_font_family = self.resolve_font_family(FONT_FAMILIES["mono"])
        self.text_font_family = self.resolve_font_family(FONT_FAMILIES["text"])
        self.font_scale = SCALE_OPTIONS.get(self.window_scale_var.get(), 1.0)
        self.fonts = {
            "title": tkfont.Font(family=self.ui_font_family, size=24, weight="bold"),
            "subtitle": tkfont.Font(family=self.ui_font_family, size=11),
            "section": tkfont.Font(family=self.ui_font_family, size=12, weight="bold"),
            "body": tkfont.Font(family=self.ui_font_family, size=11),
            "small": tkfont.Font(family=self.ui_font_family, size=10),
            "button": tkfont.Font(family=self.ui_font_family, size=11, weight="bold"),
            "button_secondary": tkfont.Font(family=self.ui_font_family, size=11),
            "mono": tkfont.Font(family=self.mono_font_family, size=11),
            "text_area": tkfont.Font(family=self.text_font_family, size=11),
            "badge": tkfont.Font(family=self.ui_font_family, size=10, weight="bold"),
        }
        self.apply_font_scale()
        self.root.option_add("*TCombobox*Listbox.font", self.fonts["body"])
        self._fonts_ready = True

    def apply_font_scale(self):
        scale = SCALE_OPTIONS.get(self.window_scale_var.get(), 1.0)
        self.font_scale = scale
        font_sizes = {
            "title": round(24 * scale),
            "subtitle": round(11 * scale),
            "section": round(12 * scale),
            "body": round(11 * scale),
            "small": round(10 * scale),
            "button": round(11 * scale),
            "button_secondary": round(11 * scale),
            "mono": round(11 * scale),
            "text_area": round(11 * scale),
            "badge": round(10 * scale),
        }
        for name, size in font_sizes.items():
            self.fonts[name].configure(size=max(size, 8))

    def on_scale_change(self, _event=None):
        if not self._fonts_ready:
            return
        self.apply_font_scale()
        self.setup_styles()
        self.refresh_preview(force=True)

    def on_window_resize(self, event):
        if event.widget is not self.root:
            return
        width = max(event.width, self.root.winfo_width())
        layout_mode = "split"
        if layout_mode != self._layout_mode:
            self._layout_mode = layout_mode
            self.apply_responsive_layout(layout_mode)

    def on_close(self):
        self.stop_event.set()
        self.teardown_drop_support()
        self.root.destroy()

    def setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        primary_pad_x = max(12, round(14 * self.font_scale))
        primary_pad_y = max(8, round(10 * self.font_scale))
        secondary_pad_x = max(10, round(12 * self.font_scale))
        secondary_pad_y = max(6, round(8 * self.font_scale))

        style.configure(".", background=BG, foreground=TEXT, font=self.fonts["body"])
        style.configure("Page.TFrame", background=BG)
        style.configure("Header.TFrame", background=BG)
        style.configure("Card.TFrame", background=SURFACE, relief="flat")
        style.configure("Muted.TFrame", background=SURFACE_MUTED, relief="flat")
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=self.fonts["title"])
        style.configure("Subtitle.TLabel", background=BG, foreground=TEXT_MUTED, font=self.fonts["subtitle"])
        style.configure("Section.TLabel", background=SURFACE, foreground=TEXT, font=self.fonts["section"])
        style.configure("Hint.TLabel", background=BG, foreground=TEXT_MUTED, font=self.fonts["small"])
        style.configure("Badge.TLabel", background=SURFACE, foreground=ACCENT_SUCCESS, font=self.fonts["badge"])
        style.configure("Card.TLabelframe", background=SURFACE, borderwidth=1, relief="solid")
        style.configure("Card.TLabelframe.Label", background=SURFACE, foreground=TEXT, font=self.fonts["section"])
        style.configure("Action.TButton", font=self.fonts["button"], padding=(primary_pad_x, primary_pad_y), borderwidth=0)
        style.configure("Ghost.TButton", font=self.fonts["button_secondary"], padding=(secondary_pad_x, secondary_pad_y), borderwidth=0)
        style.configure("TCheckbutton", background=SURFACE, foreground=TEXT, font=self.fonts["body"])
        style.map("TCheckbutton", background=[("active", SURFACE)], foreground=[("active", TEXT)])
        style.configure("TEntry", fieldbackground=SURFACE_ALT, foreground=TEXT, bordercolor=BORDER, insertcolor=TEXT, padding=(10, 8))
        style.configure("TCombobox", fieldbackground=SURFACE_ALT, foreground=TEXT, padding=(10, 8))

    def build_layout(self):
        self.build_header()

        self.body = ttk.Frame(self.root, style="Page.TFrame", padding=(18, 0, 18, 0))
        self.body.pack(fill="both", expand=True)

        self.content_frame = ttk.Frame(self.body, style="Page.TFrame")
        self.content_frame.pack(fill="both", expand=True)

        self.left_panel = ttk.Frame(self.content_frame, style="Page.TFrame")
        self.right_panel = ttk.Frame(self.content_frame, style="Page.TFrame")

        self.build_left_panel(self.left_panel)
        self.build_right_panel(self.right_panel)
        self.apply_responsive_layout("split")

    def build_header(self):
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(20, 16, 20, 12))
        header.pack(fill="x")
        header.columnconfigure(0, weight=1)

        left_controls = ttk.Frame(header, style="Header.TFrame")
        left_controls.grid(row=0, column=0, sticky="w")
        ttk.Label(left_controls, text="预设", style="Hint.TLabel").pack(side="left", padx=(0, 6))
        ttk.Combobox(left_controls, values=PROFILE_NAMES, textvariable=self.profile_var, state="readonly", width=10).pack(side="left", padx=(0, 8))
        ttk.Label(left_controls, text="缩放", style="Hint.TLabel").pack(side="left", padx=(6, 6))
        scale_combo = ttk.Combobox(left_controls, values=list(SCALE_OPTIONS.keys()), textvariable=self.window_scale_var, state="readonly", width=7)
        scale_combo.pack(side="left", padx=(0, 8))
        scale_combo.bind("<<ComboboxSelected>>", self.on_scale_change)
        ttk.Button(left_controls, text="应用预设", style="Ghost.TButton", command=self.apply_profile).pack(side="left", padx=(0, 8))
        ttk.Button(left_controls, text="帮助", style="Ghost.TButton", command=self.show_help).pack(side="left")

        right_controls = ttk.Frame(header, style="Header.TFrame")
        right_controls.grid(row=0, column=1, sticky="e")
        ttk.Button(right_controls, text="开始运行", style="Action.TButton", command=self.start_run).pack(side="left", padx=(0, 8))
        ttk.Button(right_controls, text="停止运行", style="Action.TButton", command=self.stop_run).pack(side="left")

    def apply_responsive_layout(self, layout_mode):
        self.left_panel.pack_forget()
        self.right_panel.pack_forget()
        if layout_mode == "stacked":
            self.left_panel.pack(fill="x", expand=False, side="top", pady=(0, 14))
            self.right_panel.pack(fill="both", expand=True, side="top")
        else:
            self.left_panel.pack(fill="y", expand=False, side="left", padx=(0, 16))
            self.right_panel.pack(fill="both", expand=True, side="left")

    def build_left_panel(self, parent):
        self.left_scroll = ScrollableFrame(parent)
        self.left_scroll.pack(fill="both", expand=True)
        container = self.left_scroll.inner

        self.build_scan_card(container)
        self.build_scope_card(container)
        self.build_injection_card(container)
        self.build_detection_card(container)
        self.build_tamper_card(container)
        self.build_toggle_card(container)
        self.build_enum_card(container)

    def build_right_panel(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=0)
        parent.rowconfigure(1, weight=0)
        parent.rowconfigure(2, weight=1)
        self.build_target_card(parent)
        self.build_preview_card(parent)
        self.build_console_card(parent)

    def build_card(self, parent, title, padding=16):
        card = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe", padding=padding)
        card.pack(fill="x", padx=2, pady=(0, 14))
        return card

    def add_labeled_field(self, parent, label_text, variable, values=None, state=None):
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=(0, 12))
        row.columnconfigure(1, weight=1)
        ttk.Label(row, text=label_text, style="Hint.TLabel", width=12).grid(row=0, column=0, sticky="w", padx=(0, 12))
        if values is not None:
            widget = ttk.Combobox(row, values=values, textvariable=variable, state=state or "normal")
        else:
            widget = ttk.Entry(row, textvariable=variable)
            if state:
                widget.configure(state=state)
        widget.grid(row=0, column=1, sticky="ew")
        return widget

    def build_scan_card(self, parent):
        card = self.build_card(parent, "扫描配置")
        self.add_labeled_field(card, "Level", self.level_var, [str(i) for i in range(1, 6)])
        self.add_labeled_field(card, "Risk", self.risk_var, [str(i) for i in range(1, 4)])
        self.add_labeled_field(card, "线程", self.threads_var)
        self.add_labeled_field(card, "批量并发", self.batch_workers_var)
        self.add_labeled_field(card, "技术", self.technique_var, list(TECHNIQUES.keys()))
        self.add_labeled_field(card, "DBMS", self.dbms_var, DBMS_OPTIONS)

    def build_scope_card(self, parent):
        card = self.build_card(parent, "目标范围")
        self.parameter_entry = self.add_labeled_field(card, "指定参数 -p", self.test_parameter_var)
        self.db_combo = self.add_labeled_field(card, "数据库 -D", self.custom_db_var, values=[], state="normal")
        self.table_combo = self.add_labeled_field(card, "表名 -T", self.custom_table_var, values=[], state="normal")
        self.column_combo = self.add_labeled_field(card, "列名 -C", self.custom_column_var, values=[], state="normal")
        self.db_combo.bind("<<ComboboxSelected>>", self.on_db_selected)
        self.table_combo.bind("<<ComboboxSelected>>", self.on_table_selected)
        self.column_combo.bind("<<ComboboxSelected>>", self.on_column_selected)

        quick_actions = ttk.Frame(card, style="Card.TFrame")
        quick_actions.pack(fill="x", pady=(0, 8))
        ttk.Button(quick_actions, text="使用已识别参数", style="Ghost.TButton", command=self.apply_detected_parameter).pack(side="left", padx=(0, 8))
        ttk.Button(quick_actions, text="清空范围", style="Ghost.TButton", command=self.clear_scope_selection).pack(side="left")

        ttk.Label(card, textvariable=self.detected_injection_summary_var, style="Hint.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Checkbutton(card, text="检测到成功注入后优先复用", variable=self.reuse_injection_var).pack(anchor="w", pady=(0, 4))
        ttk.Label(card, textvariable=self.scope_summary_var, style="Hint.TLabel").pack(anchor="w")

    def build_injection_card(self, parent):
        card = self.build_card(parent, "注入控制")
        self.add_labeled_field(card, "跳过参数", self.skip_parameter_var)
        self.add_labeled_field(card, "参数排除", self.param_exclude_var)
        self.add_labeled_field(card, "参数类型", self.param_filter_var, ["", "GET", "POST", "COOKIE", "UA", "REFERER", "HOST"])
        self.add_labeled_field(card, "Prefix", self.prefix_var)
        self.add_labeled_field(card, "Suffix", self.suffix_var)
        self.add_labeled_field(card, "Time Sec", self.time_sec_var)
        self.add_labeled_field(card, "Union Cols", self.union_cols_var)
        self.add_labeled_field(card, "Union Char", self.union_char_var)
        self.add_labeled_field(card, "Union From", self.union_from_var)
        self.add_labeled_field(card, "Union Values", self.union_values_var)

    def build_detection_card(self, parent):
        card = self.build_card(parent, "检测控制")
        self.add_labeled_field(card, "匹配字符串", self.string_var)
        self.add_labeled_field(card, "排除字符串", self.not_string_var)
        self.add_labeled_field(card, "正则表达式", self.regexp_var)
        self.add_labeled_field(card, "HTTP 代码", self.code_var)
        self.add_labeled_field(card, "测试过滤", self.test_filter_var)
        self.add_labeled_field(card, "测试跳过", self.test_skip_var)

    def build_tamper_card(self, parent):
        card = self.build_card(parent, "绕过与扩展")
        self.add_labeled_field(card, "Tamper 预设", self.tamper_preset_var, list(TAMPER_PRESETS.keys()), state="readonly")
        self.add_labeled_field(card, "附加参数", self.custom_param_var)
        ttk.Label(card, text="复杂请求头、Cookie、代理、超时等高级参数，统一写在附加参数里。", style="Hint.TLabel").pack(anchor="w")

    def build_toggle_card(self, parent):
        card = self.build_card(parent, "快捷开关")
        grid = ttk.Frame(card, style="Card.TFrame")
        grid.pack(fill="x")
        for column in range(2):
            grid.columnconfigure(column, weight=1)
        items = [
            ("随机 UA", self.random_agent_var),
            ("默认应答", self.batch_var),
            ("强制 SSL", self.force_ssl_var),
            ("仅文本比对", self.text_only_var),
            ("跳过 WAF 检测", self.skip_waf_var),
            ("跳过静态参数", self.skip_static_var),
            ("智能探测", self.smart_var),
            ("标题比对", self.titles_var),
            ("跳过启发式", self.skip_heuristics_var),
            ("不使用 CAST", self.no_cast_var),
            ("不转义", self.no_escape_var),
            ("无效大数", self.invalid_bignum_var),
            ("无效逻辑", self.invalid_logical_var),
            ("无效字符串", self.invalid_string_var),
            ("启动前清空会话", self.flush_session_var),
        ]
        for index, (text, variable) in enumerate(items):
            ttk.Checkbutton(grid, text=text, variable=variable).grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 12), pady=4)

    def build_enum_card(self, parent):
        card = self.build_card(parent, "信息获取与批量")
        grid = ttk.Frame(card, style="Card.TFrame")
        grid.pack(fill="x")
        for column in range(2):
            grid.columnconfigure(column, weight=1)
        items = [
            ("当前库", self.current_db_var),
            ("当前用户", self.current_user_var),
            ("枚举库", self.dbs_var),
            ("枚举表", self.tables_var),
            ("枚举列", self.columns_var),
            ("Dump", self.dump_var),
            ("Dump All", self.dump_all_var),
            ("批量 URL", self.batch_url_var),
            ("批量请求包", self.batch_data_var),
        ]
        for index, (text, variable) in enumerate(items):
            ttk.Checkbutton(grid, text=text, variable=variable).grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 12), pady=4)
        ttk.Label(card, text="拖入多个 .txt 文件会自动复制到 batch 目录并启用批量请求包模式。", style="Hint.TLabel").pack(anchor="w", pady=(8, 0))

    def build_target_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.grid(row=0, column=0, sticky="nsew")

        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="目标 / 数据包输入", style="Section.TLabel").pack(side="left")
        badge = tk.Label(top, textvariable=self.mode_var, bg=ACCENT_SOFT, fg=ACCENT, padx=12, pady=5, font=self.fonts["badge"])
        badge.pack(side="left", padx=(12, 0))

        ttk.Label(card, textvariable=self.drop_hint_var, style="Hint.TLabel").pack(anchor="w", pady=(8, 10))

        quick_actions = ttk.Frame(card, style="Card.TFrame")
        quick_actions.pack(fill="x", pady=(0, 10))
        for text, command in [
            ("填充 URL 示例", self.fill_url_example),
            ("填充请求示例", self.fill_request_example),
            ("导入文件", self.import_request_file),
            ("粘贴剪贴板", self.paste_target_text),
            ("清空输入", self.clear_target_text),
        ]:
            ttk.Button(quick_actions, text=text, style="Ghost.TButton", command=command).pack(side="left", padx=(0, 8))

        self.target_text = self.create_text_widget(card, height=7, font_key="text_area")
        self.target_text.pack(fill="both", expand=True)
        self.root.after(120, self.focus_target_input)

    def build_preview_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        card.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="命令预览", style="Section.TLabel").pack(side="left")
        ttk.Button(top, text="复制预览", style="Ghost.TButton", command=self.copy_preview).pack(side="right")
        self.preview_text = self.create_text_widget(card, height=1, font_key="mono")
        self.preview_text.pack(fill="x", pady=(8, 0))

        input_row = ttk.Frame(card, style="Card.TFrame")
        input_row.pack(fill="x", pady=(10, 0))
        ttk.Label(input_row, text="交互输入", style="Hint.TLabel").pack(side="left", padx=(0, 8))
        input_entry = ttk.Entry(input_row, textvariable=self.interactive_input_var)
        input_entry.pack(side="left", fill="x", expand=True)
        input_entry.bind("<Return>", self.send_interactive_input)
        ttk.Button(input_row, text="发送", style="Ghost.TButton", command=self.send_interactive_input).pack(side="left", padx=(8, 0))

    def build_console_card(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame", padding=(18, 18, 18, 0))
        card.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)
        top = ttk.Frame(card, style="Card.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="运行日志", style="Section.TLabel").pack(side="left")
        ttk.Label(top, textvariable=self.status_var, style="Badge.TLabel").pack(side="left", padx=(12, 0))
        ttk.Button(top, text="清空日志", style="Ghost.TButton", command=self.clear_console).pack(side="right")
        ttk.Button(top, text="打开结果目录", style="Ghost.TButton", command=self.open_result_dir).pack(side="right", padx=(0, 8))

        self.console_text = self.create_text_widget(card, height=1, font_key="mono")
        self.console_text.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

    def create_text_widget(self, parent, height, font_key="text_area"):
        widget = ScrolledText(
            parent,
            height=height,
            wrap="none" if font_key == "mono" else "word",
            undo=True,
            autoseparators=True,
            maxundo=-1,
            bg=SURFACE_ALT,
            fg=TEXT,
            insertbackground=TEXT,
            insertwidth=2,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            takefocus=True,
            font=self.fonts[font_key],
            padx=14,
            pady=14,
        )
        widget.bind("<Button-1>", self.focus_text_widget, add="+")
        widget.bind("<FocusIn>", self.on_text_focus_in, add="+")
        widget.bind("<FocusOut>", self.on_text_focus_out, add="+")
        widget.bind("<Control-v>", self.handle_text_paste, add="+")
        widget.bind("<Button-3>", self.focus_text_widget, add="+")
        widget.bind("<KeyRelease>", lambda _event: self.refresh_preview(force=True))
        return widget

    def focus_target_input(self):
        self.target_text.after_idle(self.target_text.focus_force)
        self.target_text.after_idle(lambda: self.target_text.mark_set(tk.INSERT, tk.INSERT))

    def focus_text_widget(self, event):
        event.widget.focus_set()

    def on_text_focus_in(self, event):
        event.widget.configure(highlightbackground=ACCENT, highlightcolor=ACCENT)

    def on_text_focus_out(self, event):
        event.widget.configure(highlightbackground=BORDER, highlightcolor=ACCENT)

    def handle_text_paste(self, event):
        event.widget.after_idle(lambda: self.refresh_preview(force=True))

    def enable_drop_support(self):
        if sys.platform.startswith("win") and self.enable_windows_drop(self.target_text):
            self.drop_hint_var.set("可将 .txt 请求包直接拖到输入区，或粘贴原始数据包 / URL")
            return
        self.drop_hint_var.set("当前环境未启用原生拖拽，可直接粘贴内容")

    def enable_windows_drop(self, widget):
        try:
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32

            user32.GetWindowLongPtrW.restype = ctypes.c_void_p
            user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.SetWindowLongPtrW.restype = ctypes.c_void_p
            user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            user32.CallWindowProcW.restype = LRESULT
            user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

            hwnd = widget.winfo_id()
            old_proc = user32.GetWindowLongPtrW(hwnd, GWL_WNDPROC)
            app = self

            @WNDPROC
            def new_proc(drop_hwnd, msg, wparam, lparam):
                if msg == WM_DROPFILES:
                    files = []
                    count = shell32.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)
                    for index in range(count):
                        length = shell32.DragQueryFileW(wparam, index, None, 0) + 1
                        buffer = ctypes.create_unicode_buffer(length)
                        shell32.DragQueryFileW(wparam, index, buffer, length)
                        files.append(buffer.value)
                    shell32.DragFinish(wparam)
                    app.root.after(0, lambda: app.handle_dropped_files(files))
                    return 0
                return user32.CallWindowProcW(old_proc, drop_hwnd, msg, wparam, lparam)

            user32.SetWindowLongPtrW(hwnd, GWL_WNDPROC, ctypes.cast(new_proc, ctypes.c_void_p).value)
            shell32.DragAcceptFiles(hwnd, True)
            self._drop_old_proc = old_proc
            self._drop_callback = new_proc
            self._drop_hwnd = hwnd
            return True
        except Exception:
            return False

    def teardown_drop_support(self):
        if not sys.platform.startswith("win"):
            return
        if not self._drop_hwnd or not self._drop_old_proc:
            return
        try:
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32
            user32.SetWindowLongPtrW.restype = ctypes.c_void_p
            user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            user32.SetWindowLongPtrW(self._drop_hwnd, GWL_WNDPROC, self._drop_old_proc)
            shell32.DragAcceptFiles(self._drop_hwnd, False)
        except Exception:
            pass

    def handle_dropped_files(self, paths):
        txt_paths = [path for path in paths if path.lower().endswith(".txt") and os.path.isfile(path)]
        if not txt_paths:
            messagebox.showwarning("提示", "仅支持拖入 .txt 请求包文件。")
            return
        self.load_or_batch_import_files(txt_paths)

    def import_request_file(self):
        path = filedialog.askopenfilename(
            title="选择请求包文件",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        self.load_or_batch_import_files([path])

    def set_target_text(self, content):
        self.focus_target_input()
        normalized_content = normalize_request_payload(content)
        self.target_text.delete("1.0", tk.END)
        self.target_text.insert("1.0", normalized_content)
        self.target_text.mark_set(tk.INSERT, "1.0")
        self.target_text.see(tk.INSERT)
        self.refresh_preview(force=True)

    def paste_target_text(self):
        try:
            content = self.root.clipboard_get()
        except tk.TclError:
            self.status_var.set("剪贴板没有可粘贴的文本")
            self.target_text.focus_set()
            return
        self.batch_url_var.set(False)
        self.batch_data_var.set(False)
        self.set_target_text(content)
        self.status_var.set("已粘贴剪贴板内容")

    def load_or_batch_import_files(self, paths):
        txt_paths = [path for path in paths if path.lower().endswith(".txt") and os.path.isfile(path)]
        if not txt_paths:
            messagebox.showwarning("提示", "没有可用的 .txt 文件。")
            return

        if len(txt_paths) == 1:
            content = read_text_file(txt_paths[0])
            self.set_target_text(content)
            self.batch_data_var.set(False)
            self.status_var.set(f"已导入请求包：{os.path.basename(txt_paths[0])}")
            return

        copied = []
        for path in txt_paths:
            copied.append(unique_copy_to_batch(path))
        self.batch_data_var.set(True)
        self.target_text.delete("1.0", tk.END)
        self.status_var.set(f"已导入 {len(copied)} 个请求包到 batch 目录")
        self.refresh_preview(force=True)

    def fill_url_example(self):
        self.batch_url_var.set(False)
        self.batch_data_var.set(False)
        self.set_target_text(URL_EXAMPLE)

    def fill_request_example(self):
        self.batch_url_var.set(False)
        self.batch_data_var.set(False)
        self.set_target_text(REQUEST_EXAMPLE)

    def clear_target_text(self):
        self.set_target_text("")

    def open_batch_dir(self):
        open_path(ensure_directory(BATCH_DIR))

    def select_sqlmap_script(self):
        path = filedialog.askopenfilename(
            title="选择 sqlmap.py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
            initialdir=os.path.dirname(self.sqlmap_script_var.get()) if self.sqlmap_script_var.get() else PROJECT_ROOT,
        )
        if not path:
            return
        self.sqlmap_script_var.set(path)
        self.refresh_sqlmap_version()
        self.refresh_preview(force=True)

    def refresh_sqlmap_version(self):
        framework_entry = os.path.join(PROJECT_ROOT, "framework", "cli.py")
        exists = os.path.isfile(framework_entry)
        status = "可用" if exists else "不存在"
        self.sqlmap_version_var.set(f"当前框架入口：{framework_entry} | 状态：{status}")

    def open_output_dir(self):
        output_dir, _ = get_sqlmap_result_dirs()
        open_path(output_dir)

    def open_result_dir(self):
        _, ldopt_dir = get_sqlmap_result_dirs()
        open_path(ldopt_dir)

    def append_console_text(self, message, parse_output=False):
        if parse_output:
            try:
                for line in self.iter_console_parse_lines(message):
                    self.handle_sqlmap_output_line(line)
            except Exception as exc:
                self.status_var.set(f"日志解析异常：{exc}")
        self.console_text.insert(tk.END, message)
        self.console_text.mark_set(tk.INSERT, tk.END)
        self.console_text.see(tk.END)
        self.console_text.yview_moveto(1.0)
        self.console_text.update_idletasks()

    def iter_console_parse_lines(self, message):
        if not message:
            return []

        self.output_parse_buffer += message.replace("\r", "\n")
        completed = []
        while "\n" in self.output_parse_buffer:
            line, self.output_parse_buffer = self.output_parse_buffer.split("\n", 1)
            completed.append(line)
        return completed

    def log(self, text):
        message = text if text.endswith("\n") else text + "\n"
        if threading.current_thread() is threading.main_thread():
            self.append_console_text(message, parse_output=False)
        else:
            self.console_queue.put(message)

    def start_console_pump(self):
        self.root.after(100, self.pump_console)

    def pump_console(self):
        try:
            while True:
                try:
                    message = self.console_queue.get_nowait()
                except queue.Empty:
                    break
                if isinstance(message, tuple):
                    kind = message[0]
                    if kind == "status":
                        self.status_var.set(message[1])
                    elif kind == "done":
                        self.on_process_done(message[1], message[2])
                    continue
                self.append_console_text(message, parse_output=False)
        finally:
            self.root.after(100, self.pump_console)

    def start_preview_watcher(self):
        for variable in self.watch_vars:
            variable.trace_add("write", lambda *_args: self.refresh_preview(force=True))
        self.refresh_preview(force=True)

    def get_target_value(self):
        return self.target_text.get("1.0", "end-1c").strip()

    def get_selected_tampers(self):
        preset = self.tamper_preset_var.get()
        return [name for name in TAMPER_PRESETS.get(preset, []) if name in self.tamper_scripts]

    def refresh_scope_choices(self):
        db_values = list(self.discovered_dbs)
        self.db_combo.configure(values=db_values)

        selected_db = self.custom_db_var.get().strip()
        db_key = selected_db or self.current_enum_db
        table_values = list(self.discovered_tables.get(db_key, [])) if db_key else []
        self.table_combo.configure(values=table_values)

        selected_table = self.custom_table_var.get().strip()
        table_key = (db_key, selected_table or self.current_enum_table)
        column_values = list(self.discovered_columns.get(table_key, [])) if all(table_key) else []
        self.column_combo.configure(values=column_values)

        db_count = len(self.discovered_dbs)
        table_count = sum(len(items) for items in self.discovered_tables.values())
        column_count = sum(len(items) for items in self.discovered_columns.values())
        if db_count or table_count or column_count:
            self.scope_summary_var.set(f"已枚举 数据库 {db_count} / 表 {table_count} / 列 {column_count}")
        else:
            self.scope_summary_var.set("尚未枚举到数据库 / 表 / 列")

    def update_detected_injection_summary(self):
        if not self.detected_technique_codes and not self.detected_parameter_name:
            self.detected_injection_summary_var.set("尚未识别到成功注入方式")
            return

        labels = []
        for name, code in TECHNIQUES.items():
            if name != "全部" and code in self.detected_technique_codes:
                labels.append(name)

        parts = []
        if self.detected_parameter_name:
            parts.append(f"参数: {self.detected_parameter_name}")
        if labels:
            parts.append("方式: " + " / ".join(labels))
        self.detected_injection_summary_var.set("已识别 " + "，".join(parts))

    def add_discovered_db(self, name):
        value = (name or "").strip()
        if not value or value == "<current>":
            return
        if value not in self.discovered_dbs:
            self.discovered_dbs.append(value)
            self.discovered_dbs.sort(key=str.lower)
        self.current_enum_db = value
        self.refresh_scope_choices()

    def add_discovered_table(self, db_name, table_name):
        db_value = (db_name or "").strip()
        table_value = (table_name or "").strip()
        if db_value == "<current>":
            db_value = self.current_database_name
        if not db_value or not table_value:
            return
        bucket = self.discovered_tables.setdefault(db_value, [])
        if table_value not in bucket:
            bucket.append(table_value)
            bucket.sort(key=str.lower)
        self.current_enum_db = db_value
        self.current_enum_table = table_value
        self.refresh_scope_choices()

    def add_discovered_column(self, db_name, table_name, column_name):
        db_value = (db_name or "").strip()
        table_value = (table_name or "").strip()
        column_value = (column_name or "").strip()
        if db_value == "<current>":
            db_value = self.current_database_name
        if not db_value or not table_value or not column_value:
            return
        bucket = self.discovered_columns.setdefault((db_value, table_value), [])
        if column_value not in bucket:
            bucket.append(column_value)
            bucket.sort(key=str.lower)
        self.current_enum_db = db_value
        self.current_enum_table = table_value
        self.refresh_scope_choices()

    def remember_detected_technique(self, code):
        if code and code not in self.detected_technique_codes:
            self.detected_technique_codes.append(code)
            ordered_codes = []
            for candidate in TECHNIQUES.values():
                if candidate and candidate != "BESUTQ" and candidate in self.detected_technique_codes:
                    ordered_codes.append(candidate)
            self.detected_technique_codes = ordered_codes
            self.update_detected_injection_summary()
            self.refresh_preview(force=True)

    def apply_detected_parameter(self):
        if self.detected_parameter_name:
            self.test_parameter_var.set(self.detected_parameter_name)
        self.refresh_preview(force=True)

    def clear_scope_selection(self):
        self.custom_db_var.set("")
        self.custom_table_var.set("")
        self.custom_column_var.set("")
        self.current_enum_db = None
        self.current_enum_table = None
        self.refresh_scope_choices()
        self.refresh_preview(force=True)

    def on_db_selected(self, _event=None):
        self.current_enum_db = self.custom_db_var.get().strip() or None
        self.custom_table_var.set("")
        self.custom_column_var.set("")
        self.current_enum_table = None
        self.refresh_scope_choices()
        self.refresh_preview(force=True)

    def on_table_selected(self, _event=None):
        self.current_enum_db = self.custom_db_var.get().strip() or self.current_enum_db
        self.current_enum_table = self.custom_table_var.get().strip() or None
        self.custom_column_var.set("")
        self.refresh_scope_choices()
        self.refresh_preview(force=True)

    def on_column_selected(self, _event=None):
        self.refresh_preview(force=True)

    def handle_sqlmap_output_line(self, line):
        text = (line or "").rstrip("\r\n")
        if not text:
            return

        current_db_match = re.search(r"(?:当前数据库|current database)(?:\([^)]*\))?:\s*'?(.*?)'?$", text, re.I)
        if current_db_match:
            current_db = current_db_match.group(1).strip()
            if current_db:
                self.current_database_name = current_db
                self.add_discovered_db(current_db)

        parameter_match = re.search(r"(?:参数|Parameter):\s*([^\s(]+)", text, re.I)
        if parameter_match:
            self.detected_parameter_name = parameter_match.group(1).strip()
            self.update_detected_injection_summary()

        technique_patterns = {
            "B": r"(?:类型|Type):\s*(?:基于布尔的盲注|boolean-based blind)",
            "E": r"(?:类型|Type):\s*(?:报错|error-based)",
            "S": r"(?:类型|Type):\s*(?:堆叠|stacked queries)",
            "U": r"(?:类型|Type):\s*(?:UNION 查询|UNION query)",
            "T": r"(?:类型|Type):\s*(?:基于时间的盲注|time-based blind)",
            "Q": r"(?:类型|Type):\s*(?:内联查询|inline query)",
        }
        for code, pattern in technique_patterns.items():
            if re.search(pattern, text, re.I):
                self.remember_detected_technique(code)

        db_list_match = re.search(r"(?:可用数据库|available databases)\s*\[(\d+)\]:", text, re.I)
        if db_list_match:
            self._parse_state = "dbs"
            return

        db_header_match = re.search(r"^(?:数据库|Database):\s*(.+)$", text, re.I)
        if db_header_match:
            self._parse_state = None
            self._current_output_db = db_header_match.group(1).strip()
            return

        current_db_context_match = re.search(r"Database:\s*(.+)$", text, re.I)
        if current_db_context_match:
            self._current_output_db = current_db_context_match.group(1).strip().strip("'\"")

        table_header_match = re.search(r"^Table:\s*(.+)$", text, re.I)
        if table_header_match:
            self._current_output_table = table_header_match.group(1).strip().strip("'\"")
            self._parse_state = None
            return

        current_table_context_match = re.search(r"Table:\s*(.+)$", text, re.I)
        if current_table_context_match:
            self._current_output_table = current_table_context_match.group(1).strip().strip("'\"")

        fetch_tables_match = re.search(r"fetching tables for database(?:s)?:\s*'?(.*?)'?$", text, re.I)
        if fetch_tables_match:
            fetched_dbs = [item.strip().strip("'\"") for item in fetch_tables_match.group(1).split(",") if item.strip()]
            if fetched_dbs:
                self._current_output_db = fetched_dbs[0]
            return

        fetch_columns_match = re.search(r"fetching columns .*? for table(?:s)?:\s*'?(.*?)'?(?:\s+in database\s+'?(.*?)'?)?$", text, re.I)
        if fetch_columns_match:
            table_name = fetch_columns_match.group(1).strip().strip("'\"")
            db_name = (fetch_columns_match.group(2) or self._current_output_db or "").strip().strip("'\"")
            if db_name:
                self._current_output_db = db_name
            if table_name:
                self._current_output_table = table_name
            return

        if text.startswith("[") and ("tables" in text.lower() or "table" in text.lower()) and self._current_output_db:
            self._parse_state = "tables"
            return

        if text.startswith("[") and ("columns" in text.lower() or "column" in text.lower()) and self._current_output_db and self._current_output_table:
            self._parse_state = "columns"
            return

        item_match = re.search(r"^\[\*\]\s+(.+)$", text)
        if item_match and self._parse_state == "dbs":
            self.add_discovered_db(item_match.group(1).strip())
            return

        table_row_match = re.search(r"^\|\s+([^|]+?)\s+\|$", text)
        if table_row_match and self._current_output_db and self._parse_state == "tables":
            table_name = table_row_match.group(1).strip()
            if table_name.lower() not in {"table"} and not set(table_name) <= {"-"}:
                self.add_discovered_table(self._current_output_db, table_name)
            return

        column_row_match = re.search(r"^\|\s+([^|]+?)\s+\|(?:\s+[^|]+?\s+\|)?$", text)
        if column_row_match and self._current_output_db and self._current_output_table and self._parse_state == "columns":
            column_name = column_row_match.group(1).strip()
            if column_name.lower() not in {"column"} and not set(column_name) <= {"-"}:
                self.add_discovered_column(self._current_output_db, self._current_output_table, column_name)
            return

        if text.startswith("+"):
            return

        if not text.startswith("|"):
            self._parse_state = None

    def detect_input_mode(self):
        if self.batch_data_var.get():
            return "batch_request_files", []

        text = self.get_target_value()
        if not text:
            return "empty", []

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return "empty", []

        all_are_urls = all(re.match(r"(?i)^https?://", line) for line in lines)
        if self.batch_url_var.get() or (len(lines) > 1 and all_are_urls):
            return "batch_urls", lines

        if re.match(r"(?i)^https?://", lines[0]):
            return "single_url", lines[0]

        if re.search(r"HTTP/\d\.\d", text) or re.match(r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+", lines[0]):
            return "raw_request", text

        if len(lines) == 1:
            return "single_url", lines[0]

        return "raw_request", text

    def refresh_preview(self, force=False):
        signature = (tuple(var.get() for var in self.watch_vars), self.get_target_value())
        if not force and signature == self.preview_signature:
            return
        self.preview_signature = signature

        mode, payload = self.detect_input_mode()
        label_text = {
            "empty": "等待输入目标",
            "single_url": "单目标 URL",
            "raw_request": "原始请求包",
            "batch_urls": f"批量 URL × {len(payload)}",
            "batch_request_files": "批量请求包目录",
        }.get(mode, "未识别")
        self.mode_var.set(label_text)

        preview_lines = []
        try:
            if mode == "empty":
                preview_lines.append("等待输入 URL、原始 HTTP 请求或拖拽 .txt 请求包。")
            elif mode == "single_url":
                preview_lines.append(format_command(self.build_sqlmap_command(target_override=payload)))
            elif mode == "raw_request":
                preview_lines.append(format_command(self.build_sqlmap_command(request_file=self.persist_request_payload(payload))))
            elif mode == "batch_urls":
                preview_lines.append(f"批量目标数：{len(payload)}")
                preview_lines.append(f"批量并发：{safe_int(self.batch_workers_var.get(), default=5, minimum=1, maximum=20)}")
                preview_lines.append(format_command(self.build_sqlmap_command(target_override=payload[0], force_batch=True)))
                if len(payload) > 1:
                    preview_lines.append("以上命令预览展示第 1 个目标，实际会按列表逐条执行。")
            elif mode == "batch_request_files":
                preview_lines.append("数据来源：batch/*.txt")
                preview_lines.append(f"批量并发：{safe_int(self.batch_workers_var.get(), default=5, minimum=1, maximum=20)}")
                preview_lines.append(format_command(self.build_sqlmap_command(request_file="<batch-request>", force_batch=True)))
        except Exception as exc:
            preview_lines.append(f"命令预览生成失败：{exc}")

        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", "\n".join(preview_lines))

    def build_base_launcher(self):
        framework_entry = os.path.join(PROJECT_ROOT, "framework", "cli.py")
        return [self.python_command, "-u", "-Xfrozen_modules=off", framework_entry]

    def append_optional_value(self, command, flag, value):
        value = (value or "").strip()
        if value:
            command.extend([flag, value])

    def append_optional_bool(self, command, flag, enabled):
        if enabled:
            command.append(flag)

    def persist_request_payload(self, text):
        normalized_text = normalize_request_payload(text)
        with open(REQUEST_CACHE_FILE, "w", encoding="utf-8", newline="") as handle:
            handle.write(normalized_text)
        return REQUEST_CACHE_FILE

    def build_sqlmap_command(self, target_override=None, request_file=None, force_batch=False, output_dir=None):
        command = self.build_base_launcher()
        if os.path.isfile(FRAMEWORK_CONFIG_FILE):
            command.extend(["--config", FRAMEWORK_CONFIG_FILE])

        if target_override:
            command.extend(["--target", target_override])
        elif request_file:
            command.extend(["--request-file", request_file])
        else:
            mode, payload = self.detect_input_mode()
            if mode == "single_url":
                command.extend(["--target", payload])
            elif mode == "raw_request":
                command.extend(["--request-file", self.persist_request_payload(payload)])

        command.extend(["--output-dir", output_dir or FRAMEWORK_OUTPUT_DIR])
        return command

    def apply_profile(self):
        profile = self.profile_var.get()
        if profile == "平衡测试":
            self.level_var.set("3")
            self.risk_var.set("2")
            self.threads_var.set("6")
            self.batch_workers_var.set("5")
            self.technique_var.set("全部")
            self.batch_var.set(True)
            self.random_agent_var.set(True)
            self.force_ssl_var.set(False)
            self.text_only_var.set(False)
            self.skip_waf_var.set(False)
            self.tamper_preset_var.set("通用绕过")
        elif profile == "深度测试":
            self.level_var.set("5")
            self.risk_var.set("3")
            self.threads_var.set("10")
            self.batch_workers_var.set("4")
            self.technique_var.set("全部")
            self.batch_var.set(True)
            self.random_agent_var.set(True)
            self.force_ssl_var.set(False)
            self.text_only_var.set(False)
            self.skip_waf_var.set(False)
            self.tamper_preset_var.set("通用绕过")
        elif profile == "WAF 绕过":
            self.level_var.set("4")
            self.risk_var.set("2")
            self.threads_var.set("4")
            self.batch_workers_var.set("4")
            self.technique_var.set("全部")
            self.batch_var.set(True)
            self.random_agent_var.set(True)
            self.force_ssl_var.set(True)
            self.text_only_var.set(True)
            self.skip_waf_var.set(True)
            self.tamper_preset_var.set("WAF 强化")
        self.refresh_preview(force=True)

    def copy_preview(self):
        preview = self.preview_text.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(preview)
        self.status_var.set("命令预览已复制")

    def clear_console(self):
        self.console_text.delete("1.0", tk.END)
        self.status_var.set("日志已清空")

    def start_run(self):
        if self.process is not None:
            messagebox.showinfo("提示", "已有前台任务在运行，请先停止或等待完成。")
            return
        with self.process_lock:
            if self.batch_processes:
                messagebox.showinfo("提示", "已有批量任务在运行，请先停止或等待完成。")
                return

        mode, payload = self.detect_input_mode()
        if mode == "empty":
            messagebox.showwarning("提示", "请先输入 URL、原始 HTTP 请求，或拖拽 .txt 请求包。")
            return
        if mode == "batch_urls" and not payload:
            messagebox.showwarning("提示", "批量 URL 模式下至少需要一条 URL。")
            return

        framework_entry = os.path.join(PROJECT_ROOT, "framework", "cli.py")
        if not os.path.isfile(framework_entry):
            messagebox.showerror("启动失败", f"框架入口不存在：\n{framework_entry}")
            self.status_var.set("框架入口无效")
            return

        self.refresh_sqlmap_version()
        self.stop_event.clear()
        self.output_parse_buffer = ""
        self.clear_console()

        if mode in ("single_url", "raw_request"):
            command = self.build_sqlmap_command(output_dir=build_framework_output_dir())
            self.log(f"$ {format_command(command)}")
            self.run_foreground_process(command)
            return

        if mode == "batch_urls":
            jobs = [
                (
                    f"URL-{index + 1}",
                    self.build_sqlmap_command(
                        target_override=url,
                        force_batch=True,
                        output_dir=build_framework_output_dir(f"url-{index + 1}"),
                    ),
                )
                for index, url in enumerate(payload)
            ]
            threading.Thread(target=self.run_batch_jobs, args=(jobs, False), daemon=True).start()
            return

        if mode == "batch_request_files":
            ensure_directory(BATCH_DIR)
            request_files = [
                os.path.join(BATCH_DIR, filename)
                for filename in sorted(os.listdir(BATCH_DIR))
                if filename.lower().endswith(".txt")
            ]
            if not request_files:
                messagebox.showwarning("提示", "batch 目录下没有 .txt 请求包文件。")
                return
            jobs = [
                (
                    os.path.basename(path),
                    self.build_sqlmap_command(
                        request_file=path,
                        force_batch=True,
                        output_dir=build_framework_output_dir(os.path.splitext(os.path.basename(path))[0]),
                    ),
                )
                for path in request_files
            ]
            threading.Thread(target=self.run_batch_jobs, args=(jobs, True), daemon=True).start()

    def get_popen_kwargs(self, interactive=False):
        framework_entry = os.path.join(PROJECT_ROOT, "framework", "cli.py")
        kwargs = {
            "cwd": PROJECT_ROOT if os.path.isfile(framework_entry) else BASE_DIR,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "bufsize": 1,
            "env": SQLMAP_ENV,
        }
        if interactive:
            kwargs["stdin"] = subprocess.PIPE
        else:
            kwargs["stdin"] = subprocess.DEVNULL
        if sys.platform.startswith("win"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            kwargs["startupinfo"] = startupinfo
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return kwargs

    def run_foreground_process(self, command):
        self.status_var.set("前台任务运行中")
        self.process_accepts_stdin = False
        self.log("[*] 安全检测过程正在下方日志面板实时显示")
        try:
            self.process = subprocess.Popen(
                command,
                **self.get_popen_kwargs(interactive=self.process_accepts_stdin),
            )
        except Exception as exc:
            self.process = None
            messagebox.showerror("启动失败", str(exc))
            self.status_var.set("启动失败")
            return

        threading.Thread(target=self.stream_foreground_output, daemon=True).start()

    def stream_process_output(self, process, prefix=""):
        stream = process.stdout
        while True:
            line = stream.readline()
            if not line:
                break
            self.console_queue.put(f"{prefix}{line}" if prefix else line)
            if self.stop_event.is_set() and process.poll() is None:
                process.terminate()

    def stream_foreground_output(self):
        return_code = -1
        try:
            self.stream_process_output(self.process)
            return_code = self.process.wait()
        except Exception as exc:
            self.console_queue.put(f"\n[!] 读取输出失败：{exc}\n")
        finally:
            self.console_queue.put(("done", return_code, "前台任务"))

    def run_batch_jobs(self, jobs, copy_results):
        worker_count = safe_int(self.batch_workers_var.get(), default=5, minimum=1, maximum=20)
        self.console_queue.put(("status", f"批量任务运行中（并发 {worker_count}）"))
        self.log(f"[*] 批量任务启动：{len(jobs)} 个，最大并发 {worker_count}")

        def worker(label, command):
            if self.stop_event.is_set():
                return label, -1
            self.log(f"\n[{label}] $ {format_command(command)}")
            process = subprocess.Popen(
                command,
                **self.get_popen_kwargs(),
            )
            with self.process_lock:
                self.batch_processes.add(process)
            try:
                self.stream_process_output(process, prefix=f"[{label}] ")
                return_code = process.wait()
            finally:
                with self.process_lock:
                    self.batch_processes.discard(process)
            self.log(f"[{label}] 结束，返回码 {return_code}")
            return label, return_code

        futures = []
        results = []
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            for label, command in jobs:
                futures.append(executor.submit(worker, label, command))
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    self.log(f"[!] 批量任务异常：{exc}")
                    results.append(("unknown", -1))

        if copy_results and not self.stop_event.is_set():
            output_dir, ldopt_dir = get_sqlmap_result_dirs()
            if os.path.abspath(output_dir) != os.path.abspath(ldopt_dir):
                copied = copy_folders_with_log_files(output_dir, ldopt_dir)
                self.log(f"[*] 已同步 {copied} 个存在结果的目录到 ldopt")

        final_code = 0 if results and all(code == 0 for _label, code in results) else (-1 if any(code != 0 for _label, code in results) else 0)
        self.console_queue.put(("done", final_code, "批量任务"))

    def on_process_done(self, return_code, task_type):
        self.process = None
        self.process_accepts_stdin = False
        self.stop_event.clear()
        if task_type == "批量任务" and return_code == 0:
            self.status_var.set("批量任务完成")
        elif task_type == "批量任务":
            self.status_var.set(f"批量任务结束，返回码 {return_code}")
        elif return_code == 0:
            self.status_var.set("前台任务完成")
        else:
            self.status_var.set(f"{task_type}结束，返回码 {return_code}")

        summary = read_framework_report_summary(FRAMEWORK_OUTPUT_DIR)
        if summary["reports"]:
            self.detected_injection_summary_var.set(
                f"风险结论 {summary['findings']} 条，高风险 {summary['high']} / 中风险 {summary['medium']} / 低风险 {summary['low']}"
            )
            self.scope_summary_var.set(f"已生成报告 {summary['reports']} 份")

    def stop_run(self):
        self.stop_event.set()
        stopped = False
        if self.process is not None and self.process.poll() is None:
            try:
                self.process.terminate()
                stopped = True
            except Exception:
                pass
        with self.process_lock:
            for process in list(self.batch_processes):
                if process.poll() is None:
                    try:
                        process.terminate()
                        stopped = True
                    except Exception:
                        pass
        self.status_var.set("停止中" if stopped else "当前没有正在运行的任务")
        if stopped:
            self.log("[!] 已请求停止当前任务")

    def send_interactive_input(self, _event=None):
        if self.process is None or self.process.poll() is not None:
            self.status_var.set("当前没有正在运行的前台任务")
            return "break"
        if not self.process_accepts_stdin:
            self.status_var.set("当前运行模式不支持通过此输入框发送交互输入")
            return "break"

        value = self.interactive_input_var.get()
        try:
            self.process.stdin.write(value + "\n")
            self.process.stdin.flush()
            self.log(f">>> {value}")
            self.interactive_input_var.set("")
        except Exception as exc:
            self.log(f"[!] 发送交互输入失败：{exc}")
        return "break"

    def open_text_dialog(self, title, content):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("980x760")
        dialog.configure(bg=BG)
        text = self.create_text_widget(dialog, height=34)
        text.pack(fill="both", expand=True, padx=16, pady=16)
        text.delete("1.0", tk.END)
        text.insert("1.0", content)

    def show_help(self):
        self.open_text_dialog("工具帮助", HELP_TEXT)


def launch_gui(python_command):
    root = tk.Tk()
    app = SqlmapGuiApp(root, python_command=python_command)
    messagebox.showinfo(
        "使用说明",
        "新版界面已进一步精简：\n\n- 统一为单输入区\n- 支持直接粘贴原始数据包\n- 支持导入/拖拽 .txt 请求包\n- 明亮主题与更简洁布局已启用",
    )
    root.mainloop()
    return app


if __name__ == "__main__":
    launch_gui("python3" if os.name != "nt" else "python")
