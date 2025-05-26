import tkinter as tk
from ttkbootstrap import Style
from ttkbootstrap.widgets import Meter, LabelFrame
from tkinter import ttk
from Chart import LineChartFrame
from GerenciadorDados import GerenciadorDados
import threading
import time

UI_UPDATE_TIME_MS = 1000
DATA_UPDATE_TIME_S = 0.5

class Interface:
    def __init__(self):
        self.style = Style(theme="cyborg")
        self.root = self.style.master
        self.root.title("Dashboard-OS")
        self.root.resizable(True, True)
        self.root.attributes('-zoomed', True)
        self.root.minsize(1000, 1000)
        self.cur_screen = ""
        self.proc_info_pid = None

        # Limpar janela e encerrar Thread
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.gerenciador = GerenciadorDados()
        
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
                            process.getEstado(), process.getPrioB(), process.getPrioD(), ">>")
                )
            else:
                self.process_tree.insert(
                    "", "end", iid=proc_id, text=proc_id, 
                    values=(process.getNome(), process.getUsuario(), process.getCPU(), process.getMem(), 
                            process.getEstado(), process.getPrioB(), process.getPrioD(), ">>")
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
        process_button = ttk.Button(self.root, text="View Resources", command=self.redraw_resources)
        process_button.pack(pady=10)

        self.frames["prc"].pack(fill="both", expand=True, padx=10, pady=5)

        tree_scrollbar = ttk.Scrollbar(self.frames["prc"], orient="vertical")
        tree_scrollbar.pack(side="right", fill="y")

        self.process_tree = ttk.Treeview(self.frames["prc"], yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.config(command=self.process_tree.yview)
        
        self.process_tree = ttk.Treeview(self.frames["prc"])
        
        self.process_tree.bind('<ButtonRelease-1>', self.on_treeview_click)

        self.process_tree["columns"] = ("name", "user", "cpu", "memory", "state", "prioB", "prioD", "action")
        self.process_tree.heading("#0", text="PID")
        self.process_tree.heading("name", text="Nome")
        self.process_tree.heading("user", text="Usuário")
        self.process_tree.heading("cpu", text="CPU (%)")
        self.process_tree.heading("memory", text="Memory (MB)")
        self.process_tree.heading("state", text="State")
        self.process_tree.heading("prioB", text="PrioD")
        self.process_tree.heading("prioD", text="PrioB")
        self.process_tree.heading("action", text="Detalhes")
        self.process_tree.column("#0", width=100, anchor="center")
        self.process_tree.column("name", width=240, anchor="center")
        self.process_tree.column("user", width=60, anchor="center")
        self.process_tree.column("cpu", width=60, anchor="center")
        self.process_tree.column("memory", width=100, anchor="center")
        self.process_tree.column("state", width=60, anchor="center")
        self.process_tree.column("prioB", width=60, anchor="center")
        self.process_tree.column("prioD", width=60, anchor="center")
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
                self.gerenciador.getMemVirtualLivre(),
                self.gerenciador.getMemVirtualUso()
            ], self.gerenciador.getMemVirtualTotal())

        # Info de número de threads e processos
        self.process_info.config(text=f"Processes: {self.gerenciador.getNumProcessos()}")
        self.threads_info.config(text=f"Threads: {self.gerenciador.getNumThreads()}")
        
        # Info de detalhes de CPU
        self.cpu_info["Uso"].config(text=f"Uso: {self.gerenciador.getCpuUso():.2f} %")
        self.cpu_info["Ociosas"].config(text=f"Ociosas: {self.gerenciador.getCpuOcioso():.2f} %")
        self.cpu_info["Sist."].config(text=f"Sist.: {self.gerenciador.getCpuSistema():.2f} %")
        self.cpu_info["Usuario"].config(text=f"Usuario: {self.gerenciador.getCpuUsuario():.2f} %")
        self.cpu_info["Nice"].config(text=f"Nice: {self.gerenciador.getCpuNice():.2f} %")
        self.cpu_info["Wait"].config(text=f"Wait: {self.gerenciador.getCpuWait():.2f} %")
        self.cpu_info["Irq"].config(text=f"Soft Irq: {self.gerenciador.getCpuIrq():.2f} %")
        self.cpu_info["Soft Irq"].config(text=f"Soft Irq: {self.gerenciador.getCpuSoftIrq():.2f} %")
        
        # Info de detalhes de RAM
        self.mem_info["Livre"].config(text=f"Livre: {self.gerenciador.getMemLivre():.2f} MB")
        self.mem_info["Uso"].config(text=f"Uso: {self.gerenciador.getMemUso():.2f} MB")
        self.mem_info["Buffer"].config(text=f"Buffer: {self.gerenciador.getMemBuffer():.2f} MB")
        self.mem_info["Cache"].config(text=f"Cache: {self.gerenciador.getMemCache():.2f} MB")
        
        # Info de detalhes de VRAM
        self.memv_info["Uso"].config(text=f"Buffer: {self.gerenciador.getMemVirtualUso():.2f} MB")
        self.memv_info["Kernel Uso"].config(text=f"Cache: {self.gerenciador.getMemVirtualKernelUso():.2f} MB")
        
        self.root.update()
        self.root.after(UI_UPDATE_TIME_MS, self.resources_update)

    def resources_draw(self):
        """
            Insere frames de medidores/gráficos na janela root para a tela de recursos
        """
        self.cur_screen = "resources"
        process_button = ttk.Button(self.root, text="View Processes", command=self.redraw_processes)
        process_button.pack(pady=10)

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
            "Uso",
            "Kernel Uso"
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


        self.cpu_chart_frame = LineChartFrame(self.frames["cpu"], "CPU Usage (%)", 8, self.cpu_labels)
        self.mem_chart_frame = LineChartFrame(self.frames["mem"], "Memory Usage (MB)", 4, self.mem_labels)
        self.memV_chart_frame = LineChartFrame(self.frames["memV"], "Virtual Memory Usage (MB)", 2, self.memV_labels)

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
            "mem": LabelFrame(self.root, text="Memory"), 
            "memV": LabelFrame(self.root, text="Virtual Memory"),
            "prc": LabelFrame(self.root, text="Processes", padding=20),
            "prc_info": LabelFrame(self.root, text="Process Info", padding=20)
        }

        self.meters = {
            "cpu": Meter(self.frames["cpu"], textright='%', metertype='semi',
                 bootstyle='info', subtext='CPU'),
            "mem": Meter(self.frames["mem"], metertype="semi", textright='mb',
                 bootstyle="primary", subtext='Memory'),
            "memV": Meter(self.frames["memV"], metertype="semi", textright='mb',
                  bootstyle="light", subtext='Virtual Memory')
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
        process_button = ttk.Button(self.root, text="View Processes", command=self.redraw_processes)
        process_button.pack(pady=10)

        self.frames["prc_info"].pack(fill="both", expand=True, padx=10, pady=5)

        self.proc_labels = [
            "id", "nome", "usuario", "cpuUso", "memUso", 
            "numThreads", "memVirtualUso", 
            "estado", "prioB", "prioD",
            "memSegments"
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
        
        for l in self.proc_labels:
            self.proc_info[l].pack(anchor='w')

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
            mem_seg_text += f"        {seg_key}\n                Num. Pag.: {seg_val['pages']}\n                Size: {seg_val['size_kb']} KB\n"
        
        self.proc_info["id"].config(text=f"PID: {proc.getID()}")
        self.proc_info["nome"].config(text=f"Name: {proc.getNome()}")
        self.proc_info["usuario"].config(text=f"User: {proc.getUsuario()}")
        self.proc_info["cpuUso"].config(text=f"CPU Use: {proc.getCPU():.2f}%")
        self.proc_info["memUso"].config(text=f"RAM Use: {proc.getMem():.2f} MB")
        
        self.proc_info["numThreads"].config(text=f"Threads: {proc.getNumThreads()}")
        self.proc_info["memVirtualUso"].config(text=f"VRAM: {proc.getMemVirt():.2f} MB")
        
        self.proc_info["estado"].config(text=f"State: {proc.getEstado()}")
        self.proc_info["prioB"].config(text=f"prioB: {proc.getPrioB()}")
        self.proc_info["prioD"].config(text=f"prioD: {proc.getPrioD()}")
        
        self.proc_info["memSegments"].config(text=f"Memory Segments:\n{mem_seg_text}")

        self.root.after(UI_UPDATE_TIME_MS, self.proc_info_update)


if __name__ == "__main__":
    app = Interface()
    app.run()
