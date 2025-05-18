from Tarefa import Tarefa

class Thread(Tarefa): 
    def __init__(self, pid, tid):
        super().__init__(tid, f"/proc/{pid}/task")
        self._pid = pid
        super().atualizaDados()