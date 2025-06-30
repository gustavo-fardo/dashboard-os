from Tarefa import Tarefa
from Thread import Thread
import os
import math
import re
import ctypes
import ctypes.util
import stat
from collections import defaultdict
user_uid = os.getuid()

librt_path = ctypes.util.find_library("rt")
librt = ctypes.CDLL(librt_path, mode=ctypes.RTLD_GLOBAL)

sem_open = librt.sem_open
sem_open.argtypes = [ctypes.c_char_p, ctypes.c_int]
sem_open.restype = ctypes.c_void_p

sem_getvalue = librt.sem_getvalue
sem_getvalue.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
sem_getvalue.restype = ctypes.c_int

sem_close = librt.sem_close
sem_close.argtypes = [ctypes.c_void_p]
sem_close.restype = ctypes.c_int

class Processo(Tarefa):
    def __init__(self, pid):
        super().__init__(pid)
        self._id = pid
        self._threads = {}
        self._numThreads = 0
        self._memVirtualUso = 0
        self._memSegments = defaultdict(lambda: {'pages': 0, 'size_kb': 0})
        self.dictIO = defaultdict(lambda: {'file_descriptors': [], 'sockets': [], 'posix_semaphores': [], 'io_devices': [], 'disk_io': {}})
        self.atualizaDadosProcesso()

    def atualizaDadosProcesso(self):
        super().atualizaDados()
        self._atualizaMemProcesso()
        self._atualizaThreadDict()
        self._atualizaMemThreads()
        self._atualizaDictIO()

    '''
    Projeto A - Implementação da Funcionalidade Inicial do Dashboard
    '''

    def _atualizaThreadDict(self):
        try:
            tid_list = [name for name in os.listdir(f"/proc/{self._id}/task") if name.isdigit()]
        except Exception as e:
            print(f"Error reading task directory: {e}")
            tid_list = []
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
        # Acessa /proc/PID/statm e captura número de paginas de memoria virtual e RSS
        # Acessa /proc/PID/smaps para capturar o numero de paginas por segmento a partir 
        # de teste de permissao
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
        # Acessa /proc/PID/task/TID/maps para contar o tamanho do stack individual da thread
        # e soma com a memoria compartilhada do processo com as outras threads
        total_process_kb = self._memUso

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
            try:
                self._threads[int(tid)].atualizaMem(thread_data[tid]['total_kb'])
            except:
                print(f"Warning: Thread {tid} in process {self._id} not found")
    
    def getThreadDict(self):
        return self._threads

    def getNumThreads(self):
        return self._numThreads
    
    def getMemVirt(self):
        return self._memVirtualUso/1024  # Convertendo para MB
    
    def getMemSegments(self):
        return self._memSegments
    
    '''
    Projeto B - Mostrar dados do uso dos disposistivos de E/S pelos processos
    '''

    def _atualizaDescArquivos(self):
        fd_dir = f"/proc/{self._id}/fd"
        descritoresArquivos = []
        try:
            for fd_name in os.listdir(fd_dir):
                fd_path = os.path.join(fd_dir, fd_name)
                try:
                    target = os.readlink(fd_path)
                    fd_type = "unknown"
                    full_path = os.path.realpath(fd_path)

                    if target.startswith("socket:"):
                        fd_type = "socket"
                    elif target.startswith("pipe:"):
                        fd_type = "pipe"
                    elif target.startswith("anon_inode:"):
                        fd_type = "anon_inode"
                    else:
                        fd_type = "arquivo"
                
                    try:
                        st = os.stat(fd_path)
                        perms = stat.filemode(st.st_mode)
                        inode_type = stat.S_IFMT(st.st_mode)
                        mode_type = {
                            stat.S_IFREG: "regular",
                            stat.S_IFDIR: "directory",
                            stat.S_IFCHR: "char_device",
                            stat.S_IFBLK: "block_device",
                            stat.S_IFIFO: "fifo",
                            stat.S_IFSOCK: "socket",
                            stat.S_IFLNK: "symlink"
                        }.get(inode_type, "unknown")
                    except Exception:
                        perms = "?"
                        mode_type = "unknown"

                    descritoresArquivos.append({
                        "fd": fd_name,
                        "type": fd_type,
                        "target": target,
                        "real_path": full_path,
                        "permissions": perms,
                        "inode_type": mode_type
                    })
                except FileNotFoundError:
                # O descritor foi fechado entre os dois comandos
                    continue
                except PermissionError:
                    print(f"FD {fd_name}: [acesso negado]")
                except OSError as e:
                    print(f"FD {fd_name}: erro ao ler ({e})")
        except FileNotFoundError:
            print(f"Processo {self._id} não encontrado.")
        return descritoresArquivos
        
    def _atualizaSockets(self, fd_info):
        socket_inodes = []
        for fd in fd_info:
            if fd['type'] == 'socket':
                inode = fd['target'].split('[')[-1].rstrip(']')
                socket_inodes.append({
                    "fd": fd["fd"],
                    "inode": inode
                })

        def parse_proc_net(proto):
            path = f"/proc/net/{proto}"
            connections = {}
            try:
                with open(path, 'r') as f:
                    lines = f.readlines()[1:]  # skip header
                    for line in lines:
                        parts = line.split()
                        if proto == "unix":
                            inode = parts[6]
                            path = parts[-1] if len(parts) > 7 else "(anonymous)"
                            connections[inode] = {
                                "proto": "unix",
                                "path": path,
                                "local": "(none)",
                                "remote": "(none)",
                                "state": "(none)"
                            }
                        else:
                            local_ip_hex, local_port_hex = parts[1].split(':')
                            remote_ip_hex, remote_port_hex = parts[2].split(':')
                            inode = parts[9]
                            state = parts[3]

                            def hex_ip(ip_hex):
                                ip_parts = [str(int(ip_hex[i:i+2], 16)) for i in range(6, -2, -2)]
                                return ".".join(ip_parts)

                            local_ip = hex_ip(local_ip_hex)
                            remote_ip = hex_ip(remote_ip_hex)
                            local_port = int(local_port_hex, 16)
                            remote_port = int(remote_port_hex, 16)

                            connections[inode] = {
                                "proto": proto,
                                "path": "(none)",
                                "local": f"{local_ip}:{local_port}",
                                "remote": f"{remote_ip}:{remote_port}",
                                "state": state
                            }
            except FileNotFoundError:
                pass
            return connections

        all_sockets = {}
        for proto in ["tcp", "udp", "unix"]:
            all_sockets.update(parse_proc_net(proto))

        socket_details = []
        for s in socket_inodes:
            inode = s["inode"]
            detail = all_sockets.get(inode)
            if detail:
                socket_details.append({
                    "fd": s["fd"],
                    "inode": inode,
                    "info": detail
                })
        return socket_details

    def _atualizaSemaforos(self):
        fd_dir = f"/proc/{self._id}/fd"
        semaphores = []

        if not os.path.exists(fd_dir):
            return []

        for fd_name in os.listdir(fd_dir):
            fd_path = os.path.join(fd_dir, fd_name)
            try:
                target = os.readlink(fd_path)
                if target.startswith("/dev/shm/sem."):
                    sem_name = target.split("/")[-1]
                    sem_path = target
                    
                    try:
                        stat_info = os.stat(fd_path)
                        owner_uid = stat_info.st_uid
                        permissions = oct(stat_info.st_mode)[-3:]

                        # Tenta abrir o semáforo e obter o valor
                        name = "/" + sem_name[4:]  # tira 'sem.'
                        sem = sem_open(name.encode(), 0)
                        if not sem:
                            raise RuntimeError("sem_open falhou")

                        sval = ctypes.c_int()
                        res = sem_getvalue(sem, ctypes.byref(sval))
                        sem_close(sem)
                        state = sval.value if res == 0 else "erro"

                    except Exception as e:
                        state = str(e)

                    semaphores.append({
                        "fd": fd_name,
                        "name": sem_name,
                        "path": sem_path,
                        "owner_uid": owner_uid,
                        "state": state,
                        "permissions": permissions
                    })

            except (FileNotFoundError, PermissionError, OSError):
                continue

        return semaphores

    def _atualizaDispIO(self, fd_info):
        io_devices = []
        for fd in fd_info:
            target = fd.get("target", "")
            # Considera como dispositivo se o target começa com /dev/
            if target.startswith("/dev/"):
                io_devices.append({
                    "fd": fd["fd"],
                    "device_path": target
                })
        return io_devices

    def _atualizaIOBytes(self):
        io_path = f"/proc/{self._id}/io"
        io_stats = {}
        try:
            with open(io_path, 'r') as f:
                for line in f:
                    key, val = line.strip().split(":")
                    io_stats[key.strip()] = int(val.strip())
        except FileNotFoundError:
            io_stats["error"] = f"Processo {self._id} não encontrado"
        except Exception as e:
            io_stats["error"] = str(e)
        return io_stats

    def _atualizaDictIO(self):
        fd_info = self._atualizaDescArquivos()
        socket_info = self._atualizaSockets(fd_info)
        semaphores = self._atualizaSemaforos()
        io_devices = self._atualizaDispIO(fd_info)
        io_stats = self._atualizaIOBytes()

        info = {
            "pid": self._id,
            "file_descriptors": fd_info,
            "sockets": socket_info,
            "posix_semaphores": semaphores,
            "io_devices": io_devices,
            "disk_io": io_stats
        }
        return info
    
    def getDictIO(self):
        if not self.dictIO:
            self.dictIO = self._atualizaDictIO()
        return self.dictIO
    
    def getReadIO(self):
        if not self.dictIO:
            self.dictIO = self._atualizaDictIO()
        return round(self.dictIO.get("disk_io", {}).get("read_bytes", 0) / (1024 * 1024), 3)
    
    def getWriteIO(self):
        if not self.dictIO:
            self.dictIO = self._atualizaDictIO()
        return round(self.dictIO.get("disk_io", {}).get("write_bytes", 0) / (1024 * 1024), 3)