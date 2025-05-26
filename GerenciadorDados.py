from Processo import Processo
import os
import time
import sys
import threading
user_uid = os.getuid()

class GerenciadorDados():
    def __init__(self):
        self._processos = {}
        self._memTotal = None
        self._memLivre = None
        self._memUso = None
        self._memBuffer = None
        self._memCache = None
        self._memVirtualTotal = None
        self._memVirtualLivre = None
        self._memVirtualUso = None
        self._memVirtualKernelUso = None
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
        self._dictlock = threading.Lock()
        self.atualizaDados(True)
        
    def atualizaDados(self, total=False):
        with self._dictlock:
            self._atualizaProcDict()
        self._atualizaMemInfo(total=total)
        self._atualizaCPUInfo()

    def _atualizaProcDict(self):
        try:
            pid_list = [name for name in os.listdir(f"/proc/") if name.isdigit()]
        except Exception as e:
            print(f"Error reading task directory: {e}")
            pid_list = []
        # Deletar processos que nao estao mais ativos
        for existing_pid in list(self._processos.keys()):
            if existing_pid not in map(int, pid_list):
                del self._processos[existing_pid]
        # Atualizar processos ativos
        for pid in pid_list:
            if os.path.exists(f"/proc/{pid}"):
                if int(pid) not in self._processos:
                    self._processos[int(pid)] = Processo(pid)
                else:
                    self._processos[int(pid)].atualizaDadosProcesso()
            elif int(pid) in self._processos:
                del self._processos[int(pid)]
        self._numProcessos = len(self._processos)

    def _atualizaMemInfo(self, total=False):
        # Utiliza informacoes do /proc/meminfo
        # Memoria Fisica: campos MemTotal, MemFree, Buffers, Cached e SReclaimable
        # Memoria Virtual: campos CommitLimit, Committed_AS e VmallocUsed
        meminfo = {}
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    key = line.split(':')[0]
                    val = line.split(':')[1].strip().split()[0]
                    meminfo[key] = int(val)  # Values are in KB
        except FileNotFoundError:
            return {"error": "Could not read /proc/meminfo"}

        # Dados gerais de memória em MB
        self._memTotal = meminfo['MemTotal'] / 1024
        self._memLivre = meminfo['MemFree'] / 1024
        self._memBuffer = meminfo.get('Buffers', 0) / 1024
        self._memCache = meminfo.get('Cached', 0) / 1024
        sreclaimable = meminfo.get('SReclaimable', 0) / 1024  # Kernel ≥2.6.19
        self._memUso = self._memTotal - self._memLivre - self._memBuffer - self._memCache - sreclaimable
        
        # Calculo de memoria virtual
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {line.split(':')[0]: line.split(':')[1].strip() 
                        for line in f.readlines()}
            
                self._memVirtualTotal = int(meminfo.get('CommitLimit', '0 kB').split()[0]) / 1024
                self._memVirtualUso = int(meminfo.get('Committed_AS', '0 kB').split()[0]) / 1024
                self._memVirtualKernelUso = int(meminfo.get('VmallocUsed', '0 kB').split()[0]) / 1024
        except Exception as e:
            self._memVirtualTotal = self._memVirtualUso = self._memVirtualKernelUso = 0
            print(f"Warning: Could not read /proc/meminfo: {e}", file=sys.stderr)
        self._memVirtualLivre = self._memVirtualTotal - self._memVirtualUso

    def _atualizaCPUInfo(self):
        # Captura a variacao do uso de CPU em 1s acessando /proc/stat 
        # pelos campos user, nice, system, idle, iowait, irq, softirq
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
