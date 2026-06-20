import os
import shutil
import tkinter as tk
from tkinter import messagebox
import winshell
import customtkinter as ctk
import ctypes
from PIL import Image, ImageTk
import win32ui
import win32gui
import webbrowser

# Configuração do tema MD3-like
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AppLab(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AppLab v1.4 - Gerenciador de Aplicativos (Ultra Smooth)")
        self.geometry("900x600")
        self.minsize(850, 550) # Impede que a UI quebre ao encolher demais

        self.categories = {} # Armazenamento por categorias
        self.pinned_apps = set() # Apps favoritos
        self.selected_app_name = None
        self.icon_cache = {} # Cache para performance ultra rápida
        self.render_queue = [] # Fila para renderização suave
        self.render_job = None # Referência da tarefa de renderização

        # Layout Principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar (Barra Lateral)
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="AppLab", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.pack(pady=20, padx=20)

        self.search_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Buscar programa...")
        self.search_entry.pack(pady=10, padx=10, fill="x")
        self.search_entry.bind("<KeyRelease>", self.filter_apps)
        self.search_entry.bind("<Return>", lambda e: self.run_app()) # Enter pra abrir logo o app

        # Botões de Ação na Sidebar
        self.btn_run = ctk.CTkButton(self.sidebar, text="Executar", command=self.run_app, fg_color="#4CAF50", hover_color="#388E3C")
        self.btn_run.pack(pady=10, padx=20, fill="x")

        self.btn_admin = ctk.CTkButton(self.sidebar, text="Executar (Adm)", command=lambda: self.run_app(admin=True), fg_color="#F44336", hover_color="#D32F2F")
        self.btn_admin.pack(pady=10, padx=20, fill="x")

        self.btn_folder = ctk.CTkButton(self.sidebar, text="Abrir Local", command=self.open_file_location, fg_color="#FF9800", hover_color="#F57C00")
        self.btn_folder.pack(pady=10, padx=20, fill="x")

        self.btn_desktop = ctk.CTkButton(self.sidebar, text="Add Desktop", command=self.add_to_desktop)
        self.btn_desktop.pack(pady=10, padx=20, fill="x")

        self.btn_properties = ctk.CTkButton(self.sidebar, text="Propriedades", command=self.show_properties, fg_color="#9C27B0", hover_color="#7B1FA2")
        self.btn_properties.pack(pady=10, padx=20, fill="x")

        self.btn_uninstall = ctk.CTkButton(self.sidebar, text="Desinstalar", command=self.uninstall_app, fg_color="#E91E63", hover_color="#C2185B")
        self.btn_uninstall.pack(pady=10, padx=20, fill="x")

        self.btn_refresh = ctk.CTkButton(self.sidebar, text="Atualizar Lista", command=self.load_apps, fg_color="transparent", border_width=2, border_color="#1f538d")
        self.btn_refresh.pack(pady=(20, 10), padx=20, fill="x")

        self.btn_about = ctk.CTkButton(self.sidebar, text="Sobre", command=self.show_about, fg_color="transparent", text_color="#888888")
        self.btn_about.pack(side="bottom", pady=20, padx=20, fill="x")

        # Área Principal de Conteúdo
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(self.content_frame, text="Programas Instalados", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w", pady=(0, 20))

        # Lista de Apps (Scrollable)
        self.scroll_frame = ctk.CTkScrollableFrame(self.content_frame, fg_color="#1a1a1a", corner_radius=10)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.app_buttons = []

        self.load_apps()

    def get_icon(self, path, size=64):
        """Extrai o ícone de um arquivo .lnk ou .exe"""
        if path in self.icon_cache:
            return self.icon_cache[path]

        try:
            # Tenta resolver o atalho para pegar o ícone do executável real (melhor qualidade)
            icon_source = path
            if path.lower().endswith(".lnk"):
                try:
                    icon_source = winshell.shortcut(path).path
                except:
                    pass
            
            # Fallback se o caminho resolvido for inválido ou não existir
            if not icon_source or not os.path.exists(icon_source):
                icon_source = path

            # SHGetFileInfo é mais robusto para ícones de alta qualidade
            class SHFILEINFOW(ctypes.Structure):
                _fields_ = [("hIcon", ctypes.c_void_p),
                            ("iIcon", ctypes.c_int),
                            ("dwAttributes", ctypes.c_uint32),
                            ("szDisplayName", ctypes.c_wchar * 260),
                            ("szTypeName", ctypes.c_wchar * 80)]

            sfi = SHFILEINFOW()
            # SHGFI_ICON (0x100) | SHGFI_LARGEICON (0x0)
            res = ctypes.windll.shell32.SHGetFileInfoW(icon_source, 0, ctypes.byref(sfi), ctypes.sizeof(sfi), 0x100 | 0x0)
            
            if res and sfi.hIcon:
                h_icon = sfi.hIcon
                # Cria um DC compatível para renderização HD
                hdc_screen = win32gui.GetDC(0)
                hdc = win32ui.CreateDCFromHandle(hdc_screen)
                mem_dc = hdc.CreateCompatibleDC()
                
                hbmp = win32ui.CreateBitmap()
                hbmp.CreateCompatibleBitmap(hdc, size, size)
                mem_dc.SelectObject(hbmp)
                
                # DI_NORMAL (0x0003) garante canal Alpha (transparência)
                win32gui.DrawIconEx(mem_dc.GetSafeHdc(), 0, 0, h_icon, size, size, 0, None, 0x0003)

                bmpinfo = hbmp.GetInfo()
                bmpstr = hbmp.GetBitmapBits(True)
                img = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRA', 0, 1)
                # Redimensiona com Lanczos para suavizar as bordas se necessário
                img = img.resize((size, size), Image.Resampling.LANCZOS)

                win32gui.ReleaseDC(0, hdc_screen)
                win32gui.DestroyIcon(h_icon)

                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
                self.icon_cache[path] = ctk_img
                return ctk_img
        except Exception as e:
            print(f"Erro ao carregar ícone para {path}: {e}")
            
        return None

    def load_apps(self):
        paths = [
            os.path.join(os.environ['PROGRAMDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
            os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs')
        ]

        self.categories.clear()

        for path in paths:
            if os.path.exists(path):
                for root_dir, dirs, files in os.walk(path):
                    for file in files:
                        if file.endswith(".lnk"):
                            name = file.replace(".lnk", "")
                            full_path = os.path.join(root_dir, file)
                            
                            # Identificação inteligente de categoria
                            target_path = ""
                            try:
                                target_path = winshell.shortcut(full_path).path.lower()
                            except:
                                pass
                            
                            # Se o destino for no Windows, System32 ou for um atalho de sistema
                            if "windows" in target_path or "system32" in target_path:
                                category = "SISTEMA"
                            else:
                                category = "APPS"
                            
                            # Se tiver nos favoritos, move pra lá
                            if name in self.pinned_apps:
                                self.categories["⭐ FAVORITOS"][name] = full_path
                                continue

                            if category not in self.categories:
                                self.categories[category] = {}
                            
                            self.categories[category][name] = full_path
        
        self.render_apps()

    def render_apps(self, filter_text=""):
        """Prepara a fila de renderização para não travar a UI"""
        if self.render_job:
            self.after_cancel(self.render_job)

        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.app_buttons = []
        self.render_queue = []

          # Monta a lista de tarefas (Headers e Botões)
        for category, apps in sorted(self.categories.items()):
            filtered_apps = {n: p for n, p in apps.items() if filter_text.lower() in n.lower()}
            
            if filtered_apps:
                self.render_queue.append(("header", category))
                for name, path in filtered_apps.items():
                    self.render_queue.append(("app", (name, path)))

        self.process_render_queue()

    def process_render_queue(self, index=0):
        """Cria os widgets em lotes de 5 para manter o scroll suave"""
        batch_size = 8
        for _ in range(batch_size):
            if index >= len(self.render_queue):
                return

            type, data = self.render_queue[index]
            if type == "header":
                lbl = ctk.CTkLabel(self.scroll_frame, text=f"─── {data} ───", 
                                  font=ctk.CTkFont(size=11, weight="bold"), text_color="#555555")
                lbl.pack(fill="x", pady=(15, 5), padx=15, anchor="w")
            else:
                name, path = data
                icon = self.get_icon(path)
                btn = ctk.CTkButton(
                    self.scroll_frame, text=f"  {name}", image=icon, 
                    anchor="w", fg_color="transparent", text_color="white",
                    hover_color="#2b2b2b", height=60, corner_radius=8,
                    command=lambda n=name: self.select_app(n)
                )
                btn.pack(fill="x", pady=1, padx=10)
                btn.bind("<Double-Button-1>", lambda e, n=name: self.on_double_click(n))
                # Botão direito para menu secreto
                btn.bind("<Button-3>", lambda e, n=name: self.show_context_menu(e, n))
                self.app_buttons.append(btn)
            
            index += 1
        
        # Agenda o próximo lote
        self.render_job = self.after(1, lambda: self.process_render_queue(index))

    def show_context_menu(self, event, name):
        """Menu de contexto com opções de power user"""
        self.select_app(name)
        menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", borderwidth=0)
        
        is_pinned = name in self.pinned_apps
        menu.add_command(label="⭐ " + ("Desafixar" if is_pinned else "Fixar no Topo"), 
                         command=lambda: self.toggle_pin(name))
        menu.add_separator()
        menu.add_command(label="💻 Abrir no Terminal (CMD)", command=self.open_in_cmd)
        menu.add_command(label="📂 Abrir Local", command=self.open_file_location)
        menu.add_separator()
        menu.add_command(label="🛡️ Executar como Admin", command=lambda: self.run_app(True))
        menu.add_command(label="⚙️ Propriedades", command=self.show_properties)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def toggle_pin(self, name):
        if name in self.pinned_apps:
            self.pinned_apps.remove(name)
        else:
            self.pinned_apps.add(name)
        self.load_apps() # Recarrega pra mover de categoria

    def on_double_click(self, name):
        self.select_app(name)
        self.run_app()

    def select_app(self, name):
        self.selected_app_name = name
        # Destacar o selecionado
        for btn in self.app_buttons:
            if btn.cget("text").strip() == name: # Limpa os espaços pra comparar certo
                btn.configure(fg_color="#1f538d")
            else:
                btn.configure(fg_color="transparent")

    def filter_apps(self, event):
        self.render_apps(self.search_entry.get())

    def get_selected_app(self):
        if not self.selected_app_name:
            return None
        # Busca o caminho nas categorias
        for apps in self.categories.values():
            if self.selected_app_name in apps:
                return self.selected_app_name, apps[self.selected_app_name]
        return None

    def open_in_cmd(self):
        selected = self.get_selected_app()
        if selected:
            _, path = selected
            try:
                target = winshell.shortcut(path).path or path
                folder = os.path.dirname(target)
                os.system(f'start cmd /k "cd /d {folder}"')
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao abrir terminal: {e}")

    def run_app(self, admin=False):
        selected = self.get_selected_app()
        if selected:
            name, path = selected
            if not os.path.exists(path):
                messagebox.showerror("Erro", "O atalho não existe mais. Atualize a lista.")
                return

            try:
                if admin:
                    # Executa como Administrador usando ShellExecute
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", path, None, None, 1)
                else:
                    os.startfile(path)
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível abrir o programa: {e}")

    def show_properties(self):
        selected = self.get_selected_app()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione um programa primeiro.")
            return

        name, path = selected
        try:
            # Resolve o atalho de forma segura
            try:
                shortcut = winshell.shortcut(path)
                target_path = shortcut.path or "N/A"
                working_dir = shortcut.working_directory or "N/A"
                description = shortcut.description or "N/A"
            except:
                target_path = path
                working_dir = "N/A"
                description = "Não foi possível extrair metadados do atalho."
            
            # Janela de propriedades estilo MD3
            prop_win = ctk.CTkToplevel(self)
            prop_win.title(f"Propriedades - {name}")
            prop_win.geometry("500x380")
            prop_win.resizable(False, False)
            prop_win.after(100, lambda: prop_win.focus())
            prop_win.attributes("-topmost", True)

            ctk.CTkLabel(prop_win, text="Propriedades do Atalho", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)
            
            frame = ctk.CTkFrame(prop_win, fg_color="#2b2b2b")
            frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

            def add_row(label, text):
                row = ctk.CTkFrame(frame, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=5)
                ctk.CTkLabel(row, text=label, font=ctk.CTkFont(weight="bold"), width=100, anchor="w").pack(side="left")
                entry = ctk.CTkEntry(row)
                entry.insert(0, str(text))
                entry.configure(state="readonly") # Apenas leitura mas permite copiar
                entry.pack(side="left", fill="x", expand=True, padx=(5, 0))

            add_row("Nome:", name)
            add_row("Destino:", target_path)
            add_row("Início em:", working_dir)
            add_row("Descrição:", description)
            add_row("Arquivo:", path)

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao ler propriedades: {e}")

    def open_file_location(self):
        selected = self.get_selected_app()
        if selected:
            _, path = selected
            try:
                #  atalho para abrir o local do arquivo real
                try:
                    target = winshell.shortcut(path).path
                except:
                    target = path
                
                if not target or not os.path.exists(target): target = path
                os.system(f'explorer /select,"{os.path.normpath(target)}"')
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível abrir a pasta: {e}")

    def add_to_desktop(self):
        selected = self.get_selected_app()
        if selected:
            name, path = selected
            try:
                desktop = winshell.desktop()
                destination = os.path.join(desktop, os.path.basename(path))
                shutil.copy(path, destination)
                messagebox.showinfo("Sucesso", f"Atalho para '{name}' criado!")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao criar atalho: {e}")

    def uninstall_app(self):
        selected = self.get_selected_app()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione um programa primeiro.")
            return

        name, _ = selected
        if messagebox.askyesno("Desinstalar", f"Deseja desinstalar '{name}'?\nO AppLab abrirá a ferramenta de Programas e Recursos do Windows."):
            try:
                os.startfile("appwiz.cpl")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível abrir o desinstalador: {e}")

    def show_about(self):
        about_win = ctk.CTkToplevel(self)
        about_win.title("Sobre - AppLab")
        about_win.geometry("450x220")
        about_win.resizable(False, False)
        about_win.after(100, lambda: about_win.focus())
        about_win.attributes("-topmost", True)

        # Frame principal com bordas arredondadas
        frame = ctk.CTkFrame(about_win, corner_radius=15)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Container central para alinhar foto e texto
        content_layout = ctk.CTkFrame(frame, fg_color="transparent")
        content_layout.pack(expand=True)

        # --- Espaço para a foto do asset ---
        try:
            img_path = os.path.join("assets", "logo.png")
            if os.path.exists(img_path):
                self.about_logo = ctk.CTkImage(Image.open(img_path), size=(80, 80)) # self para manter a referência
                ctk.CTkLabel(content_layout, image=self.about_logo, text="").pack(side="left", padx=(0, 20))
        except Exception:
            pass

        # Coluna de Informações
        info = ctk.CTkFrame(content_layout, fg_color="transparent")
        info.pack(side="left")

        ctk.CTkLabel(info, text="AppLab v1.3", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(info, text="by: juu.dev", font=ctk.CTkFont(size=14, slant="italic")).pack(anchor="w")

        link = ctk.CTkLabel(info, text="GitHub: rip-pky", text_color="#1f538d", cursor="hand2", font=ctk.CTkFont(underline=True))
        link.pack(anchor="w", pady=(15, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/rip-pky"))

if __name__ == "__main__":
    app = AppLab()
    app.mainloop()
