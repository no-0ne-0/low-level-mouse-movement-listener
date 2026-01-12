import listener
import threading
import keyboard

threading.Thread(target=listener.setup_mouse_listener).start()

def toggle_listening():
    if listener.listening.is_set():
        print("Pausing mouse listener...")
        listener.listening.clear()
        print(listener.listener_buffer)
        listener.listener_buffer.clear() # Don't forget to clear the buffer between uses
    else:
        print("Resuming mouse listener...")
        listener.listening.set()

keyboard.add_hotkey('ctrl+m', toggle_listening)
