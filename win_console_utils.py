import ctypes


def init_win_console():
    LF_FACE_SIZE = 32
    STD_OUTPUT_HANDLE = -11

    class COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class ConsoleFontInfoEx(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_ulong),
                    ("nFont", ctypes.c_ulong),
                    ("dwFontSize", COORD),
                    ("FontFamily", ctypes.c_uint),
                    ("FontWeight", ctypes.c_uint),
                    ("FaceName", ctypes.c_wchar * LF_FACE_SIZE)]

    font = ConsoleFontInfoEx()
    font.cbSize = ctypes.sizeof(ConsoleFontInfoEx)
    # font.nFont = 12
    # font.dwFontSize.X = 11
    # font.dwFontSize.Y = 18
    # font.FontFamily = 54
    # font.FontWeight = 400
    font.FaceName = "Lucida Console"

    handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    ctypes.windll.kernel32.SetCurrentConsoleFontEx(
        handle, ctypes.c_long(False), ctypes.pointer(font))
