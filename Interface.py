import tkinter as tk
from ttkbootstrap import Style
from ttkbootstrap.widgets import Meter, LabelFrame
from tkinter import ttk
from Chart import AreaChartFrame
from GerenciadorDados import GerenciadorDados
from Processo import Processo

UPDATE_TIME_MS = 500

class Interface:
    def __init__(self):
        self.style = Style(theme="cyborg")
        self.root = self.style.master
        self.root.title("Linux System Overview - Mocked")
        self.root.attributes('-zoomed', True)
        # self.root.state('zoomed')
        self.root.resizable(True, True)

        self.gerenciador = GerenciadorDados()

        self.clear_widgets()
        self.resources_draw()

    def run(self):
        self.root.mainloop()

    def process_update(self):
        existing_items = set(self.process_tree.get_children())
        process_ids = set()

        for proc_id, process in self.gerenciador.getProcDict().items():
            proc_id = str(proc_id) 
            process_ids.add(proc_id)
            if f"proc_{proc_id}" in existing_items:
                self.process_tree.item(
                    f"proc_{proc_id}", text=process.getID(), 
                    values=(process.getNome(), process.getCPU(), process.getMem(), 
                            process.getEstado(), process.getPrioB(), process.getPrioD())
                )
            else:
                self.process_tree.insert(
                    "", "end", iid=f"proc_{proc_id}", text=process.getID(), 
                    values=(process.getNome(), process.getCPU(), process.getMem(), 
                            process.getEstado(), process.getPrioB(), process.getPrioD())
                )

            thread_ids = set()
            for tid, thread in process.getThreadDict().items():
                tid = str(tid)
                thread_ids.add(tid)
                if tid in self.process_tree.get_children(f"proc_{proc_id}"):
                        self.process_tree.item(
                        tid,
                        text=f"Thread: {thread.getNome()} (TID: {tid})",
                        values=(thread.getNome(), thread.getCPU(), thread.getMem(), 
                                thread.getEstado(), thread.getPrioB(), thread.getPrioD())
                    )
                else:
                    self.process_tree.insert(
                        f"proc_{proc_id}", "end", iid=tid,
                        text=f"Thread: {thread.getNome()} (TID: {tid})",
                        values=(thread.getNome(), thread.getCPU(), thread.getMem(), 
                                thread.getEstado(), thread.getPrioB(), thread.getPrioD())
                    )
                    
            for child in self.process_tree.get_children(f"proc_{proc_id}"):
                if child not in thread_ids:
                    self.process_tree.delete(child)

        for item in existing_items:
            if item not in process_ids:
                self.process_tree.delete(item)

        self.root.update()
        self.root.after(UPDATE_TIME_MS, self.process_update)

    def process_draw(self):
        process_button = ttk.Button(self.root, text="View Resources", command=self.redraw_resources)
        process_button.pack(pady=10)

        self.frames["prc"].pack(fill="both", padx=10, pady=5)
        self.process_tree = ttk.Treeview(self.frames["prc"])

        self.process_tree["columns"] = ("name", "cpu", "memory", "state", "prioB", "prioD")
        self.process_tree.heading("#0", text="PID")
        self.process_tree.heading("name", text="Nome")
        self.process_tree.heading("cpu", text="CPU")
        self.process_tree.heading("memory", text="Memory")
        self.process_tree.heading("state", text="State")
        self.process_tree.heading("prioB", text="PrioD")
        self.process_tree.heading("prioD", text="PrioB")
        self.process_tree.column("name", width=60, anchor="center")
        self.process_tree.column("cpu", width=60, anchor="center")
        self.process_tree.column("memory", width=80, anchor="center")
        self.process_tree.column("state", width=60, anchor="center")
        self.process_tree.column("prioB", width=60, anchor="center")
        self.process_tree.column("prioD", width=60, anchor="center")
        self.process_tree.pack(fill="both", expand=True)

        self.process_update()

    def resources_update(self):
        self.gerenciador.atualizaDados()
        
        self.meters["cpu"].configure(amounttotal=self.gerenciador._cpuSistema, amountused=self.gerenciador._cpuUso)
        self.meters["mem"].configure(amounttotal=self.gerenciador._memTotal, amountused=self.gerenciador._memUso)
        self.meters["memV"].configure(amounttotal=self.gerenciador._memVirtualTotal, amountused=self.gerenciador._memVirtualUso)

        
        self.cpu_chart_frame.update_chart(self.gerenciador._cpuUso, self.gerenciador._cpuSistema)
        self.mem_chart_frame.update_chart(self.gerenciador._memUso, self.gerenciador._memTotal)
        self.memV_chart_frame.update_chart(self.gerenciador._memVirtualUso, self.gerenciador._memVirtualTotal)

        self.root.update()
        self.root.after(UPDATE_TIME_MS, self.resources_update)

    def resources_draw(self):
        process_button = ttk.Button(self.root, text="View Processes", command=self.redraw_processes)
        process_button.pack(pady=10)

        self.frames["cpu"].pack(fill="x", padx=10)
        self.meters["cpu"].pack(side="left", padx=10)

        self.frames["mem"].pack(fill="x", padx=10)
        self.meters["mem"].pack(side="left", padx=10)
        
        self.frames["memV"].pack(fill="x", padx=10)
        self.meters["memV"].pack(side="left", padx=10)

        self.cpu_chart_frame = AreaChartFrame(self.frames["cpu"], "CPU Usage (%)", '#6e4ac9')
        self.mem_chart_frame = AreaChartFrame(self.frames["mem"], "Memory Usage (MB)", '#4fb3ff')
        self.memV_chart_frame = AreaChartFrame(self.frames["memV"], "Virtual Memory Usage (MB)", '#767676')

        self.resources_update()

    def update_chart(self, chart_frame, value, max_value):
        chart_frame.update_chart(value, max_value)

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

if __name__ == "__main__":
    app = Interface()
    app.run()
