#!/usr/bin/env python3
"""Custom Linux OS Control Center — color moods and desktop customization."""
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from pathlib import Path
import json, re, shutil, subprocess, time, xml.etree.ElementTree as ET

HOME = Path.home()
DESK = HOME / ".local/share/cinnamon/desklets/AladinOS@local"
CSS = DESK / "stylesheet.css"
CFG = HOME / ".local/share/aladin-os/settings.json"
WALL = HOME / "Pictures/Aladin"
THEME = HOME / ".themes/Aladin-OS-Futuristic"
DOCK = HOME / ".local/share/plank/themes/Aladin-OS-Futuristic/dock.theme"

MOODS = {
 "Midnight Ice":   {"base":"#101722","accent":"#8bbcff","fg":"#edf4ff","muted":"#a9b9cf","border":"#8eb8ec","wall":"#070a10","wall2":"#1e2a3d","light":False},
 "Ocean Deep":     {"base":"#0c1b25","accent":"#55cbe8","fg":"#e8faff","muted":"#a3c6d2","border":"#65d6ef","wall":"#061017","wall2":"#123949","light":False},
 "Emerald Circuit":{"base":"#0d1b17","accent":"#66ddb0","fg":"#e9fff6","muted":"#a9d4c4","border":"#69d6ad","wall":"#050e0b","wall2":"#164638","light":False},
 "Violet Nebula":  {"base":"#171321","accent":"#ba9cff","fg":"#f4edff","muted":"#c2b4db","border":"#b39ae8","wall":"#090711","wall2":"#36234f","light":False},
 "Crimson Pulse":  {"base":"#1d1118","accent":"#ff819b","fg":"#fff0f3","muted":"#d8aeb8","border":"#ee89a0","wall":"#10060b","wall2":"#4a1d2e","light":False},
 "Amber Glow":     {"base":"#1b1710","accent":"#f4c16f","fg":"#fff7e9","muted":"#d9c7a7","border":"#dcb66e","wall":"#100c05","wall2":"#49371a","light":False},
 "Arctic Silver":  {"base":"#e8edf4","accent":"#4f76b2","fg":"#273244","muted":"#657286","border":"#8b9db7","wall":"#d8e0ec","wall2":"#9facc2","light":True},
 "OLED Pure":      {"base":"#050609","accent":"#c1d5f4","fg":"#f0f4fc","muted":"#9ea8b9","border":"#90a8cb","wall":"#020304","wall2":"#18202d","light":False},
 "Mint Glass":     {"base":"#101713","accent":"#87d7a5","fg":"#eff8f0","muted":"#aabbb0","border":"#80bd91","wall":"#070d09","wall2":"#1d3827","light":False},
}
DEFAULT = {
 "mood":"Midnight Ice","accent":"#8bbcff","opacity":88,"radius":17,"scale":100,
 "font_scale":100,"border":42,"clock":"24-hour","compact":False,
 "glass_preset":"OLED Pure Glass",
 "gradient_style":"Aurora","gradient_intensity":42,"glow_effect":True,
 "smooth_animations":True,"glass_highlights":True,"accent_buttons":True,
 "dock_size":42,"dock_zoom":False,"wallpaper":"mood",
 "show_weather":True,"show_system":True,"show_ai":True,
 "applet_network":True,"applet_audio":True,"applet_system":True,
 "show_cpu_temp":True,"show_gpu_temp":True,"show_network_speed":True,
 "show_tasks":True,"show_places":True,"show_apps":True,"show_media":True,
 "show_search":True,"show_footer":True,"show_control_center":True,"show_quick_tools":True,"dock_autohide":True
}
def load():
    """Load preferences defensively so one stale/edited value cannot break the UI."""
    try:
        raw=json.loads(CFG.read_text())
        if not isinstance(raw,dict):
            raise ValueError("settings must be a JSON object")
        d={**DEFAULT,**raw}
    except (OSError, ValueError, TypeError):
        d=DEFAULT.copy()
    if d.get("mood") not in MOODS:
        d["mood"]=DEFAULT["mood"]
    if not re.fullmatch(r"#[0-9a-fA-F]{6}",str(d.get("accent",""))):
        d["accent"]=MOODS[d["mood"]]["accent"]
    numeric_ranges={
        "opacity":(10,100), "radius":(6,30), "scale":(75,110),
        "font_scale":(80,120), "border":(8,80), "dock_size":(32,60),
        "gradient_intensity":(0,100),
    }
    for key,(low,high) in numeric_ranges.items():
        try:
            value=int(d[key])
        except (ValueError,TypeError,OverflowError):
            value=int(DEFAULT[key])
        d[key]=max(low,min(high,value))
    if d.get("clock") not in ("24-hour","12-hour"):
        d["clock"]=DEFAULT["clock"]
    if d.get("wallpaper") not in ("mood","Black gradient","Silver glass","Mint default"):
        d["wallpaper"]=DEFAULT["wallpaper"]
    if d.get("gradient_style") not in ("Aurora","Diagonal glass","Radial glow","Linear minimal","Ice crystal"):
        d["gradient_style"]=DEFAULT["gradient_style"]
    if d.get("glass_preset") not in ("OLED Pure Glass","Linux Mint Glass","Frosted Mint","Clear Glass"):
        d["glass_preset"]=DEFAULT["glass_preset"]
    boolean_keys=("compact","dock_zoom","dock_autohide","glow_effect","smooth_animations",
        "glass_highlights","accent_buttons","show_weather","show_system",
        "show_cpu_temp","show_gpu_temp","show_network_speed",
        "show_ai","show_tasks","show_places","show_apps","show_media","show_search",
        "show_footer","show_control_center","show_quick_tools",
        "applet_network","applet_audio","applet_system")
    for key in boolean_keys:
        value=d.get(key,DEFAULT.get(key,False))
        if isinstance(value,bool):
            pass
        elif isinstance(value,int) and value in (0,1):
            value=bool(value)
        elif isinstance(value,str) and value.lower() in ("true","false","1","0","yes","no"):
            value=value.lower() in ("true","1","yes")
        else:
            value=bool(DEFAULT.get(key,False))
        d[key]=value
    return d
def run(cmd):
    try: subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
    except Exception: pass
def rgb(hexv):
    h = hexv.lstrip("#")
    return tuple(int(h[i:i+2],16) for i in (0,2,4))
def rgba(hexv, a):
    r,g,b = rgb(hexv)
    return f"rgba({r},{g},{b},{max(0,min(1,a)):.2f})"

class AladinCustomizer:
    def __init__(self, root):
        self.root = root
        self.cfg = load()
        self.vars = {}
        root.title("Custom Linux OS • Control Center")
        root.geometry("860x790")
        root.minsize(720,660)
        root.configure(bg="#0d1118")
        st = ttk.Style(); st.theme_use("clam")
        st.configure("TFrame", background="#0d1118")
        st.configure("TLabel", background="#0d1118", foreground="#e7edf8", font=("Sans",10))
        st.configure("Title.TLabel", font=("Sans",23,"bold"), foreground="#f4f7ff")
        st.configure("Sub.TLabel", foreground="#a6b4c8")
        st.configure("TButton", background="#253246", foreground="#f2f6ff", padding=8)
        st.map("TButton", background=[("active","#3b5272")])
        st.configure("TCheckbutton", background="#0d1118", foreground="#e7edf8", indicatorcolor="#243246")
        st.map("TCheckbutton", background=[("active", "#0d1118")], foreground=[("disabled", "#66758b")])
        st.configure("TNotebook", background="#0d1118", borderwidth=0)
        st.configure("TNotebook.Tab", padding=[15,9], background="#182231", foreground="#d8e5f7", borderwidth=0)
        st.map("TNotebook.Tab", background=[("selected", "#30445e"), ("active", "#25364c")], foreground=[("selected", "#ffffff"), ("active", "#ffffff")])
        st.configure("TCombobox", fieldbackground="#17202d", background="#253246", foreground="#e7edf8", arrowcolor="#dce8f8", bordercolor="#465c7a", lightcolor="#465c7a", darkcolor="#0b111a")
        st.map("TCombobox", fieldbackground=[("readonly", "#17202d"), ("focus", "#202f43")], foreground=[("readonly", "#e7edf8")], selectbackground=[("readonly", "#30445e")], selectforeground=[("readonly", "#ffffff")])
        st.configure("Horizontal.TScale", background="#0d1118", troughcolor="#29394e", sliderlength=18, bordercolor="#0d1118")
        st.configure("TButton", relief="flat", borderwidth=1, bordercolor="#415675", lightcolor="#253246", darkcolor="#101722")
        head=ttk.Frame(root,padding=(22,18,22,7)); head.pack(fill="x")
        ttk.Label(head,text="CUSTOM LINUX OS",style="Title.TLabel").pack(anchor="w")
        ttk.Label(head,text="Control Center  •  Color moods, widgets, dock & desktop",style="Sub.TLabel").pack(anchor="w",pady=(2,0))
        self.note=tk.StringVar(value="Choose a color mood or customize every detail.")
        ttk.Label(root,textvariable=self.note,style="Sub.TLabel").pack(anchor="w",padx=24,pady=(0,7))
        nb=ttk.Notebook(root); nb.pack(fill="both",expand=True,padx=18,pady=4)
        appearance=ttk.Frame(nb,padding=17); dashboard=ttk.Frame(nb,padding=17); desktop=ttk.Frame(nb,padding=17); effects=ttk.Frame(nb,padding=17)
        nb.add(appearance,text="Color & Style"); nb.add(effects,text="Gradients & Effects"); nb.add(dashboard,text="Dashboard"); nb.add(desktop,text="Desktop & Dock")
        self.add_combo(appearance,"mood","Color mood",list(MOODS),0)
        self.add_color(appearance,"accent","Custom accent color",1)
        self.add_combo(appearance,"glass_preset","Glass preset",["OLED Pure Glass","Linux Mint Glass","Frosted Mint","Clear Glass"],2)
        self.add_scale(appearance,"opacity","Glass opacity",10,100,3,"%")
        self.add_scale(appearance,"radius","Card corner radius",6,30,4,"px")
        self.add_scale(appearance,"scale","Dashboard size",75,110,5,"%")
        self.add_scale(appearance,"font_scale","Typography size",80,120,6,"%")
        self.add_scale(appearance,"border","Glass border intensity",8,80,7,"%")
        self.add_combo(appearance,"clock","Clock format",["24-hour","12-hour"],8)
        self.add_check(appearance,"compact","Compact layout (less spacing)",9)
        ttk.Label(appearance,text="Glass presets: Linux Mint Glass uses Mint green (#87d7a5), dark translucent surfaces and soft green borders. Opacity controls the glass surface strength; lower values are clearer and darker.",style="Sub.TLabel",wraplength=680,justify="left").grid(row=10,column=0,columnspan=3,sticky="w",pady=(15,0))
        self.add_combo(effects,"gradient_style","Gradient preset",["Aurora","Diagonal glass","Radial glow","Linear minimal","Ice crystal"],0)
        self.add_scale(effects,"gradient_intensity","Gradient strength",0,100,1,"%")
        self.add_check(effects,"glow_effect","Soft accent glow on cards",2)
        self.add_check(effects,"glass_highlights","Glass highlight gradients",3)
        self.add_check(effects,"smooth_animations","Smooth hover transitions",4)
        self.add_check(effects,"accent_buttons","Gradient accent buttons",5)
        ttk.Label(effects,text="Aurora adds layered ice-blue light; Diagonal glass adds a clean diagonal sheen; Radial glow emphasizes the center; Linear minimal keeps gradients subtle; Ice crystal adds cool, multi-stop highlights. Lower strength keeps OLED blacks dominant.",style="Sub.TLabel",wraplength=650,justify="left").grid(row=6,column=0,columnspan=3,sticky="w",pady=(18,0))
        flags=[
          ("show_weather","Weather card"),("show_system","System monitor"),
          ("show_cpu_temp","CPU temperature"),("show_gpu_temp","GPU temperature"),
          ("show_network_speed","Internet speed (upload/download)"),
          ("show_ai","Local AI chat panel"),
          ("show_apps","App grid"),("show_media","Media shortcuts"),
          ("show_tasks","Tasks list"),("show_places","Places / map"),
          ("show_control_center","Control Center card"),("show_quick_tools","Focus & quick tools"),("show_search","Search field"),
          ("show_footer","Bottom action/status strip"),
          ("applet_network","Right-side applet: Network"),
          ("applet_audio","Right-side applet: Audio"),
          ("applet_system","Right-side applet: System Monitor")
        ]
        for i,(key,label) in enumerate(flags):
            self.add_check(dashboard,key,label,i)
        ttk.Label(dashboard,text="The App Menu stays pinned on the left. Toggle the optional applets here; Apply reloads the desklet. No applet close buttons are shown on the desktop.",style="Sub.TLabel",wraplength=650).grid(row=len(flags)+1,column=0,columnspan=2,sticky="w",pady=14)
        self.add_combo(desktop,"wallpaper","Wallpaper style",["mood","Black gradient","Silver glass","Mint default"],0)
        self.add_scale(desktop,"dock_size","Dock icon size",32,60,1,"px")
        self.add_check(desktop,"dock_zoom","Enable dock zoom animation",2)
        self.add_check(desktop,"dock_autohide","Automatically hide dock",3)
        ttk.Button(desktop,text="Open Cinnamon Settings",command=lambda:run(["cinnamon-settings"])).grid(row=4,column=0,sticky="ew",pady=7)
        ttk.Button(desktop,text="Open Files",command=lambda:run(["nemo"])).grid(row=4,column=1,sticky="ew",pady=7,padx=8)
        ttk.Button(desktop,text="Open Terminal",command=lambda:run(["x-terminal-emulator"])).grid(row=5,column=0,sticky="ew",pady=7)
        ttk.Button(desktop,text="Reload Custom Linux OS dashboard",command=self.reload_desklet).grid(row=5,column=1,sticky="ew",pady=7,padx=8)
        ttk.Label(desktop,text="Low-effects defaults: no heavy blur or shadows. Dock zoom and auto-hide are optional.",style="Sub.TLabel",wraplength=650).grid(row=7,column=0,columnspan=2,sticky="w",pady=18)
        foot=ttk.Frame(root,padding=(18,10,18,16)); foot.pack(fill="x")
        ttk.Button(foot,text="Restore defaults",command=self.defaults).pack(side="left")
        ttk.Button(foot,text="Preview gradients",command=self.preview_gradients).pack(side="left",padx=8)
        ttk.Button(foot,text="Apply changes",command=self.apply).pack(side="right")
        ttk.Button(foot,text="Save only",command=self.save_only).pack(side="right",padx=8)
        # When the user chooses a mood, stage its accent automatically unless they later choose a custom color.
        self.vars["mood"].trace_add("write",self.mood_changed)

    def add_combo(self,parent,key,label,values,row):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky="w",pady=8)
        v=tk.StringVar(value=self.cfg.get(key,values[0])); self.vars[key]=v
        ttk.Combobox(parent,textvariable=v,values=values,state="readonly",width=27).grid(row=row,column=1,sticky="w",padx=14)
    def add_color(self,parent,key,label,row):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky="w",pady=8)
        self.vars[key]=tk.StringVar(value=self.cfg.get(key,MOODS[self.cfg["mood"]]["accent"]))
        ttk.Button(parent,text="Choose color…",command=self.pick_color).grid(row=row,column=1,sticky="w",padx=14)
        self.color_label=ttk.Label(parent,textvariable=self.vars[key]); self.color_label.grid(row=row,column=2,sticky="w")
    def pick_color(self):
        c=colorchooser.askcolor(self.vars["accent"].get(),parent=self.root)
        if c and c[1]:
            self.vars["accent"].set(c[1]); self.color_label.configure(foreground=c[1])
    def add_scale(self,parent,key,label,lo,hi,row,unit=""):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky="w",pady=8)
        v=tk.IntVar(value=int(self.cfg.get(key,lo))); self.vars[key]=v
        s=ttk.Scale(parent,from_=lo,to=hi,orient="horizontal",command=lambda x,v=v:v.set(round(float(x))))
        s.set(v.get()); s.grid(row=row,column=1,sticky="ew",padx=14)
        value=ttk.Label(parent,width=8,anchor="e")
        value.grid(row=row,column=2,sticky="w")
        def update_value(*_):
            value.configure(text=f"{v.get()}{unit}")
        v.trace_add("write",update_value)
        update_value()
        parent.columnconfigure(1,weight=1)
    def add_check(self,parent,key,label,row):
        v=tk.BooleanVar(value=bool(self.cfg.get(key,DEFAULT.get(key,True))))
        self.vars[key]=v
        ttk.Checkbutton(parent,text=label,variable=v).grid(row=row,column=0,sticky="w",pady=6)
    def values(self):
        d={k:v.get() for k,v in self.vars.items()}
        # Keep existing user-defined settings (including the optional applet order)
        # while layering current Control Center values on top.
        return {**DEFAULT,**self.cfg,**d}
    def mood_changed(self,*args):
        mood=self.vars["mood"].get()
        if mood in MOODS:
            # Accent is coordinated with mood automatically; user can change it manually afterward.
            self.vars["accent"].set(MOODS[mood]["accent"])
            self.color_label.configure(foreground=MOODS[mood]["accent"])
        preset=self.vars.get("glass_preset")
        if preset and preset.get()=="Linux Mint Glass" and mood!="Mint Glass":
            self.vars["mood"].set("Mint Glass")
    def save_only(self):
        try:
            d=self.values()
            if d.get("mood") not in MOODS:
                raise ValueError("Choose a valid color mood.")
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(d.get("accent", ""))):
                raise ValueError("Accent color must be a six-digit hex color, such as #c1d5f4.")
            CFG.parent.mkdir(parents=True, exist_ok=True)
            # Back up the prior config and atomically replace it, so an interrupted
            # write cannot leave a truncated JSON settings file.
            if CFG.exists():
                dest=HOME/"Aladin-Theme"/"backups"
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(CFG, dest/("settings-save-only-"+time.strftime("%Y%m%d-%H%M%S")+".json"))
            tmp=CFG.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(d, indent=2)+"\n")
            json.loads(tmp.read_text())
            tmp.replace(CFG)
            check=json.loads(CFG.read_text())
            if check != d:
                raise IOError("Saved settings did not match the selected values.")
            self.note.set("Preferences saved and verified locally. Click Apply changes to activate them.")
        except Exception as e:
            self.note.set("Save failed: " + str(e))
            messagebox.showerror("Could not save settings", str(e), parent=self.root)
    def preview_gradients(self):
        d=self.values()
        accent=d.get("accent", "#c1d5f4")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}",str(accent)):
            accent="#c1d5f4"
        style=d.get("gradient_style","Aurora")
        strength=max(0,min(100,int(d.get("gradient_intensity",42))))/100
        preview=tk.Toplevel(self.root)
        preview.title("Custom Linux OS • Gradient Preview")
        preview.configure(bg="#050609")
        preview.geometry("560x300")
        preview.transient(self.root)
        canvas=tk.Canvas(preview,bg="#050609",highlightthickness=0)
        canvas.pack(fill="both",expand=True,padx=16,pady=16)
        canvas.create_text(22,18,anchor="nw",text=style.upper()+"  /  "+accent,
            fill="#f0f4fc",font=("Sans",13,"bold"))
        canvas.create_rectangle(22,58,538,254,fill="#080b12",outline=accent,width=1)
        rgbv=rgb(accent)
        mid="#%02x%02x%02x" % tuple(round(c*strength) for c in rgbv)
        if style=="Radial glow":
            for i in range(14,0,-1):
                t=(15-i)/15
                col="#%02x%02x%02x" % tuple(round(5+(c*t*strength)) for c in rgbv)
                canvas.create_oval(100-i*12,70-i*5,460+i*5,235+i*4,fill=col,outline="")
        elif style=="Ice crystal":
            for i in range(8):
                x=50+i*66
                canvas.create_line(x,70,x+100,244,fill=mid,width=2)
                canvas.create_line(x+50,70,x-15,244,fill=accent,width=1)
        elif style=="Diagonal glass":
            canvas.create_polygon(22,58,330,58,180,254,22,254,fill=mid,outline="")
            canvas.create_polygon(330,58,538,58,538,254,180,254,fill="#101a2b",outline="")
        elif style=="Linear minimal":
            canvas.create_rectangle(22,58,538,254,fill="#050609",outline=accent,width=1)
            canvas.create_line(24,62,536,62,fill=mid,width=4)
        else:
            canvas.create_polygon(22,180,180,90,340,165,538,82,538,254,22,254,fill=mid,outline="")
            canvas.create_line(22,180,180,90,340,165,538,82,fill=accent,width=2)
        canvas.create_text(42,224,anchor="w",text="OLED PURE  •  ICE BLUE  •  GRADIENT STRENGTH %d%%" % int(strength*100),
            fill="#f0f4fc",font=("Sans",9,"bold"))
        ttk.Button(preview,text="Close preview",command=preview.destroy).pack(pady=(0,12))
    def defaults(self):
        for k,v in DEFAULT.items():
            if k in self.vars: self.vars[k].set(v)
        if "accent" in self.vars:
            self.vars["accent"].set(MOODS[DEFAULT["mood"]]["accent"])
            if hasattr(self, "color_label"):
                self.color_label.configure(foreground=MOODS[DEFAULT["mood"]]["accent"])
        self.note.set("Defaults selected. Click Apply changes to activate them.")
    def write_wallpaper(self,mood):
        p=MOODS[mood]
        if p["light"]:
            wave="#7889a6"
        else:
            wave=p["accent"]
        svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{p["wall"]}"/><stop offset=".52" stop-color="{p["base"]}"/><stop offset="1" stop-color="{p["wall2"]}"/></linearGradient><radialGradient id="glow"><stop stop-color="{wave}" stop-opacity=".20"/><stop offset="1" stop-color="{p["base"]}" stop-opacity="0"/></radialGradient><linearGradient id="wavefill" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{wave}" stop-opacity=".025"/><stop offset=".54" stop-color="{wave}" stop-opacity=".14"/><stop offset="1" stop-color="{wave}" stop-opacity=".035"/></linearGradient></defs>
<rect width="1920" height="1080" fill="url(#bg)"/><ellipse cx="160" cy="680" rx="480" ry="400" fill="url(#glow)"/><ellipse cx="1540" cy="820" rx="650" ry="430" fill="url(#glow)"/><path d="M-80 315 Q270 510 600 660 T1190 770 T2010 555 L2010 1080 L-80 1080Z" fill="url(#wavefill)"/><path d="M-50 320 Q280 520 620 665 T1200 770 T1980 560" fill="none" stroke="{wave}" stroke-opacity=".18" stroke-width="2"/><path d="M-20 365 Q320 550 660 695 T1240 800 T1970 595" fill="none" stroke="{wave}" stroke-opacity=".08" stroke-width="1"/><path d="M-30 890 Q460 770 850 850 T1640 845 T1980 765" fill="none" stroke="{wave}" stroke-opacity=".06" stroke-width="2"/>
</svg>'''
        path=WALL/"aladin-os-mood.svg"; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(svg)
        ET.parse(path)
        return path
    def backup(self):
        dest=HOME/"Aladin-Theme"/"backups"/("customizer-"+time.strftime("%Y%m%d-%H%M%S"))
        dest.mkdir(parents=True,exist_ok=True)
        for source in [CSS,CFG,THEME/"cinnamon/cinnamon.css",THEME/"gtk-3.0/gtk.css",THEME/"gtk-4.0/gtk.css",DOCK]:
            if source.exists():
                target=dest/(source.name+"-"+source.parent.name)
                shutil.copy2(source,target)
        return dest
    def apply(self):
        d=self.values()
        if d["mood"] not in MOODS: d["mood"]=DEFAULT["mood"]
        p=MOODS[d["mood"]]
        accent=d["accent"] if re.fullmatch(r"#[0-9a-fA-F]{6}",str(d["accent"])) else p["accent"]
        d["accent"]=accent
        fg=p["fg"]; muted=p["muted"]; base=p["base"]; border=p["border"]
        glass_preset=d.get("glass_preset","OLED Pure Glass")
        selected_fg="#ffffff" if p["light"] else base
        op=max(10,min(100,int(d["opacity"])))/100
        if glass_preset=="Clear Glass":
            op=min(op,.24)
        elif glass_preset=="Frosted Mint":
            op=max(op,.46)
        elif glass_preset=="Linux Mint Glass":
            op=min(op,.68)
        rad=max(6,min(30,int(d["radius"])))
        scale=max(75,min(110,int(d["scale"])))/100
        fs=max(80,min(120,int(d["font_scale"])))/100
        ba=max(8,min(80,int(d["border"])))/100
        spacing=6 if d["compact"] else 10
        pad=9 if d["compact"] else 13
        gradient_strength=max(0,min(100,int(d.get("gradient_intensity",42))))/100
        gradient_style=d.get("gradient_style","Aurora")
        if glass_preset in ("Linux Mint Glass","Frosted Mint"):
            # Mint green provides the preset identity while respecting a user-custom accent.
            glass_tint="#87d7a5" if glass_preset=="Linux Mint Glass" else accent
            glass_border="#80bd91" if glass_preset=="Linux Mint Glass" else accent
        else:
            glass_tint=accent
            glass_border=border
        if gradient_style=="Diagonal glass":
            gradient=f"linear-gradient(135deg,{rgba(accent,gradient_strength*.42)},{rgba(base,.98)} 58%,{rgba(accent,gradient_strength*.12)})"
        elif gradient_style=="Radial glow":
            gradient=f"radial-gradient(ellipse at 50% 0%,{rgba(accent,gradient_strength*.45)},{rgba(base,.98)} 72%)"
        elif gradient_style=="Linear minimal":
            gradient=f"linear-gradient(180deg,{rgba(accent,gradient_strength*.18)},{rgba(base,.98)} 75%)"
        elif gradient_style=="Ice crystal":
            gradient=f"linear-gradient(135deg,{rgba(accent,gradient_strength*.30)},{rgba(base,.98)} 42%,{rgba(accent,gradient_strength*.10)} 68%,{rgba(base,.98)})"
        else:
            gradient=f"linear-gradient(135deg,{rgba(accent,gradient_strength*.28)},{rgba(base,.98)} 45%,{rgba(accent,gradient_strength*.16)})"
        if glass_preset in ("Linux Mint Glass","Frosted Mint"):
            gradient=f"linear-gradient(135deg,{rgba(glass_tint,gradient_strength*.28)},{rgba(base,op)} 48%,{rgba(glass_tint,gradient_strength*.10)})"
        elif glass_preset=="Clear Glass":
            gradient=f"linear-gradient(135deg,{rgba(accent,.10)},{rgba(base,.16)} 55%,{rgba(accent,.04)})"
        card_background=f"background-image:{gradient};" if d.get("glass_highlights",True) else f"background-color:{rgba(base,op)};"
        glow=f"box-shadow:0 0 {int(gradient_strength*22)}px {rgba(glass_tint,gradient_strength*.22)};" if d.get("glow_effect",True) and gradient_strength>0 else ""
        transition="transition-duration:180ms;" if d.get("smooth_animations",True) else "transition-duration:0ms;"
        button_background=f"background-image:linear-gradient(135deg,{rgba(accent,gradient_strength*.45)},{rgba(base,.94)});" if d.get("accent_buttons",True) else f"background-color:{rgba(accent,.22)};"
        try:
            backup=self.backup()
            css=f""".ald-root {{ width:{int(1750*scale)}px; padding:2px 8px 4px 8px; color:{fg}; font-family:"Noto Sans",sans-serif; }}
.ald-header {{ width:{int(1750*scale)}px; height:{int(270*scale)}px; padding:5px 12px; }}
.ald-header-center {{ margin-top:{int((55 if d["compact"] else 70)*scale)}px; }}
.ald-brand {{ font-size:{int(17*fs)}px; font-weight:700; color:{fg}; }}
.ald-clock {{ font-size:{int(56*fs*scale)}px; font-weight:300; color:{fg}; margin-bottom:4px; }}
.ald-date {{ font-size:{int(12*fs)}px; color:{muted}; margin-bottom:10px; }}
.ald-search {{ min-width:{int(300*scale)}px; height:34px; border-radius:20px; background-color:{rgba(base,op)}; background-image:linear-gradient(135deg,{rgba(glass_tint,gradient_strength*.16)},{rgba(base,op)}); border:1px solid {rgba(glass_border,ba)}; padding:5px 14px; color:{fg}; }}
.ald-search-row {{ spacing:8px; }}
.ald-google-search-entry {{ min-width:{int(360*scale)}px; min-height:34px; padding:7px 12px; border-radius:18px; background-color:{rgba(base,.90)}; background-image:linear-gradient(135deg,{rgba(glass_tint,gradient_strength*.18)},{rgba(base,.86)}); border:1px solid {rgba(glass_border,ba)}; color:{fg}; caret-color:{accent}; }}
.ald-google-search-entry:focus {{ border-color:{accent}; }}
.ald-header-action {{ height:32px; border-radius:16px; background-color:{rgba(base,op)}; border:1px solid {rgba(border,ba)}; padding:5px 12px; color:{fg}; font-size:11px; }}
.ald-cols {{ width:{int(1750*scale)}px; }}
.ald-col-weather {{ width:{int(440*scale)}px; margin-right:{spacing+8}px; }}
.ald-col-ai {{ width:{int(420*scale)}px; margin-right:{spacing+8}px; }}
.ald-col-apps {{ width:{int(330*scale)}px; margin-right:{spacing+8}px; }}
.ald-col-right {{ width:{int(390*scale)}px; }}
.ald-card {{ background-color:{rgba(base,op)}; {card_background} {glow} border:1px solid {rgba(glass_border,ba)}; border-radius:{rad}px; padding:{pad}px; color:{fg}; margin-bottom:{spacing+4}px; {transition} }}
.ald-col-weather > .ald-card {{ width:{int(370*scale)}px; }} .ald-col-ai > .ald-card {{ width:{int(400*scale)}px; }} .ald-col-apps > .ald-card {{ width:{int(310*scale)}px; }} .ald-col-right > .ald-card {{ width:{int(350*scale)}px; }}
.ald-title {{ font-size:{int(14*fs)}px; font-weight:700; color:{fg}; margin-bottom:4px; }} .ald-muted {{ font-size:{int(11*fs)}px; color:{muted}; }} .ald-text {{ font-size:{int(12*fs)}px; color:{muted}; }}
.ald-big {{ font-size:{int(27*fs)}px; font-weight:300; color:{fg}; margin-bottom:4px; }}
.ald-metric {{ font-size:{int(12*fs)}px; color:{fg}; padding:3px 2px; margin-right:5px; }} .ald-weather {{ font-size:{int(20*fs)}px; color:{fg}; padding:4px 0; }}
.ald-row {{ margin-bottom:{spacing}px; }} .ald-action {{ color:{fg}; {button_background} border:1px solid {rgba(border,ba)}; border-radius:{max(7,rad-6)}px; padding:{pad-3}px 10px; font-size:{int(11*fs)}px; margin-right:5px; margin-bottom:5px; }}
.ald-action:hover {{ background-color:{rgba(accent,.38)}; color:{'#fff' if not p['light'] else '#101b2b'}; }}
.ald-grid {{ padding-top:{spacing}px; }} .ald-app {{ width:{int(74*scale)}px; height:{int(80*scale)}px; {card_background} {glow} border:1px solid {rgba(border,ba)}; border-radius:{min(24,rad+2)}px; margin-right:5px; margin-bottom:5px; }}
.ald-app:hover {{ background-image:linear-gradient(135deg,{rgba(accent,gradient_strength*.48)},{rgba(base,.96)}); border-color:{rgba(accent,.75)}; {transition} }} .ald-app-inner {{ padding:{pad-4}px 2px; }} .ald-icon {{ color:{accent}; }} .ald-app-label {{ font-size:{int(10*fs)}px; color:{fg}; }}
.ald-task {{ background-color:{rgba(base,.55)}; border:1px solid {rgba(border,ba*.55)}; border-radius:9px; padding:6px 5px; color:{fg}; font-size:{int(12*fs)}px; margin-bottom:5px; }} .ald-task:hover {{ background-color:{rgba(accent,.20)}; }}
.ald-file {{ font-size:{int(11*fs)}px; color:{muted}; margin-bottom:5px; }}
.ald-ai-status {{ color:{accent}; font-size:10px; padding:3px 0; }}
.ald-ai-scroll {{ background-color:{rgba(base,.55)}; {card_background} border:1px solid {rgba(border,ba*.6)}; border-radius:{max(7,rad-4)}px; padding:8px; min-height:200px; }}
.ald-ai-reply {{ color:{fg}; font-size:{int(11*fs)}px; padding:3px; }}
.ald-ai-prompt-row {{ spacing:5px; padding-top:8px; padding-bottom:5px; }}
.ald-ai-entry {{ min-height:34px; padding:5px 9px; border-radius:10px; background-color:{rgba(base,.85)}; color:{fg}; border:1px solid {rgba(border,ba)}; caret-color:{accent}; }}
.ald-footer {{ width:{int(1750*scale)}px; height:46px; padding:3px 12px; margin-top:{50 if d['compact'] else 90}px; }}
.ald-footer-pill {{ background-color:{rgba(base,op)}; background-image:linear-gradient(135deg,{rgba(glass_tint,gradient_strength*.14)},{rgba(base,op)}); border:1px solid {rgba(glass_border,ba)}; border-radius:20px; padding:8px 13px; color:{fg}; font-size:11px; }}
.ald-applet-footer {{ width:{int(1750*scale)}px; padding:8px 12px 4px 12px; margin-top:{18 if d["compact"] else 28}px; }}
.ald-applet-heading {{ spacing:8px; padding-bottom:6px; }}
.ald-applet-title {{ font-size:{int(10*fs)}px; font-weight:700; color:{muted}; }}
.ald-applet-row {{ spacing:8px; width:100%; }}
.ald-applet-left {{ spacing:8px; }}
.ald-applet-right {{ spacing:8px; }}
.ald-applet-item {{ spacing:4px; padding:2px; border-radius:{rad}px; background-color:{rgba(base,op)}; border:1px solid {rgba(glass_border,ba*.7)}; }}
"""
            CSS.write_text(css)
            # Keep Cinnamon's shell panel/popups on the selected mood too.
            shell=f"""/* Custom Linux OS Futuristic — generated color mood */
stage {{ color:{fg}; }}
#panel, .panel-top, .panel-bottom {{ background-color:{rgba(base,.97)}; color:{fg}; border:1px solid {rgba(border,ba)}; }}
#panel .panel-button {{ color:{fg}; border-radius:10px; }}
#panel .panel-button:hover, #panel .panel-button:focus {{ background-color:{rgba(accent,.22)}; color:{fg}; }}
#panel .panel-button:active, #panel .panel-button:checked {{ background-color:{rgba(accent,.32)}; color:{fg}; }}
.popup-menu, .popup-menu-box, .popup-menu-content {{ background-color:{rgba(base,.99)}; color:{fg}; border:1px solid {rgba(border,ba)}; border-radius:14px; }}
.popup-menu-item {{ color:{fg}; padding:8px 12px; }}
.popup-menu-item:hover, .popup-menu-item:focus {{ background-color:{rgba(accent,.24)}; color:{fg}; }}
.notification {{ background-color:{rgba(base,.98)}; color:{fg}; border:1px solid {rgba(border,ba)}; border-radius:14px; }}
"""
            (THEME/"cinnamon/cinnamon.css").write_text(shell)
            gtk3=f"""@define-color theme_bg_color {base}; @define-color theme_fg_color {fg}; @define-color theme_base_color {base}; @define-color theme_text_color {fg}; @define-color theme_selected_bg_color {accent}; @define-color theme_selected_fg_color {selected_fg};
window, .background {{ background-color:{base}; color:{fg}; }}
headerbar, .titlebar {{ background-image:linear-gradient(to bottom,{rgba(accent,.28)},{base}); color:{fg}; border-color:{border}; }}
button {{ background-image:linear-gradient(to bottom,{rgba(accent,.24)},{base}); color:{fg}; border:1px solid {rgba(border,ba)}; border-radius:9px; }}
button:hover {{ background-image:linear-gradient(to bottom,{rgba(accent,.42)},{rgba(base,.96)}); color:{fg}; }}
entry, textview, spinbutton, combobox, .search-entry {{ background-color:{rgba(base,.98)}; color:{fg}; border:1px solid {rgba(border,ba)}; border-radius:8px; }}
selection {{ background-color:{accent}; color:{selected_fg}; }} tooltip {{ background-color:{base}; color:{fg}; border:1px solid {border}; }}
"""
            gtk4=f"""@define-color window_bg_color {base}; @define-color window_fg_color {fg}; @define-color view_bg_color {base}; @define-color view_fg_color {fg}; @define-color accent_bg_color {accent}; @define-color accent_fg_color {selected_fg}; @define-color headerbar_bg_color {base}; @define-color headerbar_fg_color {fg};
window, .background {{ background-color:{base}; color:{fg}; }}
headerbar {{ background-color:{base}; color:{fg}; border-color:{border}; }}
button {{ background-color:{rgba(accent,.20)}; color:{fg}; border:1px solid {rgba(border,ba)}; border-radius:9px; }}
button:hover {{ background-color:{rgba(accent,.38)}; color:{fg}; }}
entry, textview, spinbutton, combobox, .search-entry {{ background-color:{rgba(base,.98)}; color:{fg}; border:1px solid {rgba(border,ba)}; border-radius:8px; }}
selection {{ background-color:{accent}; color:{selected_fg}; }} tooltip {{ background-color:{base}; color:{fg}; border:1px solid {border}; }}
"""
            (THEME/"gtk-3.0/gtk.css").write_text(gtk3)
            (THEME/"gtk-3.0/gtk-dark.css").write_text(gtk3)
            (THEME/"gtk-4.0/gtk.css").write_text(gtk4)
            (THEME/"gtk-4.0/gtk-dark.css").write_text(gtk4)
            # Recolor the Plank glass dock to match the selected palette.
            def blend(a, b, t):
                aa,bb=rgb(a),rgb(b)
                return tuple(round(aa[i]*(1-t)+bb[i]*t) for i in range(3))
            def plank_color(values, alpha):
                return ";;".join(str(max(0,min(255,int(v)))) for v in values)+";;"+str(max(0,min(255,int(alpha))))
            fill=blend(base,accent,.22)
            DOCK.parent.mkdir(parents=True,exist_ok=True)
            DOCK.write_text(f"""[PlankTheme]
TopRoundness={rad}
BottomRoundness={rad}
LineWidth=1
OuterStrokeColor={plank_color(rgb(border),round(ba*255))}
FillStartColor={plank_color(fill,238)}
FillEndColor={plank_color(rgb(base),246)}
InnerStrokeColor={plank_color(rgb(fg),48)}

[PlankDockTheme]
HorizPadding=8
TopPadding=-6
BottomPadding=5
ItemPadding=4
IndicatorSize=5
IconShadowSize=1
UrgentBounceHeight=1.2
LaunchBounceHeight=0.45
FadeOpacity=1
ClickTime=280
UrgentBounceTime=500
LaunchBounceTime=450
ActiveTime=250
SlideTime=250
HideTime=220
GlowSize=18
GlowTime=8000
GlowPulseTime=1800
UrgentHueShift=0
ItemMoveTime=350
CascadeHide=true
BadgeColor={plank_color(rgb(accent),255)}
""")
            # Regenerate the chosen wallpaper mood, then select it.
            wallpaper=d["wallpaper"]
            uri=None
            if wallpaper=="mood":
                wp=self.write_wallpaper(d["mood"]); uri="file://"+str(wp)
            elif wallpaper=="Black gradient":
                uri="file://"+str(WALL/"aladin-black.svg")
            elif wallpaper=="Silver glass":
                # The legacy silver-glass file is a placeholder; generate a valid SVG instead.
                wp=self.write_wallpaper("Arctic Silver"); uri="file://"+str(wp)
            elif wallpaper=="Mint default":
                uri="file:///usr/share/backgrounds/linuxmint/default_background.jpg"
            if uri:
                run(["gsettings","set","org.cinnamon.desktop.background","picture-uri",uri])
            # Execute desktop changes with checked subprocesses; failures must not
            # disappear behind the old run() helper, which intentionally suppresses errors.
            failures=[]
            def checked(cmd, label):
                try:
                    result=subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE, text=True, timeout=5)
                    if result.returncode:
                        detail=(result.stderr or "").strip()
                        failures.append(label + (": " + detail if detail else " (exit "+str(result.returncode)+")"))
                except Exception as command_error:
                    failures.append(label + ": " + str(command_error))
            if uri:
                wallpaper_path=Path(uri.removeprefix("file://"))
                if not wallpaper_path.is_file():
                    failures.append("Wallpaper file is missing: " + str(wallpaper_path))
                else:
                    checked(["gsettings","set","org.cinnamon.desktop.background","picture-uri",uri],"Set wallpaper")
            # Match shell/GTK/icon theme to the selected mood.
            checked(["gsettings","set","org.cinnamon.desktop.interface","icon-theme","Papirus-Light" if p["light"] else "Papirus-Dark"],"Set icon theme")
            # Brief stock-theme switch forces GTK to re-read edited theme files.
            checked(["gsettings","set","org.cinnamon.theme","name","Mint-Y-Dark"],"Refresh Cinnamon theme")
            checked(["gsettings","set","org.cinnamon.desktop.interface","gtk-theme","Mint-Y-Dark"],"Refresh GTK theme")
            checked(["gsettings","set","org.cinnamon.desktop.interface","gtk-theme","Aladin-OS-Futuristic"],"Set Aladin GTK theme")
            checked(["gsettings","set","org.cinnamon.theme","name","Aladin-OS-Futuristic"],"Set Aladin shell theme")
            checked(["dconf","write","/net/launchpad/plank/docks/dock1/icon-size",str(int(d["dock_size"]))],"Set dock icon size")
            checked(["dconf","write","/net/launchpad/plank/docks/dock1/zoom-enabled","true" if d["dock_zoom"] else "false"],"Set dock zoom")
            checked(["dconf","write","/net/launchpad/plank/docks/dock1/hide-mode", "'intelligent'" if d["dock_autohide"] else "'none'"],"Set dock auto-hide")
            checked(["dconf","write","/net/launchpad/plank/docks/dock1/theme","'Aladin-OS-Futuristic'"],"Set dock theme")
            CFG.parent.mkdir(parents=True,exist_ok=True)
            tmp=CFG.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(d,indent=2)+"\n")
            json.loads(tmp.read_text())
            tmp.replace(CFG)
            # Refresh Plank to load its updated theme. A missing running process is not
            # an apply failure; the subsequent Popen and read-back checks catch issues.
            subprocess.run(["pkill","-x","plank"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)
            try:
                subprocess.Popen(["plank"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            except Exception as launch_error:
                failures.append("Restart Plank: " + str(launch_error))
            self.reload_desklet(update_note=False)
            # Verify all settings exposed by the UI, not only the mood name.
            try:
                saved=json.loads(CFG.read_text())
                if saved != d:
                    failures.append("Saved settings did not match all selected Control Center values")
            except Exception as verify_error:
                failures.append("Settings file read-back failed: " + str(verify_error))
            checks=[
                (["gsettings","get","org.cinnamon.theme","name"],"Aladin-OS-Futuristic","Cinnamon shell theme"),
                (["gsettings","get","org.cinnamon.desktop.interface","gtk-theme"],"Aladin-OS-Futuristic","GTK theme"),
                (["gsettings","get","org.cinnamon.desktop.interface","icon-theme"],"Papirus-Light" if p["light"] else "Papirus-Dark","icon theme"),
                (["dconf","read","/net/launchpad/plank/docks/dock1/icon-size"],str(int(d["dock_size"])),"dock icon size"),
                (["dconf","read","/net/launchpad/plank/docks/dock1/zoom-enabled"],"true" if d["dock_zoom"] else "false","dock zoom"),
                (["dconf","read","/net/launchpad/plank/docks/dock1/hide-mode"],"'intelligent'" if d["dock_autohide"] else "'none'","dock auto-hide"),
                (["dconf","read","/net/launchpad/plank/docks/dock1/theme"],"'Aladin-OS-Futuristic'","dock theme"),
            ]
            if uri:
                checks.append((["gsettings","get","org.cinnamon.desktop.background","picture-uri"],uri,"wallpaper"))
            for cmd, expected, label in checks:
                try:
                    actual=subprocess.check_output(cmd,text=True,timeout=3).strip()
                    if actual != expected and expected not in actual:
                        failures.append(f"{label} mismatch (expected {expected}, got {actual})")
                except Exception as verify_error:
                    failures.append(label + " could not be verified: " + str(verify_error))
            if failures:
                detail="\n".join("• " + item for item in failures)
                self.note.set("Applied with warnings — some system changes failed verification.")
                messagebox.showwarning("Custom Linux OS applied with warnings",detail+"\n\nBackup: "+str(backup),parent=self.root)
            else:
                self.note.set(f"Applied and verified {d['mood']} mood, desktop, dock and theme. Backup: {backup}")
        except Exception as e:
            messagebox.showerror("Could not apply settings",str(e),parent=self.root)
            self.note.set("Apply failed; current settings were not intentionally removed.")
    def reload_desklet(self, update_note=True):
        # Preserve the exact enabled-desklet list and its order.
        try:
            raw=subprocess.check_output(
                ["gsettings","get","org.cinnamon","enabled-desklets"],
                text=True, timeout=3
            ).strip()
            import ast
            current=ast.literal_eval(raw)
            if not isinstance(current,list):
                raise ValueError("Cinnamon returned an unexpected desklet list")
            target=next((x for x in current if str(x).startswith("AladinOS@local:")), "AladinOS@local:1:30:10")
            had_target=any(str(x).startswith("AladinOS@local:") for x in current)
            temporarily=[x for x in current if not str(x).startswith("AladinOS@local:")]
            subprocess.run(["gsettings","set","org.cinnamon","enabled-desklets",str(temporarily)],
                           check=True, timeout=3, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            def restore():
                try:
                    final=current if had_target else current + [target]
                    subprocess.run(["gsettings","set","org.cinnamon","enabled-desklets",str(final)],
                                   check=True, timeout=3, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
                    if update_note:
                        self.note.set("Custom Linux OS dashboard reloaded; other desklets preserved.")
                except Exception as e:
                    self.note.set("Desklet reload failed: " + str(e))
                    messagebox.showerror("Desklet reload failed", str(e), parent=self.root)
            self.root.after(900,restore)
        except Exception as e:
            self.note.set("Could not reload dashboard: " + str(e))
            messagebox.showerror("Could not reload dashboard", str(e), parent=self.root)

if __name__=="__main__":
    root=tk.Tk(); AladinCustomizer(root); root.mainloop()
