import ctypes
from ctypes import wintypes, c_long, c_longlong
from threading import Event

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_INPUT = 0x00FF
RIM_TYPEMOUSE = 0
RID_INPUT = 0x10000003
RIDEV_INPUTSINK = 0x00000100

if ctypes.sizeof(ctypes.c_void_p) == 8:
    LRESULT = c_longlong
else:
    LRESULT = c_long
HCURSOR = wintypes.HANDLE

class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]
class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]
class RAWMOUSE(ctypes.Structure):
    _fields_ = [
        ("usFlags", wintypes.USHORT),
        ("usButtonFlags", wintypes.USHORT),
        ("usButtonData", wintypes.USHORT),
        ("ulRawButtons", wintypes.ULONG),
        ("lLastX", wintypes.LONG),
        ("lLastY", wintypes.LONG),
        ("ulExtraInformation", wintypes.ULONG),
    ]
class RAWINPUT(ctypes.Structure):
    class _DATA(ctypes.Union):
        _fields_ = [("mouse", RAWMOUSE)]

    _fields_ = [
        ("header", RAWINPUTHEADER),
        ("data", _DATA),
    ]

WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM
)
@WNDPROC
def wnd_proc(hwnd, msg, wparam, lparam):
    if msg == WM_INPUT:
        handle_raw_input(lparam)
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]

user32.DefWindowProcW.argtypes = (
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
user32.DefWindowProcW.restype = LRESULT

user32.RegisterClassW.argtypes = (ctypes.POINTER(WNDCLASS),)
user32.RegisterClassW.restype = wintypes.ATOM

user32.CreateWindowExW.argtypes = (
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    ctypes.c_void_p,
)
user32.CreateWindowExW.restype = wintypes.HWND

user32.RegisterRawInputDevices.argtypes = (
    ctypes.POINTER(RAWINPUTDEVICE),
    wintypes.UINT,
    wintypes.UINT,
)
user32.RegisterRawInputDevices.restype = wintypes.BOOL

user32.GetRawInputData.argtypes = (
    wintypes.LPARAM,
    wintypes.UINT,
    ctypes.c_void_p,
    ctypes.POINTER(wintypes.UINT),
    wintypes.UINT,
)
user32.GetRawInputData.restype = wintypes.UINT

user32.GetMessageW.argtypes = (
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
)
user32.GetMessageW.restype = wintypes.BOOL

user32.DispatchMessageW.argtypes = (ctypes.POINTER(wintypes.MSG),)
user32.DispatchMessageW.restype = LRESULT

user32.DestroyWindow.argtypes = (wintypes.HWND,)
user32.DestroyWindow.restype = wintypes.BOOL

user32.UnregisterClassW.argtypes = (wintypes.LPCWSTR, wintypes.HINSTANCE)
user32.UnregisterClassW.restype = wintypes.BOOL

kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

listening = Event()
listener_buffer = []

def setup_mouse_listener():
    wc = WNDCLASS()
    wc.lpfnWndProc = wnd_proc
    wc.lpszClassName = "RawInputWindow"
    wc.hInstance = kernel32.GetModuleHandleW(None)

    user32.RegisterClassW(ctypes.byref(wc))

    hwnd = user32.CreateWindowExW(
        0,
        wc.lpszClassName,
        "hidden",
        0,
        0, 0, 0, 0,
        None, None, wc.hInstance, None
    )

    rid = RAWINPUTDEVICE()
    rid.usUsagePage = 0x01      # HID
    rid.usUsage = 0x02          # Mouse
    rid.dwFlags = RIDEV_INPUTSINK
    rid.hwndTarget = hwnd

    if not user32.RegisterRawInputDevices(
        ctypes.byref(rid),
        1,
        ctypes.sizeof(rid)
    ):
        raise ctypes.WinError(ctypes.get_last_error())


    msg = wintypes.MSG()

    while True:
        listening.wait()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if not listening.is_set():
                break
            user32.DispatchMessageW(ctypes.byref(msg))
            

def handle_raw_input(lparam):
    global listener_buffer
    size = wintypes.UINT(0)

    user32.GetRawInputData(
        lparam,
        RID_INPUT,
        None,
        ctypes.byref(size),
        ctypes.sizeof(RAWINPUTHEADER),
    )

    buffer = ctypes.create_string_buffer(size.value)

    user32.GetRawInputData(
        lparam,
        RID_INPUT,
        buffer,
        ctypes.byref(size),
        ctypes.sizeof(RAWINPUTHEADER),
    )

    raw = ctypes.cast(buffer, ctypes.POINTER(RAWINPUT)).contents

    if raw.header.dwType != RIM_TYPEMOUSE:
        return

    if raw.data.mouse.lLastX != 0 or raw.data.mouse.lLastY != 0:
        listener_buffer.append((raw.data.mouse.lLastX, raw.data.mouse.lLastY))
