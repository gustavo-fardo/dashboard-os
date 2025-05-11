from Tarefa import Tarefa  # Ensure Tarefa is a class in the Tarefa module

class Thread(Tarefa):  # Ensure Tarefa is the correct base class
    def __init__(self, pid, tid):
        super().__init__(tid, f"/proc/{pid}/task")
        self._pid = pid
        super().atualizaDados()