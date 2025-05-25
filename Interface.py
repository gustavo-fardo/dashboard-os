import tkinter as tk
from ttkbootstrap import Style
from ttkbootstrap.widgets import Meter, LabelFrame
from tkinter import ttk
from Chart import AreaChartFrame
from GerenciadorDados import GerenciadorDados
import threading
import time

UI_UPDATE_TIME_MS = 5000
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

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.gerenciador = GerenciadorDados()
        
        self.atualiza_thread_running = True

        self.atualiza_thread = threading.Thread(target=self.atualiza_thread_func, daemon=True)
        self.atualiza_thread.start()

        self.clear_widgets()
        self.resources_draw()

    def run(self):
        self.root.mainloop()

    def process_update(self):
        if not self.process_tree.winfo_exists():
            return 
        
        existing_items = set(self.process_tree.get_children())
        process_ids = set()
        
        with self.gerenciador._dictlock:
            proc_dict = self.gerenciador.getProcDict().copy()

        for pid, process in proc_dict.items():
            proc_id = str(pid)
            process_ids.add(proc_id)
            if proc_id in existing_items:
                self.process_tree.item(
                    proc_id, text=proc_id, 
                    values=(process.getNome(), process.getCPU(), process.getMem(), 
                            process.getEstado(), process.getPrioB(), process.getPrioD())
                )
            else:
                self.process_tree.insert(
                    "", "end", iid=proc_id, text=proc_id, 
                    values=(process.getNome(), process.getCPU(), process.getMem(), 
                            process.getEstado(), process.getPrioB(), process.getPrioD())
                )

            thread_ids = set()
            for tid, thread in process.getThreadDict().items():
                tid = "tid-" + str(tid)
                thread_ids.add(tid)
                try:
                    self.process_tree.insert(
                        proc_id, "end", iid=tid,
                        text=f"{tid}",
                        values=(thread.getNome(), thread.getCPU(), thread.getMem(), 
                                thread.getEstado(), thread.getPrioB(), thread.getPrioD())
                    )
                except Exception as e:
                    self.process_tree.item(
                        tid,
                        text=f"{tid}",
                        values=(thread.getNome(), thread.getCPU(), thread.getMem(), 
                                thread.getEstado(), thread.getPrioB(), thread.getPrioD())
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
        self.cur_screen = "process"
        process_button = ttk.Button(self.root, text="View Resources", command=self.redraw_resources)
        process_button.pack(pady=10)

        self.frames["prc"].pack(fill="both", expand=True, padx=10, pady=5)

        tree_scrollbar = ttk.Scrollbar(self.frames["prc"], orient="vertical")
        tree_scrollbar.pack(side="right", fill="y")

        self.process_tree = ttk.Treeview(self.frames["prc"], yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.config(command=self.process_tree.yview)
        
        self.process_tree = ttk.Treeview(self.frames["prc"])

        self.process_tree["columns"] = ("name", "cpu", "memory", "state", "prioB", "prioD")
        self.process_tree.heading("#0", text="PID")
        self.process_tree.heading("name", text="Nome")
        self.process_tree.heading("cpu", text="CPU (%)")
        self.process_tree.heading("memory", text="Memory (MB)")
        self.process_tree.heading("state", text="State")
        self.process_tree.heading("prioB", text="PrioD")
        self.process_tree.heading("prioD", text="PrioB")
        self.process_tree.column("name", width=200, anchor="center")
        self.process_tree.column("cpu", width=60, anchor="center")
        self.process_tree.column("memory", width=80, anchor="center")
        self.process_tree.column("state", width=60, anchor="center")
        self.process_tree.column("prioB", width=60, anchor="center")
        self.process_tree.column("prioD", width=60, anchor="center")
        self.process_tree.pack(fill="both", expand=True)

        self.process_update()

    def resources_update(self):        
        self.meters["cpu"].configure(amounttotal=100, amountused=self.gerenciador._cpuUso)
        self.meters["mem"].configure(amounttotal=self.gerenciador._memTotal, amountused=self.gerenciador._memUso)
        self.meters["memV"].configure(amounttotal=self.gerenciador._memVirtualTotal, amountused=self.gerenciador._memVirtualUso)

        
        self.cpu_chart_frame.update_chart(
            [self.gerenciador._cpuUso,
            self.gerenciador._cpuOcioso,
            self.gerenciador._cpuSistema,
            self.gerenciador._cpuUsuario,
            self.gerenciador._cpuNice,
            self.gerenciador._cpuWait,
            self.gerenciador._cpuIrq,
            self.gerenciador._cpuSoftIrq], 100)
        
        self.mem_chart_frame.update_chart([
            self.gerenciador._memLivre,
            self.gerenciador._memUso,
            self.gerenciador._memBuffer,
            self.gerenciador._memCache], self.gerenciador._memTotal)
        
        self.memV_chart_frame.update_chart([
                self.gerenciador._memVirtualUso,
                self.gerenciador._memVirtualKernelUso
            ], self.gerenciador._memVirtualTotal)

        self.root.update()
        self.root.after(UI_UPDATE_TIME_MS, self.resources_update)

    def resources_draw(self):
        self.cur_screen = "resources"
        process_button = ttk.Button(self.root, text="View Processes", command=self.redraw_processes)
        process_button.pack(pady=10)

        self.frames["cpu"].pack(fill="x", padx=10)
        self.meters["cpu"].pack(side="left", padx=10)

        self.frames["mem"].pack(fill="x", padx=10)
        self.meters["mem"].pack(side="left", padx=10)
        
        self.frames["memV"].pack(fill="x", padx=10)
        self.meters["memV"].pack(side="left", padx=10)
        
        cpu_labels = ["Uso",
            "Ociosas",
            "Sist.",
            "Usuario",
            "Nice",
            "Wait",
            "Irq",
            "Soft Irq"
        ]

        mem_labels = [
            "Livre",
            "Uso",
            "Buffer",
            "Cache"
        ]
        
        memV_labels = [
            "Uso",
            "Kernel Uso"
        ]

        self.cpu_chart_frame = AreaChartFrame(self.frames["cpu"], "CPU Usage (%)", 8, cpu_labels)
        self.mem_chart_frame = AreaChartFrame(self.frames["mem"], "Memory Usage (MB)", 4, mem_labels)
        self.memV_chart_frame = AreaChartFrame(self.frames["memV"], "Virtual Memory Usage (MB)", 2, memV_labels)

        self.resources_update()


    def redraw_processes(self):
        self.clear_widgets()
        self.process_draw()

    def redraw_resources(self):
        self.clear_widgets()
        self.resources_draw()

    def clear_widgets(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.frames = {
            "cpu": LabelFrame(self.root, text="CPU"), 
            "mem": LabelFrame(self.root, text="Memory"), 
            "memV": LabelFrame(self.root, text="Virtual Memory"),
            "prc": LabelFrame(self.root, text="Processes", padding=20)
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
        self.atualiza_thread_running = False
        if self.atualiza_thread.is_alive():
            self.atualiza_thread.join(timeout=1)
        self.root.destroy()
    
    def atualiza_thread_func(self):
        while self.atualiza_thread_running:
            if self.cur_screen == "resources":
                self.gerenciador._atualizaMemInfo()
                self.gerenciador._atualizaCPUInfo()
            else:
                self.gerenciador._atualizaProcDict()
            time.sleep(DATA_UPDATE_TIME_S)
            

if __name__ == "__main__":
    app = Interface()
    app.run()
