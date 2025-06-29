from ctypes import CDLL, byref, c_char_p, Structure, c_ulong, c_void_p, POINTER
import ctypes
import threading

libc = CDLL("libc.so.6")

class Statvfs(Structure):
    _fields_ = [
        ('f_bsize', c_ulong),
        ('f_frsize', c_ulong),
        ('f_blocks', c_ulong),
        ('f_bfree', c_ulong),
        ('f_bavail', c_ulong),
        ('f_files', c_ulong),
        ('f_ffree', c_ulong),
        ('f_favail', c_ulong),
        ('f_fsid', c_ulong),
        ('f_flag', c_ulong),
        ('f_namemax', c_ulong),
    ]

libc.statvfs.argtypes = [c_char_p, ctypes.POINTER(Statvfs)]
libc.statvfs.restype = ctypes.c_int

def get_statvfs(path):
    if not isinstance(path, str) or not path:
        return None

    path_bytes = path.encode('utf-8', errors='ignore')

    stat = Statvfs()
    result = libc.statvfs(path_bytes, byref(stat))

    if result != 0:
        print(f"Erro ao chamar statvfs para {path}")
        return None

    return {
        'frsize': stat.f_frsize,
        'blocks': stat.f_blocks,
        'bfree': stat.f_bfree,
        'bavail': stat.f_bavail
    }
    
def get_fsize_bytes(filepath):
    try:
        with open(filepath, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            return size
    except Exception as e:
        return None

DTYPES = {
    0: "UNKNOWN", 1: "FIFO", 2: "CHR", 4: "DIR", 6: "BLK", 8: "REG", 10: "LNK", 12: "SOCK"
}

class FileInfo():
    def __init__(self):
        self.particoes = None
        self.folder_content = None
        self._curr_folder = "/"
        self._parent = None
        self._dictlock = threading.Lock()
        self.mostrar_info_particoes()
        self.list_dir()


    def mostrar_info_particoes(self):
        with self._dictlock:
            self.particoes = []
            seen_mounts = set()
            
            try:
                with open('/proc/mounts', 'r') as f:
                    mounts = f.readlines()
            except FileNotFoundError:
                print("Não foi possível acessar /proc/mounts.")
                return

            for linha in mounts:
                partes = linha.split()
                if len(partes) < 3:
                    continue

                dispositivo = partes[0]
                mount_point = partes[1]

                if mount_point in seen_mounts:
                    continue
                seen_mounts.add(mount_point)

                try:
                    stat = get_statvfs(mount_point)
                    total = (stat['blocks'] * stat['frsize']) // 1024
                    livre = (stat['bfree'] * stat['frsize']) // 1024
                    disponivel = (stat['bavail'] * stat['frsize']) // 1024
                    usado = total - livre
                    uso_perc = int((usado / total) * 100) if total > 0 else 0

                    particao_dict = {
                        "disp": dispositivo,
                        "mountp": mount_point,
                        "total": total,
                        "usado": usado,
                        "dispo": disponivel,
                        "uso_pct": uso_perc
                    }
                    self.particoes.append(particao_dict)

                except Exception as e:
                    print(f"[erro] mount point {mount_point}: {e}")
                    continue

    def open_dir(self, path):
        fd = libc.open(bytes(path, "utf-8"), 0)  # 0 pra readonly
        if fd < 0:
            err = ctypes.get_errno()
            raise OSError(err, f"Erro ao abrir diretório: {path}")
        return fd

    def list_dir(self, path=None):
        if path == None:
            path=self._curr_folder
        
        self.folder_content = {}
        fd = self.open_dir(path)
        buffer_size = 4096
        buf = ctypes.create_string_buffer(buffer_size)
        
        if path != "/":
            self._parent = self._curr_folder
            self._curr_folder = path
            
            
            self.folder_content[".."] = {
                "fname": "..",
                "size": "",
                "inode": "",
                "parent": "",
                "tipo": "DIR",
                "fullpath": self.go_up_one_folder(path)
            }
        else:
            self._parent = None

        while True:
            nread = libc.syscall(217, fd, buf, buffer_size) # syscall pro getdents64 pra listar entrada de diretorios
            if nread == -1:
                err = ctypes.get_errno()
                raise OSError(err, "Erro em getdents64")
            if nread == 0:
                break

            bpos = 0
            while bpos < nread:
                
                d_ino = int.from_bytes(buf[bpos : bpos+8], "little")
                d_off = int.from_bytes(buf[bpos+8 : bpos+16], "little")
                d_reclen = int.from_bytes(buf[bpos+16 : bpos+18], "little")
                d_type = buf[bpos + 18]
                
                d_name_start = bpos + 19#  Nome no offset 19
                d_name_end = bpos + d_reclen
                d_name = buf[d_name_start:d_name_end].split(b'\x00', 1)[0].decode("utf-8", errors="ignore")

                tipo = DTYPES.get(int.from_bytes(d_type, 'little'), "UNKNOWN")
                
                if d_name not in ['.', '..']:
                    fullpath = f"{path}/{d_name}".replace("//", "/")
                    f_info = {
                        "fname": d_name,
                        "size": get_fsize_bytes(fullpath),
                        "inode": d_ino,
                        "parent": path,
                        "tipo": tipo,
                        "fullpath": fullpath
                    }
                    
                    self.folder_content[fullpath] = f_info
                
                bpos += d_reclen

        libc.close(fd)

    def go_up_one_folder(self, path):
        if not path or path == "/":
            return "/"
        path = path.rstrip('/')
        parts = path.split('/')
        if len(parts) > 1:
            parts.pop()
            new_path = '/'.join(parts)
            return new_path if new_path else "/"
        return "/"
    