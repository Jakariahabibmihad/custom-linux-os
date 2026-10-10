const St = imports.gi.St;
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const Desklet = imports.ui.desklet;
const Mainloop = imports.mainloop;
const CD = imports.gi.CinnamonDesktop;

class AladinOS extends Desklet.Desklet {
    constructor(metadata, id) {
        super(metadata, id);
        this.settings = this.loadSettings();
        this.timers = [];
        this.lastCpu = null;
        this.lastNetwork = null;
        this.tasks = ["Review today's priorities", "Study / deep work", "Take a short break", "Organize workspace", "Plan tomorrow"];
        this.aiHistory = [];
        this.aiModel = "qwen3:4b";
        this.aiBusy = false;
        this.root = new St.BoxLayout({ vertical: true, style_class: "ald-root" });
        this.root.set_width(1750);
        this.buildHeader();
        const columns = new St.BoxLayout({ style_class: "ald-cols" });
        columns.add_child(this.spacer());
        columns.add_child(this.buildWeatherColumn());
        if (this.setting("show_ai", true)) columns.add_child(this.buildAIColumn());
        columns.add_child(this.buildAppsColumn());
        columns.add_child(this.buildRightColumn());
        columns.add_child(this.spacer());
        this.root.add_child(columns);
        this.buildFooter();
        this.setContent(this.root);
        this.setHeader("");
        this.wallClock = new CD.WallClock();
        this.clockSignal = this.wallClock.connect("notify::clock", () => this.updateClock());
        this.updateClock();
        this.updateSystem();
        this.checkAIStatus();
        this.timers.push(Mainloop.timeout_add_seconds(2, () => { this.updateSystem(); return true; }));
        this.timers.push(Mainloop.timeout_add_seconds(30, () => { this.updateClock(); return true; }));
        this.timers.push(Mainloop.timeout_add_seconds(45, () => { this.checkAIStatus(); return true; }));
    }

    loadSettings() { try { return JSON.parse(this.read(GLib.get_home_dir() + "/.local/share/aladin-os/settings.json")); } catch (e) { return {}; } }
    setting(key, fallback) { return this.settings && this.settings[key] !== undefined ? this.settings[key] : fallback; }
    label(text, style) { return new St.Label({ text: String(text), style_class: style || "ald-text" }); }
    row() { return new St.BoxLayout({ style_class: "ald-row" }); }
    spacer() { return new St.Widget({ x_expand: true, y_expand: false }); }
    action(text, callback) {
        const b = new St.Button({ label: text, style_class: "ald-action" });
        b.connect("clicked", callback);
        return b;
    }
    card(title, subtitle, height) {
        const b = new St.BoxLayout({ vertical: true, style_class: "ald-card" });
        if (height) b.set_height(height);
        b.add_child(this.label(title, "ald-title"));
        if (subtitle) b.add_child(this.label(subtitle, "ald-muted"));
        return b;
    }
    googleSearch(query) {
        query = String(query || "").trim();
        if (!query) {
            global.log("Custom Linux OS: enter a search query first");
            return;
        }
        const url = "https://www.google.com/search?q=" + encodeURIComponent(query);
        try {
            GLib.spawn_command_line_async("xdg-open " + GLib.shell_quote(url));
        } catch (e) {
            global.logError("Custom Linux OS Google search could not open the default browser: " + e);
        }
    }
    openDrawer() {
        GLib.spawn_command_line_async("/usr/bin/python3 " + GLib.shell_quote(GLib.get_home_dir() + "/.local/bin/aladin-app-drawer.py"));
    }
    openCustomizer() {
        GLib.spawn_command_line_async("/usr/bin/python3 " + GLib.shell_quote(GLib.get_home_dir() + "/.local/bin/aladin-control-center.py"));
    }
    launch(id) {
        try {
            if (id === "aladin-app-drawer") { this.openDrawer(); return; }
            if (id === "aladin-customizer") { this.openCustomizer(); return; }
            if (id === "aladin-terminal") { GLib.spawn_command_line_async("x-terminal-emulator"); return; }
            if (id === "xed.desktop") { GLib.spawn_command_line_async("xed"); return; }
            const app = Gio.DesktopAppInfo.new(id);
            if (app) app.launch([], null);
            else global.log("Custom Linux OS: desktop application not found: " + id);
        } catch (e) { global.logError("Custom Linux OS launch error: " + e); }
    }
    appTile(name, icon, id) {
        const b = new St.Button({ style_class: "ald-app" });
        const v = new St.BoxLayout({ vertical: true, style_class: "ald-app-inner" });
        // Prefer the installed application's own desktop-entry icon; use the old
        // symbolic icon only for Aladin built-ins or missing desktop entries.
        let appIcon = null;
        try {
            const appInfo = Gio.DesktopAppInfo.new(id);
            if (appInfo) appIcon = appInfo.get_icon();
        } catch (e) {
            global.log("Custom Linux OS: couldn't load app icon for " + id + ": " + e);
        }
        const iconWidget = appIcon
            ? new St.Icon({ gicon: appIcon, icon_size: 38, style_class: "ald-app-icon" })
            : new St.Icon({ icon_name: icon, icon_size: 38, style_class: "ald-icon" });
        v.add_child(iconWidget);
        v.add_child(this.label(name, "ald-app-label"));
        b.set_child(v);
        b.connect("clicked", () => this.launch(id));
        return b;
    }
    buildHeader() {
        const h = new St.BoxLayout({ style_class: "ald-header" });
        const brand = new St.BoxLayout({ vertical: true });
        brand.add_child(this.label("◢  CUSTOM LINUX OS", "ald-brand"));
        brand.add_child(this.label("BLACK GLASS • DESKTOP", "ald-muted"));
        h.add_child(brand);
        h.add_child(this.spacer());
        const center = new St.BoxLayout({ vertical: true, style_class: "ald-header-center" });
        center.add_child(this.label("--:--", "ald-clock"));
        this.clockLabel = center.get_last_child();
        this.dateLabel = this.label("", "ald-date");
        center.add_child(this.dateLabel);
        if (this.setting("show_search", true)) {
            const searchRow = new St.BoxLayout({ style_class: "ald-search-row" });
            const search = new St.Entry({
                name: "aladin-google-search",
                style_class: "ald-google-search-entry",
                hint_text: "Search Google in your browser…",
                can_focus: true,
                x_expand: true
            });
            search.set_width(430);
            search.clutter_text.connect("activate", () => this.googleSearch(search.get_text()));
            searchRow.add_child(search);
            searchRow.add_child(this.action("Google  ↗", () => this.googleSearch(search.get_text())));
            center.add_child(searchRow);
        }
        h.add_child(center);
        h.add_child(this.spacer());
        this.root.add_child(h);
    }
    buildWeatherColumn() {
        const col = new St.BoxLayout({ vertical: true, style_class: "ald-col-weather" });
        if (this.setting("show_weather", true)) {
            const weather = this.card("WEATHER", "Live weather requires a configured provider", 145);
            const line = this.row();
            line.add_child(this.label("☁", "ald-big"));
            line.add_child(this.label("Weather unavailable", "ald-weather"));
            weather.add_child(line);
            weather.add_child(this.label("No location or forecast configured", "ald-muted"));
            col.add_child(weather);
        }

        if (this.setting("show_system", true)) {
            const sys = this.card("SYSTEM MONITOR", "CPU • memory • disk • thermals • network", 224);
            const metrics = this.row();
            this.cpuLabel = this.label("CPU  --%", "ald-metric");
            this.memLabel = this.label("MEM  --%", "ald-metric");
            this.diskLabel = this.label("SSD  --", "ald-metric");
            metrics.add_child(this.cpuLabel); metrics.add_child(this.memLabel); metrics.add_child(this.diskLabel);
            sys.add_child(metrics);
            this.upLabel = this.label("UPTIME  --", "ald-muted");
            sys.add_child(this.upLabel);
            this.cpuTempLabel = this.setting("show_cpu_temp", true) ? this.label("CPU TEMP  --", "ald-sensor") : null;
            this.gpuTempLabel = this.setting("show_gpu_temp", true) ? this.label("GPU TEMP  --", "ald-sensor") : null;
            this.netSpeedLabel = this.setting("show_network_speed", true) ? this.label("NET  ↓ sampling…  ↑ sampling…", "ald-sensor") : null;
            if (this.cpuTempLabel) sys.add_child(this.cpuTempLabel);
            if (this.gpuTempLabel) sys.add_child(this.gpuTempLabel);
            if (this.netSpeedLabel) sys.add_child(this.netSpeedLabel);
            col.add_child(sys);
        }

        if (this.setting("show_quick_tools", true)) {
        const quick = this.card("FOCUS & TOOLS", "Quick actions", 169);
        let r = this.row();
        r.add_child(this.action("◴  Focus Timer", () => this.startFocusTimer()));
        r.add_child(this.action("✎  Write Journal", () => this.launch("xed.desktop")));
        quick.add_child(r);
        r = this.row();
        r.add_child(this.action("☕  Take a break", () => this.startBreak()));
        r.add_child(this.action("▣  Screen Capture", () => GLib.spawn_command_line_async("gnome-screenshot")));
        quick.add_child(r);
        col.add_child(quick);
        }
        return col;
    }
    buildAIColumn() {
        const col = new St.BoxLayout({ vertical: true, style_class: "ald-col-ai" });
        const ai = this.card("ALADIN AI", "Private • local model • offline", 405);
        this.aiStatus = this.label("●  Connecting to local AI…", "ald-ai-status");
        ai.add_child(this.aiStatus);
        this.aiReply = this.label("Hello! I'm your local Aladin assistant. Ask me anything — your prompt stays on this device.", "ald-ai-reply");
        this.aiReply.clutter_text.line_wrap = true;
        this.aiReply.clutter_text.ellipsize = imports.gi.Pango.EllipsizeMode.NONE;
        this.aiReply.set_x_expand(true);
        const replyScroll = new St.ScrollView({ style_class: "ald-ai-scroll", overlay_scrollbars: false });
        replyScroll.set_policy(imports.gi.Gtk.PolicyType.AUTOMATIC, imports.gi.Gtk.PolicyType.AUTOMATIC);
        replyScroll.set_height(242);
        replyScroll.set_child(this.aiReply);
        ai.add_child(replyScroll);
        const promptRow = new St.BoxLayout({ style_class: "ald-ai-prompt-row" });
        this.aiEntry = new St.Entry({ style_class: "ald-ai-entry", hint_text: "Message your local AI…", can_focus: true, x_expand: true });
        this.aiEntry.clutter_text.connect("activate", () => this.sendAI());
        promptRow.add_child(this.aiEntry);
        promptRow.add_child(this.action("Send ↗", () => this.sendAI()));
        ai.add_child(promptRow);
        const actions = this.row();
        actions.add_child(this.action("New chat", () => this.resetAI()));
        actions.add_child(this.action("Open AI console", () => GLib.spawn_command_line_async("xdg-open http://127.0.0.1:8088/docs")));
        ai.add_child(actions);
        col.add_child(ai);
        return col;
    }
    checkAIStatus() {
        try {
            const proc = Gio.Subprocess.new(["/usr/bin/curl", "-sS", "--max-time", "2", "http://127.0.0.1:11434/api/tags"], Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            proc.communicate_utf8_async(null, null, (p, result) => {
                try {
                    const [ok, out, err] = p.communicate_utf8_finish(result);
                    const data = ok ? JSON.parse(out) : {};
                    const models = data.models || [];
                    if (this.aiStatus) this.aiStatus.set_text(models.length ? "●  LOCAL AI READY  •  " + this.aiModel : "○  No local models found");
                } catch (e) { if (this.aiStatus) this.aiStatus.set_text("○  Local AI unavailable"); }
            });
        } catch (e) { if (this.aiStatus) this.aiStatus.set_text("○  Start Ollama to chat"); }
    }
    sendAI() {
        if (this.aiBusy || !this.aiEntry) return;
        const prompt = this.aiEntry.get_text().trim();
        if (!prompt) return;
        this.aiEntry.set_text("");
        this.aiBusy = true;
        this.aiReply.set_text("You  ›  " + prompt + "\n\nAladin AI is thinking…");
        this.aiHistory.push({ role: "user", content: prompt });
        const payload = JSON.stringify({ model: this.aiModel, messages: this.aiHistory.slice(-12), stream: false, options: { temperature: 0.7 } });
        try {
            const proc = Gio.Subprocess.new(["/usr/bin/curl", "-sS", "--max-time", "120", "-H", "Content-Type: application/json", "-d", payload, "http://127.0.0.1:11434/api/chat"], Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            proc.communicate_utf8_async(null, null, (p, result) => {
                this.aiBusy = false;
                try {
                    const [ok, out, err] = p.communicate_utf8_finish(result);
                    if (!ok) throw new Error(err || "Local AI request failed");
                    const data = JSON.parse(out);
                    if (data.error) throw new Error(data.error);
                    const answer = data.message && data.message.content ? data.message.content.trim() : "No response received.";
                    this.aiHistory.push({ role: "assistant", content: answer });
                    if (this.aiReply) this.aiReply.set_text("You  ›  " + prompt + "\n\nALADIN AI\n" + answer);
                    if (this.aiStatus) this.aiStatus.set_text("●  LOCAL AI READY  •  " + this.aiModel);
                } catch (e) {
                    if (this.aiReply) this.aiReply.set_text("I couldn't reach your local model. Check that Ollama is running, then try again.\n\n" + String(e.message || e));
                    if (this.aiStatus) this.aiStatus.set_text("○  AI request failed");
                }
            });
        } catch (e) {
            this.aiBusy = false;
            this.aiReply.set_text("Could not start the local AI request: " + String(e.message || e));
        }
    }
    resetAI() {
        this.aiHistory = [];
        if (this.aiReply) this.aiReply.set_text("New conversation started. What would you like help with?");
        if (this.aiEntry) this.aiEntry.grab_key_focus();
    }
    buildAppsColumn() {
        const col = new St.BoxLayout({ vertical: true, style_class: "ald-col-apps" });
        if (this.setting("show_apps", true)) {
        const apps = this.card("APPS", "Your workspace", 380);
        const grid = new St.BoxLayout({ vertical: true, style_class: "ald-grid" });
        const items = [
            ["Calendar", "x-office-calendar", "org.gnome.Calendar.desktop"],
            ["Notes", "accessories-text-editor", "xed.desktop"],
            ["Browser", "web-browser", "brave-browser.desktop"],
            ["Pictures", "folder-pictures", "xviewer.desktop"],
            ["Calculator", "accessories-calculator", "org.gnome.Calculator.desktop"],
            ["App Drawer", "view-app-grid-symbolic", "aladin-app-drawer"],
            ["Videos", "video-x-generic", "vlc.desktop"],
            ["Terminal", "utilities-terminal", "aladin-terminal"],
            ["Files", "system-file-manager", "nemo.desktop"]
        ];
        for (let i = 0; i < items.length; i += 3) {
            const r = this.row();
            for (let j = i; j < Math.min(i + 3, items.length); j++) r.add_child(this.appTile(items[j][0], items[j][1], items[j][2]));
            grid.add_child(r);
        }
        apps.add_child(grid);
        col.add_child(apps);
        }
        if (this.setting("show_media", true)) {
        const media = this.card("NOW PLAYING", "Media shortcuts", 132);
        media.add_child(this.label("♫   Open a local media player", "ald-text"));
        const mr = this.row();
        mr.add_child(this.action("Rhythmbox", () => this.launch("org.gnome.Rhythmbox3.desktop")));
        mr.add_child(this.action("VLC", () => this.launch("vlc.desktop")));
        media.add_child(mr);
        col.add_child(media);
        }
        return col;
    }
    buildRightColumn() {
        const col = new St.BoxLayout({ vertical: true, style_class: "ald-col-right" });
        if (this.setting("show_tasks", true)) {
        const tasks = this.card("TODAY'S FOCUS", "Select an item when it's done", 280);
        this.taskCount = this.label("5 open", "ald-big");
        tasks.add_child(this.taskCount);
        this.taskButtons = [];
        this.tasks.forEach((name) => {
            const b = new St.Button({ label: "○   " + name, style_class: "ald-task" });
            b.connect("clicked", () => {
                const done = b.get_label().startsWith("✓");
                b.set_label((done ? "○   " : "✓   ") + name);
                this.updateTaskCount();
            });
            this.taskButtons.push(b);
            tasks.add_child(b);
        });
        col.add_child(tasks);
        }
        if (this.setting("show_places", true)) {
        const memories = this.card("MEMORIES & MAP", "Open pictures or explore a map", 135);
        memories.add_child(this.action("▧  Open Pictures", () => GLib.spawn_command_line_async("nemo " + GLib.shell_quote(GLib.get_home_dir() + "/Pictures"))));
        memories.add_child(this.action("⌖  OpenStreetMap", () => GLib.spawn_command_line_async("xdg-open https://www.openstreetmap.org")));
        col.add_child(memories);
        }
        if (this.setting("show_control_center", true)) {
        const tools = this.card("CONTROL CENTER", "Local desktop tools", 110);
        const tr = this.row();
        tr.add_child(this.action("⚙ Settings", () => this.launch("aladin-customizer")));
        tr.add_child(this.action("▦ All Apps", () => this.openDrawer()));
        tools.add_child(tr);
        col.add_child(tools);
        }
        return col;
    }
    buildFooter() {
        if (!this.setting("show_footer", true)) return;
        this.footerContainer = new St.BoxLayout({ vertical: true, style_class: "ald-applet-footer" });
        const heading = new St.BoxLayout({ style_class: "ald-applet-heading" });
        heading.add_child(this.label("DESKLET APPLETS", "ald-applet-title"));
        heading.add_child(this.spacer());
        this.footerContainer.add_child(heading);
        this.appletRow = new St.BoxLayout({ style_class: "ald-applet-row" });
        this.appletLeft = new St.BoxLayout({ style_class: "ald-applet-left" });
        this.appletRight = new St.BoxLayout({ style_class: "ald-applet-right" });
        this.appletRow.add_child(this.appletLeft);
        this.appletRow.add_child(this.spacer());
        this.appletRow.add_child(this.appletRight);
        this.footerContainer.add_child(this.appletRow);
        this.root.add_child(this.footerContainer);
        this.renderDeskletApplets();
    }
    availableDeskletApplets() {
        return {
            menu: { label: "▦  App Menu", run: () => this.openDrawer() },
            network: { label: "⌁  Network", run: () => GLib.spawn_command_line_async("cinnamon-settings network") },
            audio: { label: "◖  Audio", run: () => GLib.spawn_command_line_async("cinnamon-settings sound") },
            system: { label: "⚙  System", run: () => this.launch("org.gnome.SystemMonitor.desktop") }
        };
    }
    saveDeskletApplets() {
        try {
            const path = GLib.get_home_dir() + "/.local/share/aladin-os/settings.json";
            this.settings.desklet_applets = this.deskletApplets;
            GLib.file_set_contents(path, JSON.stringify(this.settings, null, 2));
        } catch (e) { global.logError("Custom Linux OS: could not save desklet applets: " + e); }
    }
    renderDeskletApplets() {
        if (!this.appletLeft || !this.appletRight) return;
        this.appletLeft.get_children().forEach(child => this.appletLeft.remove_child(child));
        this.appletRight.get_children().forEach(child => this.appletRight.remove_child(child));
        const catalog = this.availableDeskletApplets();
        // The App Menu is a permanent left-side anchor. Other applets are managed
        // in Control Center and stay grouped on the right; no inline remove buttons.
        const menu = new St.BoxLayout({ style_class: "ald-applet-item" });
        menu.add_child(this.action(catalog.menu.label, catalog.menu.run));
        this.appletLeft.add_child(menu);
        const configured = Array.isArray(this.setting("desklet_applets", null))
            ? this.setting("desklet_applets", []).filter((key, index, all) => key !== "menu" && catalog[key] && all.indexOf(key) === index)
            : ["network", "audio", "system"];
        const optional = ["network", "audio", "system"].filter(key => {
            const settingKey = "applet_" + key;
            return this.settings && this.settings[settingKey] !== undefined
                ? Boolean(this.settings[settingKey]) : configured.includes(key);
        });
        optional.forEach(key => {
            const item = new St.BoxLayout({ style_class: "ald-applet-item" });
            item.add_child(this.action(catalog[key].label, catalog[key].run));
            this.appletRight.add_child(item);
        });
    }
    addDeskletApplet() {
        // Applet visibility is controlled from the Custom Linux OS Control Center.
        this.openCustomizer();
    }
    removeDeskletApplet(key) {
        // Kept for compatibility with older desklet instances; changes are made in Control Center.
        this.openCustomizer();
    }
    updateClock() {
        const now = GLib.DateTime.new_now_local();
        let fmt = "%H:%M";
        if (this.setting("clock", "24-hour") === "12-hour") fmt = "%I:%M %p";
        this.clockLabel.set_text(this.wallClock.get_clock_for_format(fmt));
        this.dateLabel.set_text(now.format("%a, %d %b %Y"));
    }
    read(path) {
        try { const out = GLib.file_get_contents(path); return out[0] ? imports.byteArray.toString(out[1]) : ""; }
        catch (e) { return ""; }
    }
    updateSystem() {
        if (!this.cpuLabel && !this.memLabel && !this.diskLabel && !this.upLabel &&
            !this.cpuTempLabel && !this.gpuTempLabel && !this.netSpeedLabel) return;
        try {
            const stat = this.read("/proc/stat").split("\n")[0].trim().split(/\s+/).slice(1).map(Number);
            const idle = stat[3] + (stat[4] || 0);
            const total = stat.reduce((a, b) => a + b, 0);
            if (this.lastCpu) {
                const dt = total - this.lastCpu.total, di = idle - this.lastCpu.idle;
                this.cpuLabel.set_text("CPU  " + (dt ? Math.round(100 * (dt - di) / dt) : 0) + "%");
            }
            this.lastCpu = { total: total, idle: idle };
            const mem = this.read("/proc/meminfo");
            const totalMatch = mem.match(/^MemTotal:\s+(\d+)/m), availMatch = mem.match(/^MemAvailable:\s+(\d+)/m);
            if (totalMatch && availMatch) this.memLabel.set_text("MEM  " + Math.round(100 * (1 - (+availMatch[1] / +totalMatch[1]))) + "%");
            const up = Math.floor(parseFloat(this.read("/proc/uptime").split(/\s+/)[0]) || 0);
            this.upLabel.set_text("UPTIME  " + Math.floor(up / 86400) + "d " + Math.floor((up % 86400) / 3600) + "h");
            if (this.cpuTempLabel) this.cpuTempLabel.set_text("CPU TEMP  " + this.readHardwareTemp(["k10temp", "zenpower", "cpu_thermal"]));
            if (this.gpuTempLabel) this.gpuTempLabel.set_text("GPU TEMP  " + this.readHardwareTemp(["amdgpu", "i915", "nouveau", "nvidia"]));
            if (this.netSpeedLabel) this.updateNetworkSpeed();
            const diskNow = Date.now();
            if (!this.lastDiskUpdate || diskNow - this.lastDiskUpdate > 60000) {
                try {
                    const info = Gio.File.new_for_path("/").query_filesystem_info("filesystem::size,filesystem::free", null);
                    const size = info.get_attribute_uint64("filesystem::size");
                    const free = info.get_attribute_uint64("filesystem::free");
                    this.diskLabel.set_text("SSD  " + (size > 0 ? Math.round(100 * (size - free) / size) + "%" : "n/a"));
                    this.lastDiskUpdate = diskNow;
                } catch (e) { this.diskLabel.set_text("SSD  n/a"); this.lastDiskUpdate = diskNow; }
            }
        } catch (e) { global.logError("Custom Linux OS metrics: " + e); }
    }
    readHardwareTemp(preferredNames) {
        try {
            const root = "/sys/class/hwmon";
            const dirs = GLib.file_test(root, GLib.FileTest.IS_DIR) ? Gio.File.new_for_path(root).enumerate_children("standard::name", Gio.FileQueryInfoFlags.NONE, null) : null;
            if (!dirs) return "n/a";
            let hwmons = [];
            let item;
            while ((item = dirs.next_file(null)) !== null) hwmons.push(item.get_name());
            dirs.close(null);
            for (let i = 0; i < preferredNames.length; i++) {
                for (let j = 0; j < hwmons.length; j++) {
                    const dir = root + "/" + hwmons[j];
                    const name = this.read(dir + "/name").trim().toLowerCase();
                    if (name.indexOf(preferredNames[i]) < 0) continue;
                    let inputs = [];
                    const h = Gio.File.new_for_path(dir).enumerate_children("standard::name", Gio.FileQueryInfoFlags.NONE, null);
                    let f;
                    while ((f = h.next_file(null)) !== null) if (/^temp[0-9]+_input$/.test(f.get_name())) inputs.push(f.get_name());
                    h.close(null);
                    inputs.sort();
                    for (let k = 0; k < inputs.length; k++) {
                        const raw = parseInt(this.read(dir + "/" + inputs[k]).trim(), 10);
                        if (Number.isFinite(raw) && raw > 0 && raw < 150000) return (raw / 1000).toFixed(0) + "°C";
                    }
                }
            }
        } catch (e) { global.log("Custom Linux OS temperature sensor read: " + e); }
        return "n/a";
    }
    updateNetworkSpeed() {
        try {
            const lines = this.read("/proc/net/dev").split("\n").slice(2);
            let rx = 0, tx = 0;
            lines.forEach(line => {
                const parts = line.trim().split(/[:\s]+/);
                if (parts.length < 10 || parts[0] === "lo") return;
                const values = parts.slice(1).map(Number);
                if (values.length >= 9 && values.every(Number.isFinite)) { rx += values[0]; tx += values[8]; }
            });
            const now = Date.now();
            if (this.lastNetwork) {
                const seconds = Math.max(.1, (now - this.lastNetwork.time) / 1000);
                const down = Math.max(0, (rx - this.lastNetwork.rx) / seconds);
                const up = Math.max(0, (tx - this.lastNetwork.tx) / seconds);
                if (this.netSpeedLabel) this.netSpeedLabel.set_text("NET  ↓ " + this.formatSpeed(down) + "  ↑ " + this.formatSpeed(up));
            }
            this.lastNetwork = { rx: rx, tx: tx, time: now };
        } catch (e) { if (this.netSpeedLabel) this.netSpeedLabel.set_text("NET  unavailable"); }
    }
    formatSpeed(bytes) {
        if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + " MB/s";
        if (bytes >= 1024) return (bytes / 1024).toFixed(0) + " KB/s";
        return bytes.toFixed(0) + " B/s";
    }
    updateTaskCount() {
        let open = 0;
        this.taskButtons.forEach((b) => { if (!b.get_label().startsWith("✓")) open++; });
        this.taskCount.set_text(open + " open");
    }
    startFocusTimer() {
        GLib.spawn_command_line_async("notify-send 'Custom Linux OS Focus Timer' '25-minute focus session started'");
        this.timers.push(Mainloop.timeout_add_seconds(1500, () => { GLib.spawn_command_line_async("notify-send 'Custom Linux OS Focus Timer' 'Focus session complete — take a short break.'"); return false; }));
    }
    startBreak() {
        GLib.spawn_command_line_async("zenity --info --title='Custom Linux OS Break' --text='Time for a short break. Stretch, hydrate, and rest your eyes.'");
    }
    on_desklet_removed() {
        if (this.clockSignal) this.wallClock.disconnect(this.clockSignal);
        this.timers.forEach((t) => { try { Mainloop.source_remove(t); } catch (e) {} });
    }
}
function main(metadata, id) { return new AladinOS(metadata, id); }
