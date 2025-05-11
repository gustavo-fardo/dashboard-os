from Processo import Processo
import os

class GerenciadorDados():
    def __init__(self):
        self._processos = {}
        self._atualizaProcDict()

    def _atualizaProcDict(self):
        pid_list = [name for name in os.listdir(f"/proc/") if name.isdigit()]
        print (f"PID List: {pid_list}")
        self._processos = {int(pid): Processo(pid) for pid in pid_list}
        self._numProcessos = len(self._processos)

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
    gerenciador = GerenciadorDados()
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


# # Atualiza os dados continuamente em uma thread separada
# self.__att_thread = threading.Thread(target=self.__atualizaDadosContinuamente, daemon=True)
# self.__att_thread.start()
