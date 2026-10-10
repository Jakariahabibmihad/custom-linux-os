#!/usr/bin/env python3
"""Custom Linux OS One UI-style app drawer: searchable, scrollable, widget manager."""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import subprocess, os, re, json, time, base64, webbrowser, urllib.parse

HOME = Path.home()
STATE_FILE = HOME / ".local/share/aladin-os/drawer.json"
PREFS_FILE = HOME / ".local/share/aladin-os/settings.json"
SPICES = {
    "Applets": "https://cinnamon-spices.linuxmint.com/applets",
    "Desklets": "https://cinnamon-spices.linuxmint.com/desklets",
    "Extensions": "https://cinnamon-spices.linuxmint.com/extensions",
    "Themes": "https://cinnamon-spices.linuxmint.com/themes",
}
MOODS = {
    "Midnight Ice": ("#0b1018", "#eef4ff", "#a7b8d0", "#8bbcff", "#172233", "#304764"),
    "Ocean Deep": ("#08141b", "#e8faff", "#a3c6d2", "#55cbe8", "#102531", "#285365"),
    "Emerald Circuit": ("#08140f", "#e9fff6", "#a9d4c4", "#66ddb0", "#12251d", "#2a5442"),
    "Violet Nebula": ("#100d18", "#f4edff", "#c2b4db", "#ba9cff", "#21182f", "#453263"),
    "Crimson Pulse": ("#170b11", "#fff0f3", "#d8aeb8", "#ff819b", "#29151e", "#56303c"),
    "Amber Glow": ("#171208", "#fff7e9", "#d9c7a7", "#f4c16f", "#292113", "#594523"),
    "Arctic Silver": ("#e8edf4", "#273244", "#657286", "#4f76b2", "#f7f9fc", "#d2dbe8"),
    "OLED Pure": ("#030405", "#f0f4fc", "#9ea8b9", "#c1d5f4", "#0e1218", "#293546"),
    "Mint Glass": ("#101713", "#eff8f0", "#aabbb0", "#87d7a5", "#18251d", "#80bd91"),
}
ICON_ROOTS = [
    Path("/usr/share/icons/Papirus-Dark/64x64/apps"),
    Path("/usr/share/icons/Papirus-Dark/48x48/apps"),
    Path("/usr/share/icons/Papirus-Dark/32x32/apps"),
    Path("/usr/share/icons/Papirus-Dark/scalable/apps"),
    Path("/usr/share/icons/hicolor/64x64/apps"),
    Path("/usr/share/icons/hicolor/48x48/apps"),
    Path("/usr/share/icons/hicolor/32x32/apps"),
    Path("/usr/share/icons/hicolor/scalable/apps"),
    Path("/usr/share/pixmaps"),
]
try:
    import gi
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf
except Exception:
    GdkPixbuf = None

def load_state():
    try:
        val = json.loads(STATE_FILE.read_text())
        if isinstance(val, dict):
            return {"favorites": val.get("favorites", []), "recent": val.get("recent", [])}
    except Exception:
        pass
    return {"favorites": [], "recent": []}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

def icon_path(name):
    if not name:
        return None
    p = Path(name)
    if p.is_absolute() and p.is_file():
        return p
    stem = p.stem if p.suffix.lower() in (".svg", ".png", ".xpm") else name
    for root in ICON_ROOTS:
        for ext in (".svg", ".png", ".xpm"):
            candidate = root / (stem + ext)
            if candidate.is_file():
                return candidate
    return None

def load_apps():
    result, seen = [], set()
    paths = [Path("/usr/share/applications"), HOME / ".local/share/applications"]
    for base in paths:
        if not base.exists():
            continue
        try:
            files = list(base.glob("*.desktop"))
        except OSError:
            continue
        for f in files:
            try:
                text = f.read_text(errors="ignore")
                sec = text.split("[Desktop Entry]", 1)[1].split("\n[", 1)[0]
                data = {}
                for line in sec.splitlines():
                    if "=" in line and not line.lstrip().startswith("#"):
                        k, v = line.split("=", 1)
                        # Always prefer the unlocalized desktop-entry key (Name=).
                        # Localized keys such as Name[bn]= can otherwise overwrite it
                        # and make the drawer follow the system language unexpectedly.
                        if "[" in k or "]" in k:
                            continue
                        data[k] = v
                name = data.get("Name", "").strip()
                if (not name or data.get("NoDisplay","false").lower() == "true"
                    or data.get("Hidden","false").lower() == "true"
                    or data.get("Type","Application") != "Application"):
                    continue
                if f.name.lower() in seen:
                    continue
                seen.add(f.name.lower())
                cats = data.get("Categories", "Utility;").split(";")
                category = next((c for c in cats if c in ("Network","Office","Graphics","AudioVideo","Game","Education","Development","System","Utility","Settings","Science")), cats[0] if cats else "Other")
                result.append({"id":str(f), "name":name, "icon":data.get("Icon","application-x-executable"), "category":category})
            except (OSError, IndexError, ValueError):
                continue
    return sorted(result, key=lambda a:a["name"].casefold())

class Drawer:
    def __init__(self, root):
        self.root = root
        self.state = load_state()
        self.apps = []
        self.icon_cache = {}
        self.search_job = None
        self.page = "Apps"
        self.prefs = self.load_prefs()
        mood = self.prefs.get("mood", "Midnight Ice")
        self.bg, self.fg, self.muted, self.accent, self.card_bg, self.border = MOODS.get(mood, MOODS["Midnight Ice"])
        if re.fullmatch(r"#[0-9a-fA-F]{6}", str(self.prefs.get("accent",""))):
            self.accent = self.prefs["accent"]
        self.root.title("Custom Linux OS • App Drawer")
        self.root.geometry("940x800")
        self.root.minsize(700, 560)
        self.root.configure(bg=self.bg)
        self.style = ttk.Style(); self.style.theme_use("clam")
        self.style.configure("TFrame", background=self.bg)
        self.style.configure("TLabel", background=self.bg, foreground=self.fg, font=("Sans",10))
        self.style.configure("Hero.TLabel", background=self.bg, foreground=self.fg, font=("Sans",24,"bold"))
        self.style.configure("Sub.TLabel", background=self.bg, foreground=self.muted, font=("Sans",10))
        self.style.configure("TEntry", fieldbackground=self.card_bg, foreground=self.fg, insertcolor=self.fg, bordercolor=self.border, padding=10)
        self.style.configure("TCombobox", fieldbackground=self.card_bg, background=self.card_bg, foreground=self.fg, arrowcolor=self.fg, bordercolor=self.border, padding=7)
        self.style.map("TCombobox", fieldbackground=[("readonly",self.card_bg)], foreground=[("readonly",self.fg)])
        self.style.configure("TButton", background=self.card_bg, foreground=self.fg, padding=8, borderwidth=1, bordercolor=self.border)
        self.style.map("TButton", background=[("active",self.border)], foreground=[("active",self.fg)])
        self.build_header()
        self.build_tabs()
        self.build_scroll_area()
        self.apps = load_apps()
        self.update_count()
        self.switch_page("Apps")
        self.root.bind("<Escape>", lambda e:self.root.destroy())
        self.root.bind("<Control-l>", lambda e:self.entry.focus_set())
        self.root.bind("<Control-r>", lambda e:self.refresh())

    def power_action(self, action):
        labels = {"poweroff": "shut down", "reboot": "restart"}
        label = labels.get(action)
        if not label:
            return
        if not messagebox.askyesno("Confirm power action", f"Are you sure you want to {label} this computer?", parent=self.root):
            return
        try:
            subprocess.Popen(["systemctl", action], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except Exception as exc:
            messagebox.showerror("Power action failed", str(exc), parent=self.root)

    def load_prefs(self):
        try: return json.loads(PREFS_FILE.read_text())
        except Exception: return {}

    def build_header(self):
        header = tk.Frame(self.root, bg=self.bg, padx=24, pady=20)
        header.pack(fill="x")
        top = tk.Frame(header, bg=self.bg); top.pack(fill="x")
        title = tk.Label(top, text="CUSTOM LINUX OS", bg=self.bg, fg=self.fg, font=("Sans",11,"bold"))
        title.pack(side="left", anchor="w")
        power = tk.Frame(top, bg=self.bg); power.pack(side="right")
        tk.Button(power,text="⏻  Shut Down",command=lambda:self.power_action("poweroff"),
                  bg=self.card_bg,fg=self.fg,activebackground=self.border,activeforeground=self.fg,
                  relief="flat",bd=0,padx=12,pady=7,cursor="hand2",font=("Sans",9,"bold")).pack(side="left",padx=(0,6))
        tk.Button(power,text="↻  Restart",command=lambda:self.power_action("reboot"),
                  bg=self.card_bg,fg=self.fg,activebackground=self.border,activeforeground=self.fg,
                  relief="flat",bd=0,padx=12,pady=7,cursor="hand2",font=("Sans",9,"bold")).pack(side="left")
        tk.Label(header, text="Find anything.", bg=self.bg, fg=self.fg, font=("Sans",27,"bold")).pack(anchor="w", pady=(10,0))
        self.subtitle = tk.Label(header, text="Your apps, widgets and desktop tools in one place.", bg=self.bg, fg=self.muted, font=("Sans",10))
        self.subtitle.pack(anchor="w", pady=(2,13))
        searchrow = tk.Frame(header,bg=self.bg); searchrow.pack(fill="x")
        self.placeholder = "Search apps or type a Google query…"
        self.query = tk.StringVar(value=self.placeholder)
        self.entry = tk.Entry(searchrow,textvariable=self.query,bg=self.card_bg,fg=self.muted,
                              insertbackground=self.fg,relief="flat",bd=0,highlightthickness=1,
                              highlightbackground=self.border,highlightcolor=self.accent,font=("Sans",11))
        self.entry.pack(side="left",fill="x",expand=True,ipady=11,padx=(0,4))
        self.entry.bind("<FocusIn>",self.clear_placeholder)
        self.entry.bind("<FocusOut>",self.restore_placeholder)
        self.entry.bind("<KeyRelease>",self.on_search)
        self.entry.bind("<Return>",self.google_search)
        ttk.Button(searchrow,text="Google ↗",command=self.google_search).pack(side="left",padx=(6,0))
        ttk.Button(searchrow,text="↻ Refresh",command=self.refresh).pack(side="left",padx=(8,0))
        filterrow = tk.Frame(header,bg=self.bg); filterrow.pack(fill="x",pady=(10,0))
        tk.Label(filterrow,text="Category",bg=self.bg,fg=self.muted,font=("Sans",9)).pack(side="left",padx=(0,8))
        self.category = tk.StringVar(value="All categories")
        self.combo = ttk.Combobox(filterrow,textvariable=self.category,state="readonly",width=20,values=["All categories"])
        self.combo.pack(side="left")
        self.combo.bind("<<ComboboxSelected>>",lambda e:self.render())
        self.count = tk.Label(filterrow,text="",bg=self.bg,fg=self.muted,font=("Sans",9))
        self.count.pack(side="right")

    def build_tabs(self):
        nav = tk.Frame(self.root,bg=self.bg,padx=24,pady=0)
        nav.pack(fill="x",padx=24,pady=(0,12))
        self.tab_buttons = {}
        for name, symbol in [("Apps","▦"),("Favorites","★"),("Recent","◷"),("Widgets","＋")]:
            b=tk.Button(nav,text=f"{symbol}  {name}",relief="flat",bd=0,padx=16,pady=9,cursor="hand2",
                        bg=self.card_bg,fg=self.fg,activebackground=self.accent,activeforeground=self.bg,
                        font=("Sans",10,"bold"),command=lambda n=name:self.switch_page(n))
            b.pack(side="left",padx=(0,7))
            self.tab_buttons[name]=b

    def build_scroll_area(self):
        holder=tk.Frame(self.root,bg=self.bg)
        holder.pack(fill="both",expand=True,padx=18,pady=(0,14))
        self.canvas=tk.Canvas(holder,bg=self.bg,highlightthickness=0,bd=0)
        self.scrollbar=ttk.Scrollbar(holder,orient="vertical",command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right",fill="y")
        self.canvas.pack(side="left",fill="both",expand=True)
        self.inner=tk.Frame(self.canvas,bg=self.bg)
        self.window=self.canvas.create_window((0,0),window=self.inner,anchor="nw")
        self.inner.bind("<Configure>",lambda e:self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",lambda e:self.canvas.itemconfigure(self.window,width=e.width))
        self.canvas.bind_all("<MouseWheel>",self.on_wheel)
        self.canvas.bind_all("<Button-4>",lambda e:self.canvas.yview_scroll(-3,"units"))
        self.canvas.bind_all("<Button-5>",lambda e:self.canvas.yview_scroll(3,"units"))
        self.canvas.bind_all("<Shift-MouseWheel>",self.on_shift_wheel)

    def on_wheel(self,event):
        if event.delta:
            self.canvas.yview_scroll(-max(1,int(abs(event.delta)/120))*(1 if event.delta>0 else -1),"units")
    def on_shift_wheel(self,event):
        self.canvas.xview_scroll(-1 if event.delta>0 else 1,"units")

    def switch_page(self,name):
        self.page=name
        for n,b in self.tab_buttons.items():
            b.configure(bg=self.accent if n==name else self.card_bg,fg=self.bg if n==name else self.fg)
        self.combo.configure(state="readonly" if name in ("Apps","Favorites","Recent") else "disabled")
        if name=="Widgets":
            self.subtitle.configure(text="Add applets, desklets, extensions and themes to your Cinnamon desktop.")
        elif name=="Favorites":
            self.subtitle.configure(text="Your pinned apps, ready when you need them.")
        elif name=="Recent":
            self.subtitle.configure(text="Quickly return to apps you launched recently.")
        else:
            self.subtitle.configure(text="A scrollable app library with search, categories and favorites.")
        self.canvas.yview_moveto(0)
        self.render()

    def clear_placeholder(self,event=None):
        if self.query.get()==self.placeholder:
            self.query.set("")
            self.entry.configure(fg=self.fg)

    def restore_placeholder(self,event=None):
        if not self.query.get().strip():
            self.query.set(self.placeholder)
            self.entry.configure(fg=self.muted)
            self.on_search()

    def google_search(self,event=None):
        """Search Google using the desktop's configured default browser."""
        query=self.query.get().strip()
        if not query or query==self.placeholder:
            self.subtitle.configure(text="Type a search query first, then press Enter or Google.")
            self.entry.focus_set()
            return "break"
        url="https://www.google.com/search?"+urllib.parse.urlencode({"q":query})
        try:
            # xdg-open delegates to the user's configured default browser (e.g. Brave).
            subprocess.Popen(["xdg-open",url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            self.subtitle.configure(text="Searching Google in your default browser…")
        except Exception as exc:
            self.subtitle.configure(text="Could not open your default browser: "+str(exc))
        return "break"

    def on_search(self,event=None):
        if self.search_job:
            try:self.root.after_cancel(self.search_job)
            except Exception:pass
        self.search_job=self.root.after(180,self.render)

    def update_count(self):
        cats=sorted(set(a["category"] for a in self.apps))
        self.combo.configure(values=["All categories"]+cats)
        self.count.configure(text=f"{len(self.apps)} apps installed")

    def refresh(self):
        self.apps=load_apps()
        self.update_count()
        self.render()

    def image_for(self, name):
        if name in self.icon_cache:return self.icon_cache[name]
        img=None
        if GdkPixbuf is not None:
            path=icon_path(name)
            if path:
                try:
                    pix=GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path),48,48,True)
                    ok,buf=pix.save_to_bufferv("png",[],[])
                    img=tk.PhotoImage(data=base64.b64encode(bytes(buf)).decode("ascii"))
                except Exception:img=None
        self.icon_cache[name]=img
        return img

    def launch(self, app):
        try:
            subprocess.Popen(["gio","launch",app["id"]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            rid=app["id"]
            self.state["recent"]=[rid]+[x for x in self.state["recent"] if x!=rid]
            self.state["recent"]=self.state["recent"][:18]
            save_state(self.state)
            if self.page=="Recent":self.render()
        except Exception as exc:
            self.subtitle.configure(text=f"Could not open {app['name']}: {exc}")

    def toggle_favorite(self,app):
        fav=self.state["favorites"]
        if app["id"] in fav:fav.remove(app["id"])
        else:fav.insert(0,app["id"])
        self.state["favorites"]=fav
        save_state(self.state)
        self.render()

    def clear_content(self):
        for w in self.inner.winfo_children():w.destroy()
        self.images=[]

    def section_title(self,text,sub=None):
        box=tk.Frame(self.inner,bg=self.bg)
        box.pack(fill="x",padx=8,pady=(8,7))
        tk.Label(box,text=text,bg=self.bg,fg=self.fg,font=("Sans",14,"bold")).pack(anchor="w")
        if sub:tk.Label(box,text=sub,bg=self.bg,fg=self.muted,font=("Sans",9)).pack(anchor="w",pady=(2,0))

    def tile(self,parent,app,index,columns=4):
        fav=app["id"] in self.state["favorites"]
        frame=tk.Frame(parent,bg=self.card_bg,highlightbackground=self.border,highlightthickness=1)
        frame.grid(row=index//columns,column=index%columns,sticky="nsew",padx=5,pady=5)
        parent.grid_columnconfigure(index%columns,weight=1,uniform="tiles")
        row=tk.Frame(frame,bg=self.card_bg);row.pack(fill="x",padx=6,pady=(5,0))
        btnstar=tk.Button(row,text="★" if fav else "☆",relief="flat",bd=0,cursor="hand2",
                          bg=self.card_bg,fg=self.accent,activebackground=self.card_bg,activeforeground=self.fg,
                          highlightthickness=0,takefocus=0,font=("Sans",12),command=lambda a=app:self.toggle_favorite(a))
        btnstar.pack(side="right")
        img=self.image_for(app["icon"])
        self.images.append(img)
        label = app["name"] if img is not None else "◈\n" + app["name"]
        btn=tk.Button(frame,text=label,image=img,compound="top" if img is not None else "center",wraplength=130,justify="center",
                      bg=self.card_bg,fg=self.fg,activebackground=self.border,activeforeground=self.fg,
                      relief="flat",bd=0,highlightthickness=0,takefocus=0,cursor="hand2",font=("Sans",10),height=3 if img is None else 0,
                      command=lambda a=app:self.launch(a))
        btn.pack(fill="both",expand=True,padx=4,pady=(0,6),ipady=8)
        frame.bind("<Double-Button-1>",lambda e,a=app:self.launch(a))

    def render(self):
        self.search_job=None
        self.clear_content()
        if self.page=="Widgets":
            self.render_widgets()
            return
        raw_query=self.query.get()
        q="" if raw_query==self.placeholder else raw_query.casefold().strip()
        category=self.category.get()
        byid={a["id"]:a for a in self.apps}
        if self.page=="Favorites":
            source=[byid[x] for x in self.state["favorites"] if x in byid]
        elif self.page=="Recent":
            source=[byid[x] for x in self.state["recent"] if x in byid]
        else: source=self.apps
        rows=[a for a in source if (not q or q in a["name"].casefold() or q in a["category"].casefold()) and (category=="All categories" or a["category"]==category)]
        if self.page=="Apps" and not q and category=="All categories":
            favorites=[a for a in rows if a["id"] in self.state["favorites"]][:4]
            if favorites:
                self.section_title("Pinned", "Your favorite apps")
                self.render_grid(favorites,4)
                self.section_title("All apps", f"{len(rows)} applications • scroll to explore")
            else:
                self.section_title("All apps", f"{len(rows)} applications • scroll to explore")
        else:
            self.section_title(self.page, f"{len(rows)} apps")
        self.render_grid(rows if self.page!="Apps" or q or category!="All categories" else rows,4)
        if not rows:
            tk.Label(self.inner,text="Nothing here yet",bg=self.bg,fg=self.muted,font=("Sans",13)).pack(anchor="w",padx=10,pady=24)
            if self.page=="Favorites":
                tk.Label(self.inner,text="Tap ☆ on an app to pin it here.",bg=self.bg,fg=self.muted,font=("Sans",10)).pack(anchor="w",padx=10)

    def render_grid(self,rows,columns):
        grid=tk.Frame(self.inner,bg=self.bg)
        grid.pack(fill="x",padx=3,pady=(0,10))
        for c in range(columns):grid.grid_columnconfigure(c,weight=1,uniform="grid")
        for i,a in enumerate(rows):self.tile(grid,a,i,columns)

    def manager_card(self,parent,title,desc,button,url=None,command=None):
        frame=tk.Frame(parent,bg=self.card_bg,highlightbackground=self.border,highlightthickness=1)
        frame.pack(fill="x",padx=4,pady=5)
        body=tk.Frame(frame,bg=self.card_bg);body.pack(fill="x",padx=15,pady=12)
        tk.Label(body,text=title,bg=self.card_bg,fg=self.fg,font=("Sans",13,"bold")).pack(anchor="w")
        tk.Label(body,text=desc,bg=self.card_bg,fg=self.muted,font=("Sans",10),wraplength=630,justify="left").pack(anchor="w",pady=(4,9))
        fn=command if command else (lambda u=url:webbrowser.open(u))
        tk.Button(body,text=button,command=fn,bg=self.accent,fg=self.bg,activebackground=self.border,activeforeground=self.fg,
                  relief="flat",bd=0,padx=14,pady=8,cursor="hand2",font=("Sans",10,"bold")).pack(anchor="w")

    def manager(self,module):
        try:subprocess.Popen(["cinnamon-settings",module],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        except Exception as exc:self.subtitle.configure(text=f"Could not open {module} manager: {exc}")

    def render_widgets(self):
        self.section_title("Personalize your desktop", "Enable, remove or configure installed Cinnamon components.")
        managers=tk.Frame(self.inner,bg=self.bg); managers.pack(fill="x",padx=3)
        self.manager_card(managers,"＋  Add desklets","Place desktop widgets such as clocks, notes, weather and system monitors.","Open Desklet Manager",command=lambda:self.manager("desklets"))
        self.manager_card(managers,"▦  Add applets","Add panel indicators, menus, network tools and other panel controls.","Open Applet Manager",command=lambda:self.manager("applets"))
        self.manager_card(managers,"◇  Extensions","Enable or disable Cinnamon shell enhancements.","Manage Extensions",command=lambda:self.manager("extensions"))
        self.manager_card(managers,"◐  Themes & appearance","Switch themes, icons, cursors and shell styling.","Open Theme Settings",command=lambda:self.manager("themes"))
        self.section_title("Get more from Cinnamon Spices", "Community-made widgets and themes. Open a catalog, then install items from Cinnamon's manager.")
        spices=tk.Frame(self.inner,bg=self.bg);spices.pack(fill="x",padx=3)
        self.manager_card(spices,"Applets catalog","Network, sound, menus, panel indicators and more.","Browse Applets",url=SPICES["Applets"])
        self.manager_card(spices,"Desklets catalog","Desktop clocks, calendars, system monitors, notes and widgets.","Browse Desklets",url=SPICES["Desklets"])
        self.manager_card(spices,"Extensions catalog","More Cinnamon desktop behavior and workflow options.","Browse Extensions",url=SPICES["Extensions"])
        self.manager_card(spices,"Themes catalog","New colors, panel styles, icons and desktop looks.","Browse Themes",url=SPICES["Themes"])
        self.section_title("Custom Linux OS shortcuts", "Customize the mood and tune the dashboard, wallpaper and dock.")
        tools=tk.Frame(self.inner,bg=self.bg);tools.pack(fill="x",padx=3)
        self.manager_card(tools,"Custom Linux OS Control Center","Color moods, accent colors, dashboard widgets, wallpaper and dock options.","Open Control Center",
            command=lambda:subprocess.Popen(["/usr/bin/python3",str(HOME/".local/bin/aladin-control-center.py")],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
        self.manager_card(tools,"Refresh app list","Rescan desktop launchers after installing new software.","Refresh apps",command=self.refresh)

if __name__=="__main__":
    root=tk.Tk()
    drawer=Drawer(root)
    root.mainloop()
