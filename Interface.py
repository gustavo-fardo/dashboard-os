import tkinter as tk
from ttkbootstrap import Style
from ttkbootstrap.widgets import Meter, LabelFrame
from tkinter import ttk
from Chart import LineChartFrame
from GerenciadorDados import GerenciadorDados
import threading
import time
from FileInfo import FileInfo

UI_UPDATE_TIME_MS = 1000
DATA_UPDATE_TIME_S = 0.5

class Interface:
    def __init__(self):
        self.style = Style(theme="cyborg")
        self.root = self.style.master
        self.root.title("Dashboard-OS")
        self.root.resizable(True, True)
        # self.root.attributes('-zoomed', True)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{int(screen_width*0.9)}x{int(screen_height*0.9)}")
        self.root.minsize(1000, 1000)
        self.cur_screen = ""
        self.proc_info_pid = None

        # Limpar janela e encerrar Thread
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.gerenciador = GerenciadorDados()
        self.fileinfo = FileInfo()
        
        self.atualiza_thread_running = True

        # Thread para buscar e atualizar dados no objeto do Gerenciador de Dados
        self.atualiza_thread = threading.Thread(target=self.atualiza_thread_func, daemon=True)
        self.atualiza_thread.start()

        self.clear_widgets()
        self.resources_draw()

    def run(self):
        self.root.mainloop()

    def process_update(self):
        
        if not self.process_tree.winfo_exists() or self.cur_screen != "process":
            return 
        
        existing_items = set(self.process_tree.get_children())
        process_ids = set()
        
        with self.gerenciador._dictlock:
            proc_dict = dict(sorted(self.gerenciador.getProcDict().items(), key=lambda item: item[1].getCPU(), reverse=True))

        for pid, process in proc_dict.items():
            proc_id = str(pid)
            process_ids.add(proc_id)
            if proc_id in existing_items:
                self.process_tree.item(
                    proc_id, text=proc_id, 
                    values=(process.getNome(), process.getUsuario(), process.getCPU(), process.getMem(), 
                            process.getEstado(), process.getPrioB(), process.getPrioD(), process.getReadIO(),
                            process.getWriteIO(), ">>")
                )
            else:
                self.process_tree.insert(
                    "", "end", iid=proc_id, text=proc_id, 
                    values=(process.getNome(), process.getUsuario(), process.getCPU(), process.getMem(), 
                            process.getEstado(), process.getPrioB(), process.getPrioD(),  process.getReadIO(),
                            process.getWriteIO(), ">>")
                )

            thread_ids = set()
            for tid, thread in process.getThreadDict().items():
                tid = str(tid) + " (TID)" 
                thread_ids.add(tid)
                try:
                    self.process_tree.insert(
                        proc_id, "end", iid=tid,
                        text=f"{tid}",
                        values=(thread.getNome(), thread.getUsuario(), thread.getCPU(), thread.getMem(), 
                                thread.getEstado(), thread.getPrioB(), thread.getPrioD(), "")
                    )
                except Exception as e:
                    self.process_tree.item(
                        tid,
                        text=f"{tid}",
                        values=(thread.getNome(), thread.getUsuario(), thread.getCPU(), thread.getMem(), 
                                thread.getEstado(), thread.getPrioB(), thread.getPrioD(), "")
                    )
                    
            for child in self.process_tree.get_children(proc_id):
                if child not in thread_ids:
                    self.process_tree.delete(child)

        for item in existing_items:
            if item not in process_ids:
                self.process_tree.delete(item)

        self.root.update()
        self.root.after(UI_UPDATE_TIME_MS, self.process_update)

    def process_draw(self):
        """
            Cria árvore de processos/threads e botão para voltar a tela de recursos.
            Registra ultima coluna como botão de ação para ver detalhes de um processo
        """
        self.cur_screen = "process"
        process_button = ttk.Button(self.root, text="Ver Recursos", command=self.redraw_resources)
        process_button.pack(pady=10)

        self.frames["prc"].pack(fill="both", expand=True, padx=10, pady=5)

        tree_scrollbar = ttk.Scrollbar(self.frames["prc"], orient="vertical")
        tree_scrollbar.pack(side="right", fill="y")

        self.process_tree = ttk.Treeview(self.frames["prc"], yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.config(command=self.process_tree.yview)
        
        self.process_tree = ttk.Treeview(self.frames["prc"])
        
        self.process_tree.bind('<ButtonRelease-1>', self.on_treeview_click)

        self.process_tree["columns"] = ("name", "user", "cpu", "memory", "state", "prioB", "prioD", "leitura", "escrita", "action")
        self.process_tree.heading("#0", text="PID")
        self.process_tree.heading("name", text="Nome")
        self.process_tree.heading("user", text="Usuário")
        self.process_tree.heading("cpu", text="CPU (%)")
        self.process_tree.heading("memory", text="Memória (MB)")
        self.process_tree.heading("state", text="Estado")
        self.process_tree.heading("prioB", text="PrioD")
        self.process_tree.heading("prioD", text="PrioB")
        self.process_tree.heading("leitura", text="Leitura (MB)")
        self.process_tree.heading("escrita", text="Escrita(MB)")
        self.process_tree.heading("action", text="Detalhes")
        self.process_tree.column("#0", width=100, anchor="center")
        self.process_tree.column("name", width=240, anchor="center")
        self.process_tree.column("user", width=60, anchor="center")
        self.process_tree.column("cpu", width=60, anchor="center")
        self.process_tree.column("memory", width=100, anchor="center")
        self.process_tree.column("state", width=60, anchor="center")
        self.process_tree.column("prioB", width=60, anchor="center")
        self.process_tree.column("prioD", width=60, anchor="center")
        self.process_tree.column("leitura", width=100, anchor="center")
        self.process_tree.column("escrita", width=100, anchor="center")
        self.process_tree.column("action", width=80, anchor="center")
        self.process_tree.pack(fill="both", expand=True)

        self.process_update()

    def resources_update(self):
        """
            Atualiza medidores e charts com os dados atuais em self.gerenciador em intervalos
            definidos por UPDATE_TIME_MS
        """
        if self.cur_screen != "resources":
            return
        
        # Atualiza valor nos medidores
        self.meters["cpu"].configure(amounttotal=100, amountused=self.gerenciador.getCpuUso())
        self.meters["mem"].configure(amounttotal=self.gerenciador.getMemTotal(), amountused=self.gerenciador.getMemUso())
        self.meters["memV"].configure(amounttotal=self.gerenciador.getMemVirtualTotal(), amountused=self.gerenciador.getMemVirtualUso())

        self.cpu_chart_frame.update_chart(
            [self.gerenciador.getCpuUso(),
            self.gerenciador.getCpuOcioso(),
            self.gerenciador.getCpuSistema(),
            self.gerenciador.getCpuUsuario(),
            self.gerenciador.getCpuNice(),
            self.gerenciador.getCpuWait(),
            self.gerenciador.getCpuIrq(),
            self.gerenciador.getCpuSoftIrq()], 100)
        
        self.mem_chart_frame.update_chart([
            self.gerenciador.getMemLivre(),
            self.gerenciador.getMemUso(),
            self.gerenciador.getMemBuffer(),
            self.gerenciador.getMemCache()], self.gerenciador.getMemTotal())
        
        self.memV_chart_frame.update_chart([
                self.gerenciador.getMemVirtualTotal(),
                self.gerenciador.getMemVirtualKernelUso(),
                self.gerenciador.getMemVirtualUso()
            ], self.gerenciador.getMemVirtualUso())

        # Info de número de threads e processos
        self.process_info.config(text=f"Num. Processos: {self.gerenciador.getNumProcessos()}")
        self.threads_info.config(text=f"Num. Threads: {self.gerenciador.getNumThreads()}")
        
        # Info de detalhes de CPU
        self.cpu_info["Uso"].config(text=f"Uso: {self.gerenciador.getCpuUso():.2f} %")
        self.cpu_info["Ociosas"].config(text=f"Ociosas: {self.gerenciador.getCpuOcioso():.2f} %")
        self.cpu_info["Sist."].config(text=f"Sist.: {self.gerenciador.getCpuSistema():.2f} %")
        self.cpu_info["Usuario"].config(text=f"Usuario: {self.gerenciador.getCpuUsuario():.2f} %")
        self.cpu_info["Nice"].config(text=f"Nice: {self.gerenciador.getCpuNice():.2f} %")
        self.cpu_info["Wait"].config(text=f"Wait: {self.gerenciador.getCpuWait():.2f} %")
        self.cpu_info["Irq"].config(text=f"Irq: {self.gerenciador.getCpuIrq():.2f} %")
        self.cpu_info["Soft Irq"].config(text=f"Soft Irq: {self.gerenciador.getCpuSoftIrq():.2f} %")
        
        # Info de detalhes de RAM
        self.mem_info["Livre"].config(text=f"Livre: {self.gerenciador.getMemLivre():.2f} MB")
        self.mem_info["Uso"].config(text=f"Uso: {self.gerenciador.getMemUso():.2f} MB")
        self.mem_info["Buffer"].config(text=f"Buffer: {self.gerenciador.getMemBuffer():.2f} MB")
        self.mem_info["Cache"].config(text=f"Cache: {self.gerenciador.getMemCache():.2f} MB")
        
        # Info de detalhes de VRAM
        self.memv_info["Limite"].config(text=f"Limite: {self.gerenciador.getMemVirtualTotal():.2f} MB")
        self.memv_info["Kernel Uso"].config(text=f"Kernel Uso: {self.gerenciador.getMemVirtualKernelUso():.2f} MB")
        self.memv_info["Requerida"].config(text=f"Requerida: {self.gerenciador.getMemVirtualUso():.2f} MB")
        
        self.root.update()
        self.root.after(UI_UPDATE_TIME_MS, self.resources_update)

    def resources_draw(self):
        """
            Insere frames de medidores/gráficos na janela root para a tela de recursos
        """
        self.cur_screen = "resources"
                
        top_button_frame = ttk.Frame(self.root)
        top_button_frame.pack(side="top", pady=10)

        mountinfobutton = ttk.Button(top_button_frame, text="Ver Partições", command=self.redraw_mountinfo)
        filetree_button = ttk.Button(top_button_frame, text="Navegar nos diretórios", command=self.redraw_filetree)
        process_button = ttk.Button(top_button_frame, text="Ver Processos", command=self.redraw_processes)
        mountinfobutton.pack(side="left", padx=10, pady=10)
        filetree_button.pack(side="left", padx=10, pady=10)
        process_button.pack(side="left", padx=10, pady=10)

        self.frames["cpu"].pack(fill="x", padx=10)
        self.meters["cpu"].pack(side="left", padx=10)

        self.frames["mem"].pack(fill="x", padx=10)
        self.meters["mem"].pack(side="left", padx=10)
        
        self.frames["memV"].pack(fill="x", padx=10)
        self.meters["memV"].pack(side="left", padx=10)
        
        self.cpu_proc_frame = ttk.Frame(self.frames["cpu"])
        self.cpu_proc_frame.pack(side="right", padx=10)
        
        self.process_info = ttk.Label(self.cpu_proc_frame, text=f"Processes: {self.gerenciador.getNumProcessos()}")
        self.process_info.pack(anchor='w')
        self.threads_info = ttk.Label(self.cpu_proc_frame, text=f"Threads: {self.gerenciador.getNumThreads()}")
        self.threads_info.pack(anchor='w')
        
        self.mem_info_frame = ttk.Frame(self.frames["mem"])
        self.mem_info_frame.pack(side="left", padx=10)
        
        self.memv_info_frame = ttk.Frame(self.frames["memV"])
        self.memv_info_frame.pack(side="left", padx=10)
        
        self.cpu_info_frame = ttk.Frame(self.frames["cpu"])
        self.cpu_info_frame.pack(side="left", padx=10)
        
        self.cpu_labels = [
            "Uso",
            "Ociosas",
            "Sist.",
            "Usuario",
            "Nice",
            "Wait",
            "Irq",
            "Soft Irq"
        ]

        self.mem_labels = [
            "Livre",
            "Uso",
            "Buffer",
            "Cache"
        ]
        
        self.memV_labels = [
            "Limite",
            "Kernel Uso",
            "Requerida"
        ]
        
        self.mem_info = {}
        for l in self.mem_labels:
            self.mem_info[l] = ttk.Label(self.mem_info_frame, text=f"{l}: -")
            self.mem_info[l].pack(anchor='w')
        
        self.cpu_info = {}
        for l in self.cpu_labels:
            self.cpu_info[l] = ttk.Label(self.cpu_info_frame, text=f"{l}: -")
            self.cpu_info[l].pack(anchor='w')
        
        self.memv_info = {}
        for l in self.memV_labels:
            self.memv_info[l] = ttk.Label(self.memv_info_frame, text=f"{l}: -")
            self.memv_info[l].pack(anchor='w')


        self.cpu_chart_frame = LineChartFrame(self.frames["cpu"], "Uso CPU (%)", 8, self.cpu_labels)
        self.mem_chart_frame = LineChartFrame(self.frames["mem"], "Uso de Memória (MB)", 4, self.mem_labels)
        self.memV_chart_frame = LineChartFrame(self.frames["memV"], "Alocação de Memória Virtual (MB)", 3, self.memV_labels)

        self.resources_update()

    def redraw_processes(self):
        self.clear_widgets()
        self.process_draw()

    def redraw_proc_info(self):
        self.clear_widgets()
        self.draw_proc_info()

    def redraw_resources(self):
        self.clear_widgets()
        self.resources_draw()

    def clear_widgets(self):
        """
        Limpa tela root e reinicializa frames
        """
        for widget in self.root.winfo_children():
            widget.destroy()

        self.frames = {
            "cpu": LabelFrame(self.root, text="CPU"), 
            "mem": LabelFrame(self.root, text="Memória Física"), 
            "memV": LabelFrame(self.root, text="Memória Virtual"),
            "finfo": LabelFrame(self.root, text="Diretórios", padding=20),
            "mount": LabelFrame(self.root, text="Partições", padding=20),
            "prc": LabelFrame(self.root, text="Processos", padding=20),
            "prc_info": LabelFrame(self.root, text="Detalhes de Processo", padding=20),
        }

        self.meters = {
            "cpu": Meter(self.frames["cpu"], textright='%', metertype='semi',
                 bootstyle='info', subtext='CPU'),
            "mem": Meter(self.frames["mem"], metertype="semi", textright='MB',
                 bootstyle="primary", subtext='Memória Física'),
            "memV": Meter(self.frames["memV"], metertype="semi", textright='MB',
                  bootstyle="light", subtext='Memória Virtual Requisitada')
        }

    def on_close(self):
        """
            Finaliza thread de atualização de dados e fecha janela
        """
        self.atualiza_thread_running = False
        if self.atualiza_thread.is_alive():
            self.atualiza_thread.join(timeout=1)
        self.root.destroy()
    
    def atualiza_thread_func(self):
        """
            Função para atualizar dados do gerenciador periódicamente
        """
        while self.atualiza_thread_running:
            with self.fileinfo._dictlock:
                self.fileinfo.mostrar_info_particoes()
            self.fileinfo.list_dir()
            self.gerenciador.atualizaDados()
            time.sleep(DATA_UPDATE_TIME_S)
            
    def on_treeview_click(self, event):
        """
            Callback para click em um elemento da árvore de processos
        """
        region = self.process_tree.identify_region(event.x, event.y)
        
        if region == "cell":
            column = self.process_tree.identify_column(event.x)
            item = self.process_tree.identify_row(event.y)
            
            if item:
                col_name = self.process_tree.heading(column)["text"]
                text = self.process_tree.item(item, 'text')
                
                if not "(TID)" in text:
                    if col_name == "Detalhes":
                        self.proc_info_pid = text
                        self.redraw_proc_info()

    def draw_proc_info(self):
        """
            Insere frame de informações do processo selecionado na tela de processos
        """
        self.cur_screen = "proc_info"
        process_button = ttk.Button(self.root, text="Ver Processos", command=self.redraw_processes)
        process_button.pack(pady=10)

        self.frames["prc_info"].pack(fill="both", expand=True, padx=10, pady=5)

        self.proc_labels = [
            "id", "nome", "usuario", "cpuUso", "memUso", 
            "numThreads", "memVirtualUso", 
            "estado", "prioB", "prioD",
            "memSegments", "leitura", "escrita"
        ]
        
        self.proc_info = {}
            
        self.proc_info["id"] = ttk.Label(self.frames["prc_info"])
        self.proc_info["nome"] = ttk.Label(self.frames["prc_info"])
        self.proc_info["usuario"] = ttk.Label(self.frames["prc_info"])
        self.proc_info["cpuUso"] = ttk.Label(self.frames["prc_info"])
        self.proc_info["memUso"] = ttk.Label(self.frames["prc_info"])
        
        self.proc_info["numThreads"] = ttk.Label(self.frames["prc_info"])
        self.proc_info["memVirtualUso"] = ttk.Label(self.frames["prc_info"])
        
        self.proc_info["estado"] = ttk.Label(self.frames["prc_info"])
        self.proc_info["prioB"] = ttk.Label(self.frames["prc_info"])
        self.proc_info["prioD"] = ttk.Label(self.frames["prc_info"])
        
        self.proc_info["memSegments"] = ttk.Label(self.frames["prc_info"])

        self.proc_info["leitura"] = ttk.Label(self.frames["prc_info"])
        self.proc_info["escrita"] = ttk.Label(self.frames["prc_info"])

        # Infos de IO
        # Main container for both left and right panels
        container = ttk.Frame(self.frames["prc_info"])
        container.pack(fill="both", expand=True)

        # Left frame: process info labels
        left_panel = ttk.Frame(container, width=400)
        left_panel.pack(side="left", fill="both", padx=10, pady=10)

        # Right frame: IO Tree
        right_panel = ttk.Frame(container)
        right_panel.pack(side="right", fill="both", expand=True, padx=50, pady=10)

        # Store labels inside left_panel instead of frames["prc_info"]
        self.proc_info = {}
        for key in self.proc_labels:
            self.proc_info[key] = ttk.Label(left_panel)
            self.proc_info[key].pack(anchor="w")

        def create_tree(title, height=5):
            """
            Helper function to create a treeview with a scrollbar
            """
            tree_title = ttk.Label(right_panel, text=title, font=("Segoe UI", 10, "bold"))
            tree_title.pack(side="top", anchor="w", padx=5, pady=(10, 2))

            tree_container = ttk.Frame(right_panel)
            tree_container.pack(side="top", fill="both", expand=False)

            tree_scrollbar = ttk.Scrollbar(tree_container, orient="vertical")
            tree_scrollbar.pack(side="right", fill="y")

            tree = ttk.Treeview(tree_container, height=height, yscrollcommand=tree_scrollbar.set)
            tree.pack(side="left", fill="both", expand=True)

            tree_scrollbar.config(command=tree.yview)
            
            return tree

        # File Tree
        self.io_tree = create_tree("Recursos Abertos/Alocados", height=10)
        self.io_tree["columns"] = ("tipo", "caminho")
        self.io_tree.heading("#0", text="Descritor")
        self.io_tree.heading("tipo", text="Tipo")
        self.io_tree.heading("caminho", text="Caminho")
        self.io_tree.column("#0", width=50, anchor="center")
        self.io_tree.column("tipo", width=50, anchor="center")
        self.io_tree.column("caminho", width=100, anchor="w")

        # Socket Tree
        self.socket_tree = create_tree("Sockets", height=5)
        self.socket_tree["columns"] = ("tipo", "local", "remoto", "estado")
        self.socket_tree.heading("#0", text="Descritor")
        self.socket_tree.heading("tipo", text="Tipo")
        self.socket_tree.heading("local", text="IP Local")
        self.socket_tree.heading("remoto", text="IP Remoto")
        self.socket_tree.heading("estado", text="Estado")
        self.socket_tree.column("#0", width=50, anchor="center")
        self.socket_tree.column("tipo", width=50, anchor="center")
        self.socket_tree.column("local",  width=50, anchor="center")
        self.socket_tree.column("remoto", width=50, anchor="center")
        self.socket_tree.column("estado",  width=50, anchor="center")

        # Semaphore Tree
        self.semaphore_tree = create_tree("Semáforos", height=5)
        self.semaphore_tree["columns"] = ("dono", "estado", "permissoes")
        self.semaphore_tree.heading("#0", text="Semáforo")
        self.semaphore_tree.heading("dono", text="Dono (UID)")
        self.semaphore_tree.heading("estado", text="Estado")
        self.semaphore_tree.heading("permissoes", text="Permissões")
        self.semaphore_tree.column("#0", width=150, anchor="center")
        self.semaphore_tree.column("dono", width=50, anchor="center")
        self.semaphore_tree.column("estado", width=50, anchor="center")
        self.semaphore_tree.column("permissoes", width=100, anchor="center")

        # IO Devices Tree
        self.io_devices_tree = create_tree("Dispositivos de I/O", height=5)
        self.io_devices_tree["columns"] = ("path")
        self.io_devices_tree.heading("#0", text="Descritor")
        self.io_devices_tree.heading("path", text="Caminho do Dispositivo")
        self.io_devices_tree.column("#0", width=50, anchor="center")
        self.io_devices_tree.column("path", width=200, anchor="w")

        self.process_update()
        self.proc_info_update()
            
    def proc_info_update(self):
        """
            Atualiza periódicamente dados de processos selecionado
        """
        if self.cur_screen != "proc_info":
            return 
        
        proc = self.gerenciador.getProcDict()[int(self.proc_info_pid)]
        
        mem_seg_text = ""
        for seg_key, seg_val in proc.getMemSegments().items():
            mem_seg_text += f"        {seg_key}\n                Num. Pag.: {seg_val['pages']}\n                Tamanho: {seg_val['size_kb']} KB\n"
        
        self.proc_info["id"].config(text=f"PID: {proc.getID()}")
        self.proc_info["nome"].config(text=f"Nome: {proc.getNome()}")
        self.proc_info["usuario"].config(text=f"Usuário: {proc.getUsuario()}")
        self.proc_info["cpuUso"].config(text=f"Uso de CPU: {proc.getCPU():.2f}%")
        self.proc_info["memUso"].config(text=f"Uso de RAM: {proc.getMem():.2f} MB")
        
        self.proc_info["numThreads"].config(text=f"Threads: {proc.getNumThreads()}")
        self.proc_info["memVirtualUso"].config(text=f"VRAM: {proc.getMemVirt():.2f} MB")
        
        self.proc_info["estado"].config(text=f"Estado: {proc.getEstado()}")
        self.proc_info["prioB"].config(text=f"Prioridade Base: {proc.getPrioB()}")
        self.proc_info["prioD"].config(text=f"Prioridade Dinâmica: {proc.getPrioD()}")
        
        self.proc_info["memSegments"].config(text=f"Segmentos de Memória:\n{mem_seg_text}")

        self.proc_info["leitura"].config(text=f"Leitura de Disco: {proc.getReadIO():.2f} MB")
        self.proc_info["escrita"].config(text=f"Escrita de Disco: {proc.getWriteIO():.2f} MB")

        existing_items = set(self.io_tree.get_children())
        dictIO = proc.getDictIO()

        # IO Tree
        for file in dictIO.get("file_descriptors", []):
            fd = file.get("fd", "")
            tipo = file.get("type", "Arquivo")
            path = file.get("real_path", "")
            if fd in existing_items:
                self.io_tree.item(
                    fd, text=fd, 
                    values=(tipo, path)
                )
            else:
                self.io_tree.insert(
                    "", "end", iid=fd, text=fd, 
                    values=(tipo, path)
                )

        # Socket Tree
        for socket in dictIO.get("sockets", []):
            fd = socket.get("fd", "")
            socket_info = socket.get("info", {})
            tipo = socket_info.get("proto", "UNIX")
            local = socket_info.get("local", "")
            remoto = socket_info.get("remote", "")
            estado = socket_info.get("state", "")
            if fd in existing_items:
                self.socket_tree.item(
                    fd, text=fd, 
                    values=(tipo, local, remoto, estado)
                )
            else:
                self.socket_tree.insert(
                    "", "end", iid=fd, text=fd, 
                    values=(tipo, local, remoto, estado)
                )

        # Semaphore Tree
        for sem in dictIO.get("posix_semaphores", []):
            sem_name = sem.get("name", "")
            owner_uid = sem.get("owner_uid", "")
            state = sem.get("state", "")
            permissions = sem.get("permissions", "")
            if sem_name in existing_items:
                self.semaphore_tree.item(
                    sem_name, text=sem_name, 
                    values=(owner_uid, state, permissions)
                )
            else:
                self.semaphore_tree.insert(
                    "", "end", iid=sem_name, text=sem_name, 
                    values=(owner_uid, state, permissions)
                )

        # IO Devices Tree
        for device in dictIO.get("io_devices", []):
            fd = device.get("fd", "")
            device_path = device.get("device_path", "")
            if fd in existing_items:
                self.io_devices_tree.item(
                    fd, text=fd, 
                    values=(device_path,)
                )
            else:
                self.io_devices_tree.insert(
                    "", "end", iid=fd, text=fd, 
                    values=(device_path,)
                )

        self.root.after(UI_UPDATE_TIME_MS, self.proc_info_update)

    def redraw_filetree(self, reset=True):
        if reset:
            self.fileinfo.list_dir("/")
        self.clear_widgets()
        self.filetree_draw()

    def filetree_draw(self):
        """
            Cria árvore de arquivos e botão para voltar a tela principal
        """
        self.cur_screen = "filetree"
        process_button = ttk.Button(self.root, text="Voltar", command=self.redraw_resources)
        process_button.pack(pady=10)

        self.frames["finfo"].pack(fill="both", expand=True, padx=10, pady=5)

        tree_scrollbar = ttk.Scrollbar(self.frames["finfo"], orient="vertical")
        tree_scrollbar.pack(side="right", fill="y")

        self.file_tree = ttk.Treeview(self.frames["finfo"], yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.config(command=self.file_tree.yview)
        
        self.file_tree = ttk.Treeview(self.frames["finfo"])
        
        self.file_tree.bind('<ButtonRelease-1>', self.onfiletree_click)
        
        self.file_tree["columns"] = ("name", "size", "inode", "type")
        self.file_tree.heading("#0", text="Path")
        self.file_tree.heading("name", text="Nome")
        self.file_tree.heading("size", text="Tamanho (bytes)")
        self.file_tree.heading("inode", text="I Node")
        self.file_tree.heading("type", text="Tipo")
        
        self.file_tree.column("#0")
        self.file_tree.column("name", width=240)
        self.file_tree.column("size", width=60)
        self.file_tree.column("inode", width=60)
        self.file_tree.column("type", width=100)
        self.file_tree.pack(fill="both", expand=True)

        self.filetree_update()
        
    def filetree_update(self):
        if not self.file_tree.winfo_exists() or self.cur_screen != "filetree":
            return 
        
        child = self.fileinfo.folder_content

        for fullpath, c in child.items():
            if fullpath in set(self.file_tree.get_children()):
                self.file_tree.item(
                    fullpath, text=fullpath, 
                    values=(c["fname"], c["size"], c["inode"], c["tipo"]),
                    tags=[c["fullpath"], c["tipo"]]
                )
            else:
                self.file_tree.insert(
                    "", "end", iid=fullpath, text=fullpath, 
                    values=(c["fname"], c["size"], c["inode"], c["tipo"]),
                    tags=[c["fullpath"], c["tipo"]]
                )
                    
        self.root.update()
        self.root.after(UI_UPDATE_TIME_MS, self.filetree_update)
        
    def onfiletree_click(self, event):
        """
            Callback para click em um elemento da árvore de arquivos
        """
        item = self.file_tree.identify_row(event.y)
        
        if item:
            tags = self.file_tree.item(item, 'tags')
            if tags[1] == "DIR":
                self.fileinfo.list_dir(tags[0])
                self.redraw_filetree(False)

    def redraw_mountinfo(self):
        self.clear_widgets()
        self.mountinfo_draw()

    def mountinfo_draw(self):
        """
            Cria árvore de arquivos e botão para voltar a tela principal
        """
        self.cur_screen = "mountinfo"
        process_button = ttk.Button(self.root, text="Voltar", command=self.redraw_resources)
        process_button.pack(pady=10)

        self.frames["mount"].pack(fill="both", expand=True, padx=10, pady=5)

        tree_scrollbar = ttk.Scrollbar(self.frames["mount"], orient="vertical")
        tree_scrollbar.pack(side="right", fill="y")

        self.file_tree = ttk.Treeview(self.frames["mount"], yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.config(command=self.file_tree.yview)
        
        self.file_tree = ttk.Treeview(self.frames["mount"])
        
        self.file_tree["columns"] = ("mountp", "total", "usado", "disp", "usopct")
        self.file_tree.heading("#0", text="Disposivo")
        self.file_tree.heading("mountp", text="Mount Point")
        self.file_tree.heading("total", text="Total")
        self.file_tree.heading("usado", text="Usado")
        self.file_tree.heading("disp", text="Disponível")
        self.file_tree.heading("usopct", text="Uso (%)")
        
        self.file_tree.column("#0")
        self.file_tree.column("mountp")
        self.file_tree.column("total")
        self.file_tree.column("usado")
        self.file_tree.column("disp")
        self.file_tree.column("usopct")
        self.file_tree.pack(fill="both", expand=True)

        self.mountinfo_update()

    def mountinfo_update(self):
        if not self.file_tree.winfo_exists() or self.cur_screen != "mountinfo":
            return 
        
        particoes = self.fileinfo.particoes

        for c in particoes:
            if c["disp"] in set(self.file_tree.get_children()):
                self.file_tree.item(
                    c["disp"], text=c["disp"], 
                    values=(c["mountp"], c["total"], c["usado"], c["dispo"], c["uso_pct"])
                )
            else:
                self.file_tree.insert(
                    "", "end", iid=c["disp"], text=c["disp"], 
                    values=(c["mountp"], c["total"], c["usado"], c["dispo"], c["uso_pct"])
                )
                    
        self.root.update()
        self.root.after(UI_UPDATE_TIME_MS, self.mountinfo_update)


if __name__ == "__main__":    
    app = Interface()
    app.run()
