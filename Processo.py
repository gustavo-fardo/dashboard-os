from Tarefa import Tarefa
from Thread import Thread
import os

class Processo(Tarefa):
    def __init__(self, pid):
        super().__init__(pid)
        print(pid)
        self._threads = {}
        self._numThreads = 0
        self.atualizaDadosProcesso()

    def atualizaDadosProcesso(self):
        super().atualizaDados()
        self._atualizaThreadDict()

    def _atualizaThreadDict(self):
        tid_list = [name for name in os.listdir(f"/proc/{self._id}/task") if name.isdigit()]
        # Deletar threads que nao estao mais ativas
        for existing_tid in list(self._threads.keys()):
            if existing_tid not in map(int, tid_list):
                del self._threads[existing_tid]
        # Atualizar threads ativas
        for tid in tid_list:
            if int(tid) not in self._threads:
                self._threads[int(tid)] = Thread(tid=tid, pid=self._id)
            else:
                self._threads[int(tid)].atualizaDados()
        self._numThreads = len(self._threads)
    
    def getThreadDict(self):
        return self._threads

    def getNumThreads(self):
        return self._numThreads