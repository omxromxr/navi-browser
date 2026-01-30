import sys
import json
import os
import time
from datetime import datetime
from PyQt6.QtCore import QUrl, Qt, QSize, QTimer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QLineEdit,
    QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QMessageBox, QTabWidget, QMenu, QDialog, QPlainTextEdit
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings

# --- Constants ---
DATA_FILE = "navi_data.json"
TWO_WEEKS_SECONDS = 1209600

# --- Helper Functions ---
def get_search_url(engine, query):
    engines = {
        "Google": "https://www.google.com/search?q=",
        "Bing": "https://www.bing.com/search?q=",
        "Yahoo": "https://search.yahoo.com/search?p=",
        "DuckDuckGo": "https://duckduckgo.com/?q=",
        "Ecosia": "https://www.ecosia.org/search?q=",
        "Yandex": "https://yandex.com/search/?text=",
        "Brave": "https://search.brave.com/search?q=",
        "Startpage": "https://www.startpage.com/do/search?q=",
        "Qwant": "https://www.qwant.com/?q=",
        "Searx": "https://searx.be/search?q=",
        "Baidu": "https://www.baidu.com/s?wd=",  # Popular in China
        "Naver": "https://search.naver.com/search.naver?query=",  # Popular in South Korea
        "Ask": "https://www.ask.com/web?q=",
        "Mojeek": "https://www.mojeek.com/search?q=",  # Independent index
        "Gigablast": "https://www.gigablast.com/search?q=",
        "Swisscows": "https://swisscows.com/en/web?query=",  # Family-friendly
        "You.com": "https://you.com/search?q=",  # AI-powered
        "Google Scholar": "https://scholar.google.com/scholar?q=",
        "Wolfram Alpha": "https://www.wolframalpha.com/input?i=",
    }
    return engines.get(engine, engines["Google"]) + query.replace(" ", "+")

# --- UI Styling ---
class BrowserStyles:
    @staticmethod
    def get(theme, engine_mode):
        themes = {
            "light": {"bg": "#f8f9fa", "fg": "#212529", "tab": "#ffffff", "sel": "#e9ecef", "bar": "#ffffff", "acc": "#0d6efd", "border": "#dee2e6"},
            "dark": {"bg": "#212529", "fg": "#f8f9fa", "tab": "#2c3034", "sel": "#343a40", "bar": "#343a40", "acc": "#0d6efd", "border": "#495057"},
            "christmas": {"bg": "#0f2e1c", "fg": "#fff", "tab": "#1a472a", "sel": "#c41e3a", "bar": "#1a472a", "acc": "#d4af37", "border": "#5d8a6f"},
            "halloween": {"bg": "#121212", "fg": "#ffa500", "tab": "#1f1f1f", "sel": "#2d2d2d", "bar": "#1f1f1f", "acc": "#ff4500", "border": "#444"},
            "cyberpunk": {"bg": "#0b0d17", "fg": "#00f3ff", "tab": "#121526", "sel": "#1c1f3a", "bar": "#121526", "acc": "#ff0099", "border": "#00f3ff"},
            "sunset": {"bg": "#2d1b2e", "fg": "#ffcc00", "tab": "#442244", "sel": "#b3446c", "bar": "#442244", "acc": "#f6511d", "border": "#b3446c"},
            "matrix": {"bg": "#000000", "fg": "#00ff00", "tab": "#0a0a0a", "sel": "#111", "bar": "#0a0a0a", "acc": "#008f11", "border": "#003300"},
        }
        c = themes.get(theme, themes["dark"])
        radius = "12px" if engine_mode == "modern" else "0px"
        font_family = "'Poppins', sans-serif" if engine_mode == "modern" else "'Segoe UI', sans-serif"

        return f"""
        QMainWindow {{ background-color: {c['bg']}; color: {c['fg']}; }}
        QWidget {{ color: {c['fg']}; font-family: {font_family}; }}
        QTabWidget::pane {{ border: 0; background: {c['bg']}; }}
        QTabBar::tab {{ background: {c['tab']}; color: {c['fg']}; padding: 8px 20px; border-top-left-radius: {radius}; border-top-right-radius: {radius}; margin-right: 4px; }}
        QTabBar::tab:selected {{ background: {c['sel']}; border-bottom: 3px solid {c['acc']}; }}
        QToolBar {{ background: {c['bar']}; border-bottom: 1px solid {c['border']}; spacing: 8px; padding: 6px; }}
        QLineEdit {{ background: {c['bg']}; border: 1px solid {c['border']}; border-radius: {radius}; padding: 8px; color: {c['fg']}; }}
        QPushButton {{ background: transparent; border-radius: 6px; padding: 6px; color: {c['fg']}; font-weight: bold; }}
        QPushButton:hover {{ background: {c['sel']}; }}
        """

class InternalPages:
    @staticmethod
    def css(theme):
        is_dark = theme != "light"
        bg = "#1a1a1a" if is_dark else "#f4f4f4"
        card = "#2a2a2a" if is_dark else "#ffffff"
        txt = "white" if is_dark else "black"
        # We use double curly braces {{ }} here so Python f-strings don't crash
        return f"""
        body {{ font-family: 'Poppins', sans-serif; background: {bg}; color: {txt}; margin: 0; padding: 40px; }}
        .card {{ background: {card}; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-bottom: 20px; }}
        .btn {{ background: #0d6efd; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; display: inline-block; border: none; cursor: pointer; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; }}
        """

    @staticmethod
    def new_tab(data):
        s = data['settings']
        bg = s.get('bg_url', '')
        bg_style = f"background-image: url('{bg}');" if bg else "background: #121212;"
        
        # ALL CSS BRACES ARE DOUBLED BELOW TO FIX THE NameError
        return f"""
<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        body {{
            {bg_style}
            background-size: cover; background-position: center;
            font-family: 'Poppins', sans-serif; height: 100vh; margin: 0;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            color: white; overflow: hidden;
        }}
        .overlay {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.4); z-index: 1;
        }}
        .content {{ position: relative; z-index: 2; text-align: center; width: 80%; max-width: 800px; }}
        .search-container {{ width: 100%; margin-bottom: 40px; }}
        .search-input {{
            width: 100%; padding: 18px 30px; border-radius: 50px; border: none;
            background: rgba(255,255,255,0.2); backdrop-filter: blur(15px);
            color: white; font-size: 1.2rem; outline: none; transition: 0.3s;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
        }}
        .search-input:focus {{ background: rgba(255,255,255,0.3); }}
        .shortcuts {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 20px; width: 100%;
        }}
        .tile {{
            background: rgba(0,0,0,0.5); backdrop-filter: blur(10px);
            padding: 20px; border-radius: 20px; text-decoration: none; color: white;
            transition: 0.3s; border: 1px solid rgba(255,255,255,0.1);
            display: flex; flex-direction: column; align-items: center;
        }}
        .tile:hover {{ transform: translateY(-10px); background: rgba(255,255,255,0.1); }}
        .tile i {{ font-size: 2.5rem; margin-bottom: 10px; }}
        .navit-badge {{
            position: fixed; top: 20px; right: 20px; background: gold; color: black;
            padding: 8px 15px; border-radius: 20px; font-weight: bold; z-index: 10;
        }}
    </style>
</head>
<body>
    <div class="overlay"></div>
    <div class="navit-badge">🪙 {data['navits']} Navits</div>
    <div class="content">
        <h1 style="font-size: 4rem; margin-bottom: 30px; text-shadow: 0 4px 10px rgba(0,0,0,0.5);">Navi</h1>
        <div class="search-container">
            <input type="text" class="search-input" placeholder="Search the web..." 
                onkeydown="if(event.key==='Enter') window.location.href='app://navigate?url='+encodeURIComponent(this.value)">
        </div>
        <div class="shortcuts">
            <a href="navi://pw" class="tile"><i class="material-icons">language</i><span>Sites</span></a>
            <a href="navi://cws" class="tile"><i class="material-icons">extension</i><span>Extensions</span></a>
            <a href="navi://store" class="tile"><i class="material-icons">store</i><span>Store</span></a>
            <a href="navi://history" class="tile"><i class="material-icons">history</i><span>History</span></a>
            <a href="navi://settings" class="tile"><i class="material-icons">settings</i><span>Settings</span></a>
        </div>
    </div>
</body>
</html>
"""

class NaviWebPage(QWebEnginePage):
    def __init__(self, view):
        super().__init__(view)
        self._view_ref = view

    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if url.scheme() in ["navi", "app"]:
            if self._view_ref and hasattr(self._view_ref, 'main'):
                self._view_ref.main.handle_cmd(url.toString(), self._view_ref)
            return False
        return super().acceptNavigationRequest(url, _type, isMainFrame)

class BrowserTab(QWebEngineView):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setPage(NaviWebPage(self))
        self.page().loadFinished.connect(self.on_load)

    def on_load(self, ok):
        if not ok: return
        # Inject Extensions
        for ext in self.main.data['extensions'].values():
            if ext.get('active'): self.page().runJavaScript(ext['code'])
        # Handle Rewards
        u = self.url().toString()
        if "google.com" in u or "bing.com" in u:
            self.main.reward(1)

    def createWindow(self, _type): return self.main.add_tab()

class CodeEditor(QWidget):
    def __init__(self, main, mode="site", key=None):
        super().__init__()
        self.main, self.mode, self.key = main, mode, key
        self.setWindowTitle(f"Navi {mode.title()} Editor")
        self.resize(700, 500)
        layout = QVBoxLayout()
        self.name_field = QLineEdit(); self.name_field.setPlaceholderText("Name")
        self.code_field = QTextEdit(); self.code_field.setPlaceholderText("Enter HTML/JS Code...")
        if key:
            self.name_field.setText(key); self.name_field.setReadOnly(True)
            src = main.data['sites' if mode=="site" else 'extensions'].get(key, {})
            self.code_field.setText(src.get('html_content', src.get('code', '')))
        
        save_btn = QPushButton("Save & Deploy")
        save_btn.clicked.connect(self.save)
        layout.addWidget(QLabel("Name:"))
        layout.addWidget(self.name_field)
        layout.addWidget(QLabel("Code:"))
        layout.addWidget(self.code_field)
        layout.addWidget(save_btn)
        self.setLayout(layout)

    def save(self):
        n = self.name_field.text().strip()
        c = self.code_field.toPlainText()
        if not n: return
        if self.mode == "site":
            suf = self.main.data['settings']['suffix']
            full_n = n if n.endswith(suf) else n + suf
            self.main.data['sites'][full_n] = {"title": n, "html_content": c}
        else:
            self.main.data['extensions'][n] = {"code": c, "active": True}
        self.main.save_data()
        self.close()

class NaviBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Navi Browser Ultimate v7.1")
        self.resize(1200, 850)
        
        self.data = {
            'sites': {}, 'extensions': {}, 'history': [], 'downloads': [],
            'settings': {'theme': 'dark', 'engine': 'Google', 'suffix': '.pw-navi', 'mode': 'modern', 'bg_url': '', 'wholesome': True},
            'navits': 0, 'inventory': [], 'last_active': time.time(), 'last_reward': 0
        }
        self.load_data()
        self.setup_ui()
        self.apply_theme()
        self.add_tab(QUrl("local://navi/"))

    def setup_ui(self):
        tb = QToolBar(); tb.setMovable(False); self.addToolBar(tb)
        self.url_bar = QLineEdit(); self.url_bar.returnPressed.connect(self.navigate)
        
        back = QPushButton("chevron_left"); back.clicked.connect(lambda: self.tabs.currentWidget().back())
        next_ = QPushButton("chevron_right"); next_.clicked.connect(lambda: self.tabs.currentWidget().forward())
        re = QPushButton("refresh"); re.clicked.connect(lambda: self.tabs.currentWidget().reload())
        
        tb.addWidget(back); tb.addWidget(next_); tb.addWidget(re); tb.addWidget(self.url_bar)
        
        self.tabs = QTabWidget(); self.tabs.setTabsClosable(True); self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(lambda i: self.tabs.removeTab(i) if self.tabs.count() > 1 else None)
        self.tabs.currentChanged.connect(self.sync_url)
        self.setCentralWidget(self.tabs)

    def add_tab(self, url=None, label="New Tab"):
        if not url: url = QUrl("local://navi/")
        view = BrowserTab(self); view.setUrl(url)
        view.urlChanged.connect(lambda q, v=view: self.sync_url_for(q, v))
        view.titleChanged.connect(lambda t, v=view: self.tabs.setTabText(self.tabs.indexOf(v), t[:15]))
        idx = self.tabs.addTab(view, label); self.tabs.setCurrentIndex(idx)
        return view

    def navigate(self):
        txt = self.url_bar.text().strip(); b = self.tabs.currentWidget()
        if not b: return
        if txt.startswith("navi://"): self.handle_cmd(txt, b)
        elif txt.endswith(self.data['settings']['suffix']):
            site = self.data['sites'].get(txt)
            if site: b.setHtml(site['html_content'], QUrl(f"local://{txt}"))
        else:
            if "." not in txt: u = QUrl(get_search_url(self.data['settings']['engine'], txt))
            else: u = QUrl(txt if "://" in txt else "https://" + txt)
            b.setUrl(u)

    def sync_url_for(self, q, v):
        if v == self.tabs.currentWidget():
            u = q.toString()
            self.url_bar.setText("" if u == "local://navi/" else u)

    def sync_url(self, i):
        if i >= 0: self.sync_url_for(self.tabs.widget(i).url(), self.tabs.widget(i))

    def handle_cmd(self, url_str, view):
        cmd = url_str.replace("navi://", "").replace("app://", "").strip("/")
        
        if cmd.startswith("navigate?url="):
            target = QUrl.fromPercentEncoding(url_str.split("url=")[1].encode())
            self.url_bar.setText(target); self.navigate(); return

        if cmd in ["", "home", "newtab"]:
            view.setHtml(InternalPages.new_tab(self.data), QUrl("local://navi/"))
        
        elif cmd == "pw":
            items = "".join([f"<div class='card'><b>{k}</b><br><a href='navi://pw/edit/{k}' class='btn'>Edit</a> <a href='{k}' class='btn'>Visit</a></div>" for k in self.data['sites']])
            view.setHtml(f"<html><head><style>{InternalPages.css(self.data['settings']['theme'])}</style></head><body><h1>My Sites</h1><button onclick=\"window.location.href='navi://pw/new'\" class='btn'>+ New Site</button><br><br><div class='grid'>{items}</div></body></html>", QUrl("local://pw"))
        
        elif cmd == "pw/new": self.editor = CodeEditor(self, "site"); self.editor.show()
        elif cmd.startswith("pw/edit/"): self.editor = CodeEditor(self, "site", url_str.split("edit/")[1]); self.editor.show()
        
        elif cmd == "cws":
            items = "".join([f"<div class='card'><b>{k}</b><br><a href='navi://cws/toggle/{k}' class='btn'>Toggle ({v['active']})</a></div>" for k,v in self.data['extensions'].items()])
            view.setHtml(f"<html><head><style>{InternalPages.css(self.data['settings']['theme'])}</style></head><body><h1>Extensions</h1><button onclick=\"window.location.href='navi://cws/new'\" class='btn'>+ Create Extension</button><br><br><div class='grid'>{items}</div></body></html>", QUrl("local://cws"))
        
        elif cmd == "cws/new": self.editor = CodeEditor(self, "ext"); self.editor.show()
        elif cmd.startswith("cws/toggle/"):
            n = url_str.split("toggle/")[1]
            if n in self.data['extensions']: self.data['extensions'][n]['active'] = not self.data['extensions'][n]['active']
            self.save_data(); self.handle_cmd("navi://cws", view)

        elif cmd == "store":
            items = "<div class='card'><h3>Cyberpunk Theme</h3><p>Cost: 100 Navits</p><button class='btn'>Buy</button></div>"
            view.setHtml(f"<html><head><style>{InternalPages.css(self.data['settings']['theme'])}</style></head><body><h1>Store</h1><p>Balance: {self.data['navits']}</p><div class='grid'>{items}</div></body></html>", QUrl("local://store"))

        elif cmd == "settings":
            s = self.data['settings']
            view.setHtml(f"<html><head><style>{InternalPages.css(s['theme'])}</style></head><body><h1>Settings</h1><div class='card'><h3>Theme</h3><a href='navi://set/theme/dark' class='btn'>Dark</a> <a href='navi://set/theme/light' class='btn'>Light</a></div><div class='card'><h3>Search Engine</h3><p>Current: {s['engine']}</p></div></body></html>", QUrl("local://settings"))

        elif cmd.startswith("set/theme/"):
            self.data['settings']['theme'] = url_str.split("theme/")[1]
            self.apply_theme(); self.save_data(); self.handle_cmd("navi://settings", view)

    def reward(self, amt):
        if time.time() - self.data['last_reward'] > 60:
            self.data['navits'] += amt
            self.data['last_reward'] = time.time()
            self.save_data()

    def apply_theme(self):
        self.setStyleSheet(BrowserStyles.get(self.data['settings']['theme'], self.data['settings']['mode']))

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    d = json.load(f)
                    self.data.update(d)
                    if 'wholesome' not in self.data['settings']: self.data['settings']['wholesome'] = True
            except: pass

    def save_data(self):
        with open(DATA_FILE, 'w') as f: json.dump(self.data, f)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NaviBrowser()
    window.show()
    sys.exit(app.exec())

