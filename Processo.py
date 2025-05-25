from Tarefa import Tarefa
from Thread import Thread
import os
import math
import re
from collections import defaultdict
user_uid = os.getuid()

class Processo(Tarefa):
    def __init__(self, pid):
        super().__init__(pid)
        self._id = pid
        self._threads = {}
        self._numThreads = 0
        self._memVirtualUso = 0
        self._memSegments = defaultdict(lambda: {'pages': 0, 'size_kb': 0})
        self.atualizaDadosProcesso()

    def atualizaDadosProcesso(self):
        super().atualizaDados()
        self._atualizaMemProcesso()
        self._atualizaThreadDict()

    def _atualizaThreadDict(self):
        tid_list = []
        for name in os.listdir(f"/proc/{self._id}/task"):
            if name.isdigit():
                try:
                    with open(f"/proc/{self._id}/task/{name}/status") as f:
                        for line in f:
                            if line.startswith("Uid:"):
                                uid = int(line.split()[1])  # Real UID
                                if uid == user_uid:
                                    tid_list.append(name)
                                break
                except (FileNotFoundError, PermissionError):
                    continue
        # Deletar threads que nao estao mais ativas
        for existing_tid in list(self._threads.keys()):
            if existing_tid not in map(int, tid_list):
                del self._threads[existing_tid]
        # Atualizar threads ativas
        for tid in tid_list:
            if os.path.exists(f"/proc/{self._id}/task/{tid}"):
                if int(tid) not in self._threads:
                    self._threads[int(tid)] = Thread(tid=tid, pid=self._id)
                else:
                    self._threads[int(tid)].atualizaDados()
            elif int(tid) in self._threads:
                del self._threads[int(tid)]
        self._numThreads = len(self._threads)
        self._atualizaMemThreads()

    def _atualizaMemProcesso(self):
        # Dados de memoria do processo (statm do processo, com memoria virtual e RSS)
        try:
            with open(f"/proc/{self._id}/statm") as f:
                process_pages = list(map(int, f.read().split()))
            page_size = os.sysconf(os.sysconf_names['SC_PAGE_SIZE']) // 1024  # KB
            self._memVirtualUso = process_pages[0] * page_size  # Converte paginas virtuais para KB
            self._memUso = process_pages[1] * page_size  # Converte paginas do RSS para KB
        except Exception as e:
            self._memVirtualUso = 0
            self._memUso = 0

        segment_patterns = {
            'text': r'^[0-9a-f].* r-xp.*\.so|\.py|bin/',
            'heap': r'^[0-9a-f].* rw-p.*\[heap\]',
            'stack': r'^[0-9a-f].* rw-p.*\[stack\]',
            'libraries': r'\.so',
            'anonymous': r'rw-s?p.* 00:00 0',
            'file_mapped': r' rw-p.* [0-9a-f]{2}:[0-9a-f]{2} \d+'
        }

        try:
            with open(f"/proc/{self._id}/smaps") as f:
                current_segment = None
                for line in f:
                    # Verifica se há uma nova linha de segmento
                    if line[0].isdigit():
                        current_segment = None
                        for seg_type, pattern in segment_patterns.items():
                            if re.search(pattern, line):
                                current_segment = seg_type
                                break
                    # Acumula o novo segmento
                    elif current_segment:
                        if line.startswith('Size:'):
                            kb = int(line.split()[1])
                            self._memSegments[current_segment]['size_kb'] += kb
                        elif line.startswith('Rss:'):
                            pages = int(line.split()[1])  # Already in KB
                            self._memSegments[current_segment]['pages'] += pages
        except FileNotFoundError:
            pass

    def _atualizaMemThreads(self):
        total_process_kb = self._memVirtualUso

        # Stack por thread
        thread_data = {}
        task_dir = f"/proc/{self._id}/task"
        total_stacks_kb = 0
        
        try:
            for tid in os.listdir(task_dir):
                stack_kb = 0
                try:
                    # [stack] em /maps
                    with open(f"{task_dir}/{tid}/maps") as f:
                        for line in f:
                            if '[stack]' in line:
                                start, end = line.split()[0].split('-')
                                stack_kb = (int(end, 16) - int(start, 16)) // 1024
                                total_stacks_kb += stack_kb
                                break
                except IOError:
                    continue
                
                thread_data[tid] = {'stack_kb': stack_kb}
        except Exception as e:
            pass
            
        # Calcula memoria compartilhada total (total menos as stacks)
        shared_kb = max(0, total_process_kb - total_stacks_kb)
        num_threads = len(thread_data)
        
        # Estima memoria compartilhada por thread
        for tid in thread_data:
            thread_shared = shared_kb / num_threads
            thread_data[tid].update({
                'shared_kb': math.ceil(thread_shared),
                'total_kb': math.ceil(thread_data[tid]['stack_kb'] + thread_shared)
            })
            # Atualiza memoria das threads
            self._threads[int(tid)].atualizaMem(thread_data[tid]['total_kb'])
    
    def getThreadDict(self):
        return self._threads

    def getNumThreads(self):
        return self._numThreads
    
    def getMemVirt(self):
        return self._memVirtualUso
    
    def getMemSegments(self):
        return self._memSegments