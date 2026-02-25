import os
import re
import csv
import queue
import threading
from dataclasses import dataclass
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# -------------------------
# Model
# -------------------------

@dataclass
class RenameItem:
    old_path: str
    old_name: str
    new_name: str
    reason: str  # "match", "already_prefixed", "collision_skip", "no_match", ...
    will_rename: bool


def build_regex(pattern: str, ignore_case: bool, word_only: bool) -> re.Pattern:
    flags = re.UNICODE
    if ignore_case:
        flags |= re.IGNORECASE

    if word_only and pattern:
        pattern = r"\b" + pattern + r"\b"

    return re.compile(pattern, flags)


def make_unique_name(folder: str, desired_name: str) -> str:
    base, ext = os.path.splitext(desired_name)
    candidate = desired_name
    n = 1
    while os.path.exists(os.path.join(folder, candidate)):
        candidate = f"{base} ({n}){ext}"
        n += 1
    return candidate


def plan_rename_for_path(
    path: str,
    rx: re.Pattern,
    prefix: str,
    skip_already_prefixed: bool,
    collision_mode: str,  # "skip" | "overwrite" | "number"
) -> RenameItem:
    name = os.path.basename(path)

    if skip_already_prefixed and name.startswith(prefix):
        return RenameItem(path, name, name, "already_prefixed", False)

    if rx.search(name):
        desired = prefix + name
        folder = os.path.dirname(path)
        new_name = desired
        new_path = os.path.join(folder, new_name)

        if os.path.exists(new_path):
            if collision_mode == "skip":
                return RenameItem(path, name, new_name, "collision_skip", False)
            if collision_mode == "overwrite":
                return RenameItem(path, name, new_name, "match_overwrite", True)
            if collision_mode == "number":
                unique = make_unique_name(folder, desired)
                return RenameItem(path, name, unique, "match_numbered", True)

        return RenameItem(path, name, new_name, "match", True)

    return RenameItem(path, name, name, "no_match", False)


def scan_folder(
    folder: str,
    rx: re.Pattern,
    prefix: str,
    recursive: bool,
    skip_already_prefixed: bool,
    collision_mode: str,
) -> list[RenameItem]:
    items: list[RenameItem] = []

    if recursive:
        for root, _, files in os.walk(folder):
            for f in files:
                p = os.path.join(root, f)
                if os.path.isfile(p):
                    items.append(plan_rename_for_path(p, rx, prefix, skip_already_prefixed, collision_mode))
    else:
        for f in os.listdir(folder):
            p = os.path.join(folder, f)
            if os.path.isfile(p):
                items.append(plan_rename_for_path(p, rx, prefix, skip_already_prefixed, collision_mode))

    return items


def scan_files(
    files: list[str],
    rx: re.Pattern,
    prefix: str,
    skip_already_prefixed: bool,
    collision_mode: str,
) -> list[RenameItem]:
    items: list[RenameItem] = []
    for p in files:
        if os.path.isfile(p):
            items.append(plan_rename_for_path(p, rx, prefix, skip_already_prefixed, collision_mode))
    return items


def write_csv_log(log_path: str, rows: list[dict]):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    fieldnames = ["timestamp", "status", "old_path", "new_path", "reason", "error"]
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# -------------------------
# UI
# -------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI_ Prefix Renamer (regex) — Windows 11")
        self.geometry("1040x700")
        self.minsize(980, 640)

        self.msg_queue: queue.Queue = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.stop_flag = threading.Event()

        # Mode & selections
        self.var_mode = tk.StringVar(value="folder")  # "folder" | "files"
        self.var_folder = tk.StringVar(value="")
        self.selected_files: list[str] = []

        # Params
        self.var_pattern = tk.StringVar(value="LLM")
        self.var_prefix = tk.StringVar(value="AI_")

        self.var_recursive = tk.BooleanVar(value=True)
        self.var_ignore_case = tk.BooleanVar(value=False)
        self.var_word_only = tk.BooleanVar(value=False)
        self.var_skip_prefixed = tk.BooleanVar(value=True)

        self.var_dry_run = tk.BooleanVar(value=True)
        self.var_collision = tk.StringVar(value="number")  # "number" | "skip" | "overwrite"

        # State
        self.scanned_items: list[RenameItem] = []
        self.var_status = tk.StringVar(value="Prêt.")
        self.var_count_total = tk.StringVar(value="Total: 0")
        self.var_count_rename = tk.StringVar(value="À renommer: 0")
        self.var_scope = tk.StringVar(value="Cible: (aucune)")

        self._build_ui()
        self.after(100, self._poll_queue)

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # Mode frame
        mode = ttk.LabelFrame(self, text="Cible")
        mode.pack(fill="x", **pad)

        ttk.Radiobutton(mode, text="Dossier", variable=self.var_mode, value="folder", command=self._refresh_scope_ui)\
            .grid(row=0, column=0, sticky="w", padx=10, pady=4)
        ttk.Radiobutton(mode, text="Fichiers (multi-sélection)", variable=self.var_mode, value="files", command=self._refresh_scope_ui)\
            .grid(row=0, column=1, sticky="w", padx=10, pady=4)

        ttk.Label(mode, textvariable=self.var_scope).grid(row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(2, 6))

        # Folder picker row
        self.frame_folder = ttk.Frame(mode)
        self.frame_folder.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 6))
        ttk.Label(self.frame_folder, text="Dossier:").grid(row=0, column=0, sticky="w")
        self.entry_folder = ttk.Entry(self.frame_folder, textvariable=self.var_folder)
        self.entry_folder.grid(row=0, column=1, sticky="ew", padx=(6, 6))
        ttk.Button(self.frame_folder, text="Parcourir…", command=self.pick_folder).grid(row=0, column=2, sticky="e")
        self.frame_folder.columnconfigure(1, weight=1)

        # Files picker row
        self.frame_files = ttk.Frame(mode)
        self.frame_files.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 6))
        ttk.Button(self.frame_files, text="Choisir des fichiers…", command=self.pick_files).grid(row=0, column=0, sticky="w")
        ttk.Button(self.frame_files, text="Vider la sélection", command=self.clear_files).grid(row=0, column=1, sticky="w", padx=(8, 0))

        # Params frame
        params = ttk.LabelFrame(self, text="Règle")
        params.pack(fill="x", **pad)

        ttk.Label(params, text="Regex:").grid(row=0, column=0, sticky="w", padx=10, pady=4)
        ttk.Entry(params, textvariable=self.var_pattern, width=28).grid(row=0, column=1, sticky="w", padx=(0, 10), pady=4)

        ttk.Label(params, text="Préfixe:").grid(row=0, column=2, sticky="w", padx=10, pady=4)
        ttk.Entry(params, textvariable=self.var_prefix, width=12).grid(row=0, column=3, sticky="w", padx=(0, 10), pady=4)

        ttk.Checkbutton(params, text="Ignore la casse", variable=self.var_ignore_case).grid(row=1, column=0, sticky="w", padx=10, pady=4)
        ttk.Checkbutton(params, text="Mot isolé (\\b...\\b)", variable=self.var_word_only).grid(row=1, column=1, sticky="w", padx=10, pady=4)
        ttk.Checkbutton(params, text="Ignorer si déjà préfixé", variable=self.var_skip_prefixed).grid(row=1, column=2, sticky="w", padx=10, pady=4)

        ttk.Checkbutton(params, text="Récursif (sous-dossiers)", variable=self.var_recursive).grid(row=2, column=0, sticky="w", padx=10, pady=4)
        ttk.Checkbutton(params, text="Mode simulation (dry-run)", variable=self.var_dry_run).grid(row=2, column=1, sticky="w", padx=10, pady=4)

        ttk.Label(params, text="Collision:").grid(row=2, column=2, sticky="e", padx=(10, 4), pady=4)
        cmb = ttk.Combobox(params, textvariable=self.var_collision, state="readonly",
                           values=["number", "skip", "overwrite"], width=12)
        cmb.grid(row=2, column=3, sticky="w", padx=(0, 10), pady=4)

        # Buttons
        btns = ttk.Frame(self)
        btns.pack(fill="x", **pad)

        self.btn_scan = ttk.Button(btns, text="Prévisualiser", command=self.scan)
        self.btn_scan.pack(side="left")

        self.btn_run = ttk.Button(btns, text="Exécuter (renommer)", command=self.run, state="disabled")
        self.btn_run.pack(side="left", padx=(8, 0))

        self.btn_stop = ttk.Button(btns, text="Stop", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))

        # Counts + progress
        info = ttk.Frame(self)
        info.pack(fill="x", **pad)

        ttk.Label(info, textvariable=self.var_count_total).pack(side="left")
        ttk.Label(info, text="  |  ").pack(side="left")
        ttk.Label(info, textvariable=self.var_count_rename).pack(side="left")

        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(0, 8))

        ttk.Label(self, textvariable=self.var_status).pack(fill="x", padx=10, pady=(0, 8))

        # Preview
        columns = ("old", "new", "action", "reason", "path")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        self.tree.heading("old", text="Nom actuel")
        self.tree.heading("new", text="Nouveau nom")
        self.tree.heading("action", text="Action")
        self.tree.heading("reason", text="Raison")
        self.tree.heading("path", text="Chemin")
        self.tree.column("old", width=250)
        self.tree.column("new", width=250)
        self.tree.column("action", width=110)
        self.tree.column("reason", width=140)
        self.tree.column("path", width=420)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        frame_tree = ttk.Frame(self)
        frame_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree.pack(in_=frame_tree, side="left", fill="both", expand=True)
        vsb.pack(in_=frame_tree, side="right", fill="y")

        self._refresh_scope_ui()

    def _refresh_scope_ui(self):
        mode = self.var_mode.get()
        if mode == "folder":
            self.frame_folder.grid()
            self.frame_files.grid_remove()
        else:
            self.frame_files.grid()
            self.frame_folder.grid_remove()

        self._update_scope_label()

    def _update_scope_label(self):
        if self.var_mode.get() == "folder":
            d = self.var_folder.get().strip()
            self.var_scope.set(f"Cible: Dossier = {d if d else '(non défini)'}")
        else:
            n = len(self.selected_files)
            self.var_scope.set(f"Cible: {n} fichier(s) sélectionné(s)")

    def pick_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.var_folder.set(d)
            self._update_scope_label()

    def pick_files(self):
        paths = filedialog.askopenfilenames(
            title="Choisir des fichiers",
            filetypes=[("Tous les fichiers", "*.*")],
        )
        if paths:
            # Tk renvoie un tuple de str
            self.selected_files = list(paths)
            self._update_scope_label()

    def clear_files(self):
        self.selected_files = []
        self._update_scope_label()

    def _clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _get_rx(self) -> re.Pattern | None:
        pattern = self.var_pattern.get()
        try:
            return build_regex(pattern, self.var_ignore_case.get(), self.var_word_only.get())
        except re.error as e:
            messagebox.showerror("Regex invalide", f"Erreur regex: {e}")
            return None

    def scan(self):
        prefix = self.var_prefix.get()
        if prefix == "":
            messagebox.showerror("Erreur", "Le préfixe ne peut pas être vide.")
            return

        rx = self._get_rx()
        if rx is None:
            return

        self.var_status.set("Scan en cours…")
        self.update_idletasks()

        collision_mode = self.var_collision.get()

        if self.var_mode.get() == "folder":
            folder = self.var_folder.get().strip()
            if not folder or not os.path.isdir(folder):
                messagebox.showerror("Erreur", "Choisis un dossier valide.")
                return

            self.scanned_items = scan_folder(
                folder=folder,
                rx=rx,
                prefix=prefix,
                recursive=self.var_recursive.get(),
                skip_already_prefixed=self.var_skip_prefixed.get(),
                collision_mode=collision_mode,
            )
            base_for_log = folder
        else:
            if not self.selected_files:
                messagebox.showerror("Erreur", "Choisis au moins un fichier.")
                return

            self.scanned_items = scan_files(
                files=self.selected_files,
                rx=rx,
                prefix=prefix,
                skip_already_prefixed=self.var_skip_prefixed.get(),
                collision_mode=collision_mode,
            )
            # log dans le dossier du premier fichier
            base_for_log = os.path.dirname(self.selected_files[0])

        total = len(self.scanned_items)
        will = sum(1 for it in self.scanned_items if it.will_rename)

        self.var_count_total.set(f"Total: {total}")
        self.var_count_rename.set(f"À renommer: {will}")
        self.progress["value"] = 0
        self.progress["maximum"] = max(1, will)

        self._clear_tree()
        sorted_items = sorted(self.scanned_items, key=lambda x: (not x.will_rename, x.reason, x.old_name.lower()))
        for it in sorted_items[:3000]:
            action = "RENOMMER" if it.will_rename else "—"
            self.tree.insert("", "end", values=(it.old_name, it.new_name, action, it.reason, it.old_path))

        self.btn_run.configure(state="normal" if will > 0 else "disabled")

        self.var_status.set(f"Scan terminé. {will} fichier(s) à renommer.")
        if total > 3000:
            self.var_status.set(self.var_status.get() + " (Aperçu limité à 3000 lignes)")

        # store log dir for run
        self._log_base_dir = base_for_log

    def run(self):
        if not self.scanned_items:
            messagebox.showinfo("Info", "Fais d'abord une prévisualisation.")
            return

        todo = [it for it in self.scanned_items if it.will_rename]
        if not todo:
            messagebox.showinfo("Info", "Aucun fichier à renommer.")
            return

        dry = self.var_dry_run.get()
        if not dry:
            if not messagebox.askyesno("Confirmation", "Renommer les fichiers maintenant ?"):
                return

        self.stop_flag.clear()
        self.btn_scan.configure(state="disabled")
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")

        self.progress["value"] = 0
        self.progress["maximum"] = max(1, len(todo))
        self.var_status.set("Traitement en cours…")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(self._log_base_dir, f"AI_prefix_rename_log_{ts}.csv")

        self.worker_thread = threading.Thread(
            target=self._worker_rename,
            args=(todo, log_path, dry, self.var_collision.get()),
            daemon=True,
        )
        self.worker_thread.start()

    def stop(self):
        self.stop_flag.set()
        self.var_status.set("Arrêt demandé…")

    def _worker_rename(self, items: list[RenameItem], log_path: str, dry_run: bool, collision_mode: str):
        log_rows: list[dict] = []
        processed = 0

        for it in items:
            if self.stop_flag.is_set():
                self.msg_queue.put(("status", "Arrêté par l'utilisateur."))
                break

            old_path = it.old_path
            folder = os.path.dirname(old_path)
            new_path = os.path.join(folder, it.new_name)

            status = "DRY_RUN" if dry_run else "RENAMED"
            error = ""

            try:
                if not dry_run:
                    if collision_mode == "overwrite":
                        os.replace(old_path, new_path)  # remplace si existe
                    else:
                        os.rename(old_path, new_path)
            except Exception as e:
                status = "ERROR"
                error = str(e)

            processed += 1
            log_rows.append({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "status": status,
                "old_path": old_path,
                "new_path": new_path,
                "reason": it.reason,
                "error": error,
            })

            self.msg_queue.put(("progress", processed))
            self.msg_queue.put(("status", f"{'Simulation' if dry_run else 'Renommage'}: {processed}/{len(items)}"))

        try:
            write_csv_log(log_path, log_rows)
            self.msg_queue.put(("status", f"Terminé. Log CSV: {log_path}"))
        except Exception as e:
            self.msg_queue.put(("status", f"Terminé, mais log CSV impossible: {e}"))

        self.msg_queue.put(("done", None))

    def _poll_queue(self):
        try:
            while True:
                msg, payload = self.msg_queue.get_nowait()
                if msg == "progress":
                    self.progress["value"] = payload
                elif msg == "status":
                    self.var_status.set(payload)
                elif msg == "done":
                    self.btn_scan.configure(state="normal")
                    self.btn_stop.configure(state="disabled")
                    # laisse "Exécuter" réactivable après scan
                    if self.scanned_items and any(it.will_rename for it in self.scanned_items):
                        self.btn_run.configure(state="normal")
        except queue.Empty:
            pass

        self.after(100, self._poll_queue)


if __name__ == "__main__":
    App().mainloop()