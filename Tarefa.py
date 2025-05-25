import ctypes
import os
import pwd
libc = ctypes.CDLL("libc.so.6", use_errno=True)

# /proc folder ref: https://man7.org/linux/man-pages/man5/proc.5.html
PRIO_PROCESS = 0 # <linux/resource.h>

class Tarefa():
    def __init__(self, id, prefixo="/proc"):
        self._id = id
        self._prefixo = prefixo
        self._nome = None
        self._usuario = None
        self._cpuUso = None
        self._memUso = None
        self._estado = None
        self._prioB = None
        self._prioD = None
        self._atualizaNome()
        self._atualizaUsuario()

    def atualizaDados(self):
        self._atualizaPrioB()
        self._atualizaPrioD()
        self._atualizaEstado()
        self._atualizaCPU()

    def _atualizaCPU(self):
        # Metodo usado pelo comando "top" para calcular o uso de CPU
        # https://stackoverflow.com/questions/16726779/how-do-i-get-the-total-cpu-usage-of-an-application-from-proc-pid-stat
        clk_tck = os.sysconf(os.sysconf_names['SC_CLK_TCK'])

        with open(f'/proc/uptime', 'r') as f:
            fields = f.read().split()
            uptime = float(fields[0])

        try:
            with open(f'{self._prefixo}/{self._id}/stat', 'r') as f:
                fields = f.read().split()
                utime = int(fields[13]) # Tempo de CPU em modo de usuario
                stime = int(fields[14]) # Tempo de CPU em modo de sistema
                starttime = int(fields[21]) # Tempo de inicio do processo
        except Exception as e:
            self._cpuUso=0
            return

        total_time = utime + stime
        seconds = uptime - (starttime / clk_tck)
        self._cpuUso = 100 * ((total_time / clk_tck) / seconds)

    def _atualizaNome(self):
        # Nome: campo 1 do /proc/[tid]/comm
        try:
            with open(f"{self._prefixo}/{self._id}/comm", "r") as f:
                self._nome = f.read().strip()
        except FileNotFoundError:
            print(f"A tarefa com ID {self._id} não existe ou o arquivo comm não está disponível.")

    def _atualizaUsuario(self):
        # Usuario: campo 1 do /proc/[tid]/status
        with open(f"/proc/{self._id}/status") as f:
                        for line in f:
                            if line.startswith("Uid:"):
                                self._usuario = pwd.getpwuid(int(line.split()[1])).pw_name  # Real UID

    def _atualizaEstado(self):
        # Estado: campo 2 do /proc/[tid]/stat
        try:
            with open(f"{self._prefixo}/{self._id}/stat", "r") as f:
                data = f.read()
            fields = data.split()
            self._estado = fields[2]
        except Exception as e:
            print(f"Error reading {self._prefixo}/{self._id}/stat: {e}")

    def _atualizaPrioD(self):
        # Prioridade dinâmica (NICE do linux), pela syscall getpriority
        # REF: https://man7.org/linux/man-pages/man2/setpriority.2.html
        # Configuracao de chamada da funcao getpriority
        libc.getpriority.argtypes = [ctypes.c_int, ctypes.c_int]
        libc.getpriority.restype = ctypes.c_int
        ctypes.set_errno(0)  # limpa errno antes da chamada

        # SysCalls getpriority
        prio = libc.getpriority(PRIO_PROCESS, int(self._id))
        if prio == -1:
            err = ctypes.get_errno()
            if err != 0:
                self._prioD = 0
                #raise OSError(err, os.strerror(err))
        else:
            self._prioD = prio

    def _atualizaPrioB(self):
        # Prioridade Base: campo 17 do /proc/[tid]/stat
        try:
            with open(f'{self._prefixo}/{self._id}/stat', 'r') as f:
                fields = f.read().split()
                self._prioB = int(fields[17]) # Prioridade estática do processo
        except Exception as e:
            self._prioB = 0
    
    def atualizaMem(self, mem):
        self._memUso = mem

    def getID(self):
        return self._id
    
    def getNome(self):
        return self._nome
    
    def getUsuario(self):
        return self._usuario
    
    def getCPU(self):
        return round(self._cpuUso, 2)
    
    def getMem(self):    
        return self._memUso
    
    def getEstado(self):    
        return self._estado
    
    def getPrioB(self):
        return self._prioB
    
    def getPrioD(self):
        return self._prioD