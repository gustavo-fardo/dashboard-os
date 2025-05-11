from Processo import Processo
import os
import ctypes
import ctypes.util
import time
# Load the C standard library
libc = ctypes.CDLL(ctypes.util.find_library("c"))

# Como a struct sysinfo usada em C para obter informacoes de memoria pela syscall sysinfo
class Sysinfo(ctypes.Structure):
    _fields_ = [
        ("uptime", ctypes.c_long),
        ("loads", ctypes.c_ulong * 3),
        ("totalram", ctypes.c_ulong),
        ("freeram", ctypes.c_ulong),
        ("sharedram", ctypes.c_ulong),
        ("bufferram", ctypes.c_ulong),
        ("totalswap", ctypes.c_ulong),
        ("freeswap", ctypes.c_ulong),
        ("procs", ctypes.c_ushort),
        ("pad", ctypes.c_ushort),
        ("totalhigh", ctypes.c_ulong),
        ("freehigh", ctypes.c_ulong),
        ("mem_unit", ctypes.c_uint),
        ("_f", ctypes.c_char * (20 - 2 * ctypes.sizeof(ctypes.c_long) - ctypes.sizeof(ctypes.c_int)))
    ]

class GerenciadorDados():
    def __init__(self):
        self._processos = {}
        self._memTotal = None
        self._memLivre = None
        self._memUso = None
        self._memVirtualTotal = None
        self._memVirtualLivre = None
        self._memVirtualUso = None
        self._cpuUso = None
        self._cpuOcioso = None
        self._cpuSistema = None
        self._cpuUsuario = None
        self._cpuNice = None
        self._cpuWait = None
        self._cpuIrq = None
        self._cpuSoftIrq = None
        self._numProcessos = None
        self._numThreads = None
        self.atualizaDados(True)

    def atualizaDados(self, total=False):
        self._atualizaProcDict()
        self._atualizaMemInfo(total=total)
        self._atualizaCPUInfo()

    def _atualizaProcDict(self):
        pid_list = [name for name in os.listdir(f"/proc/") if name.isdigit()]
        pid_list = [1775]
        print (f"PID List: {pid_list}")
        # Deletar processos que nao estao mais ativos
        for existing_pid in list(self._processos.keys()):
            if existing_pid not in map(int, pid_list):
                del self._processos[existing_pid]
        # Atualizar processos ativos
        for pid in pid_list:
            if int(pid) not in self._processos:
                self._processos[int(pid)] = Processo(pid)
            else:
                self._processos[int(pid)].atualizaDadosProcesso()
        self._numProcessos = len(self._processos)

    def _atualizaMemInfo(self, total=False):
        # REF: https://man7.org/linux/man-pages/man2/sysinfo.2.html
        # Configuracao de chamada da funcao sysinfo
        libc.sysinfo.argtypes = [ctypes.POINTER(Sysinfo)]
        libc.sysinfo.restype = ctypes.c_int
        ctypes.set_errno(0)  # limpa errno antes da chamada

        # SysCalls getpriority
        info = Sysinfo()
        if libc.sysinfo(ctypes.byref(info)) == -1:
            err = ctypes.get_errno()
            if err != 0:
                raise OSError(err, os.strerror(err))
        else:
            # Atualiza os dados de memória
            mem_unit_mb = info.mem_unit / (1024 ** 2)
            if total:
                self._memTotal = info.totalram * mem_unit_mb
                self._memVirtualTotal = info.totalswap * mem_unit_mb
            self._memLivre = info.freeram * mem_unit_mb
            self._memUso = (info.totalram - info.freeram) * mem_unit_mb
            self._memVirtualLivre = info.freeswap * mem_unit_mb
            self._memVirtualUso = (info.totalswap - info.freeswap) * mem_unit_mb

    def _atualizaCPUInfo(self):
        # REF: https://www.idnt.net/en-GB/kb/941772
        def ler_cpu_tempos():
            with open('/proc/stat', 'r') as f:
                for line in f:
                    if line.startswith('cpu '):  # Note the space to exclude per-core lines like 'cpu0'
                        parts = line.strip().split()
                        # Extract the first 8 fields: user, nice, system, idle, iowait, irq, softirq
                        values = list(map(int, parts[1:9]))
                        keys = ['user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'steal']
                        return dict(zip(keys, values))
                
        t1 = ler_cpu_tempos()
        time.sleep(1)                           # Sleep for 1 second
        t2 = ler_cpu_tempos()

        deltas = {}
        total_delta = 0
        for key in t1:
            deltas[key] = t2[key] - t1[key]     # Tempo de CPU por tipo de uso em 1s
            total_delta += deltas[key]          # Total de tempo de CPU usado em 1s

        percentages = {}
        for key in deltas:
            percentages[key] = (deltas[key] / total_delta) * 100 if total_delta else 0.0
        cpuTotal = sum(percentages.values())  # Total de tempo de CPU usado em 1s
        
        self._cpuSistema = percentages['system']
        self._cpuUsuario = percentages['user']
        self._cpuNice = percentages['nice']
        self._cpuWait = percentages['iowait']
        self._cpuIrq = percentages['irq']
        self._cpuSoftIrq = percentages['softirq']
        self._cpuOcioso = (percentages['idle'] + self._cpuWait) / cpuTotal * 100
        self._cpuUso = (cpuTotal - self._cpuOcioso) / cpuTotal * 100

    def getMemTotal(self):
        return self._memTotal
    
    def getMemLivre(self):
        return self._memLivre
    
    def getMemUso(self):
        return self._memUso
    
    def getMemVirtualTotal(self):
        return self._memVirtualTotal
    
    def getMemVirtualLivre(self):
        return self._memVirtualLivre
    
    def getMemVirtualUso(self):
        return self._memVirtualUso
    
    def getCpuUso(self):
        return self._cpuUso
    
    def getCpuOcioso(self):
        return self._cpuOcioso
    
    def getCpuSistema(self):
        return self._cpuSistema
    
    def getCpuUsuario(self):
        return self._cpuUsuario
    
    def getCpuNice(self):
        return self._cpuNice
    
    def getCpuWait(self):
        return self._cpuWait
    
    def getCpuIrq(self):
        return self._cpuIrq
    
    def getCpuSoftIrq(self):
        return self._cpuSoftIrq
    
    def getProcDict(self):
        return self._processos
    
    def getNumProcessos(self):
        return self._numProcessos
    
    def getNumThreads(self):
        num_threads = 0
        for processo in self._processos.values():
            num_threads += processo.getNumThreads()
        return num_threads
    
if __name__ == "__main__":
    while True:
        gerenciador = GerenciadorDados()
        print("=== Informações de Memória ===")
        print(f"CPU Sistema: {gerenciador._cpuSistema} %")
        print(f"CPU Usuário: {gerenciador._cpuUsuario} %")
        print(f"CPU Nice: {gerenciador._cpuNice} %")
        print(f"CPU IOWait: {gerenciador._cpuWait} %")
        print(f"CPU IRQ: {gerenciador._cpuIrq} %")
        print(f"CPU SoftIRQ: {gerenciador._cpuSoftIrq} %")
        print(f"CPU Ocioso: {gerenciador._cpuOcioso} %")
        print(f"CPU Uso: {gerenciador._cpuUso} %")
        print(f"Memória Total: {gerenciador._memTotal} MB")
        print(f"Memória Livre: {gerenciador._memLivre} MB")
        print(f"Memória em Uso: {gerenciador._memUso} MB")
        print(f"Memória Virtual Total: {gerenciador._memVirtualTotal} MB")
        print(f"Memória Virtual Livre: {gerenciador._memVirtualLivre} MB")
        print(f"Memória Virtual em Uso: {gerenciador._memVirtualUso} MB")
        for pid, processo in gerenciador.getProcDict().items():
            processo = Processo(pid)
            print("=== Processo:")
            print(f"PID: {processo.getID()}")
            print(f"Nome: {processo.getNome()}")
            print(f"Prioridade Base: {processo.getPrioB()}")
            print(f"Prioridade Dinâmica: {processo.getPrioD()}")
            print(f"Estado: {processo.getEstado()}")
            print(f"Uso de memoria: {processo.getMem()} MB")
            print(f"Uso de CPU: {processo.getCPU()} %")
            print("=== Threads:")
            for tid, thread in processo.getThreadDict().items():
                print(f"Thread ID: {tid}")
                print(f"  Nome: {thread.getNome()}")
                print(f"  Prioridade Base: {thread.getPrioB()}")
                print(f"  Prioridade Dinâmica: {thread.getPrioD()}")
                print(f"  Estado: {thread.getEstado()}")
                print(f"  Uso de memória: {thread.getMem()} MB")
                print(f"  Uso de CPU: {thread.getCPU()} %")
        gerenciador.atualizaDados()
        os.system("clear")


# # Atualiza os dados continuamente em uma thread separada
# self.__att_thread = threading.Thread(target=self.__atualizaDadosContinuamente, daemon=True)
# self.__att_thread.start()
