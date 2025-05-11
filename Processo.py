from Tarefa import Tarefa
from Thread import Thread

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
        self._threads = {int(tid): Thread(self._id, tid) for tid in tid_list}
        self._numThreads = len(self._threads)
    
    def getThreadDict(self):
        return self._threads

    def getNumThreads(self):
        return self._numThreads