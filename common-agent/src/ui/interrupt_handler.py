"""
Interrupt Handler

Handles ESC key interrupts and task cancellation.
"""

import asyncio
import threading
from typing import Callable, Optional
import sys

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False


class InterruptHandler:
    """Handles user interrupts during task execution"""
    
    def __init__(self, interrupt_callback: Optional[Callable] = None):
        self.interrupt_callback = interrupt_callback
        self.interrupt_key = "esc"
        self.listening = False
        self.thread: Optional[threading.Thread] = None
    
    def start_listening(self):
        """Start listening for interrupt key"""
        if not HAS_KEYBOARD:
            print("Warning: keyboard library not available. ESC interrupt not supported.")
            return
        
        if self.listening:
            return
        
        self.listening = True
        self.thread = threading.Thread(target=self._keyboard_listener, daemon=True)
        self.thread.start()
    
    def stop_listening(self):
        """Stop listening for interrupt key"""
        self.listening = False
        if self.thread and self.thread.is_alive():
            # Note: keyboard listener thread will exit when listening becomes False
            pass
    
    def _keyboard_listener(self):
        """Keyboard listener thread function"""
        if not HAS_KEYBOARD:
            return
        
        try:
            keyboard.add_hotkey(self.interrupt_key, self._on_interrupt)
            
            while self.listening:
                # Keep thread alive while listening
                threading.Event().wait(0.1)
                
        except Exception as e:
            print(f"Error in keyboard listener: {e}")
        finally:
            try:
                keyboard.remove_hotkey(self.interrupt_key)
            except:
                pass
    
    def _on_interrupt(self):
        """Handle interrupt key press"""
        if self.interrupt_callback:
            self.interrupt_callback()
        else:
            print("\n⚠️ Task interrupted by user (ESC)")
    
    def set_interrupt_callback(self, callback: Callable):
        """Set the interrupt callback function"""
        self.interrupt_callback = callback
    
    async def wait_for_interrupt(self, timeout: Optional[float] = None) -> bool:
        """Wait for interrupt with optional timeout"""
        interrupt_event = asyncio.Event()
        
        def interrupt_callback():
            interrupt_event.set()
        
        original_callback = self.interrupt_callback
        self.set_interrupt_callback(interrupt_callback)
        
        try:
            self.start_listening()
            
            if timeout:
                try:
                    await asyncio.wait_for(interrupt_event.wait(), timeout=timeout)
                    return True  # Interrupted
                except asyncio.TimeoutError:
                    return False  # Timed out
            else:
                await interrupt_event.wait()
                return True  # Interrupted
                
        finally:
            self.stop_listening()
            self.set_interrupt_callback(original_callback)


class SimpleInterruptHandler:
    """Simplified interrupt handler using input() for compatibility"""
    
    def __init__(self, interrupt_callback: Optional[Callable] = None):
        self.interrupt_callback = interrupt_callback
        self.listening = False
        self.task: Optional[asyncio.Task] = None
    
    async def start_listening_async(self):
        """Start async listening for interrupt"""
        if self.listening:
            return
        
        self.listening = True
        self.task = asyncio.create_task(self._async_input_listener())
    
    def stop_listening(self):
        """Stop listening for interrupt"""
        self.listening = False
        if self.task and not self.task.done():
            self.task.cancel()
    
    async def _async_input_listener(self):
        """Async input listener"""
        try:
            while self.listening:
                # Check for input without blocking
                await asyncio.sleep(0.1)
                
                # Note: This is a simplified version
                # In a real implementation, you might use aioconsole or similar
                # for non-blocking async input
                
        except asyncio.CancelledError:
            pass
    
    def interrupt_now(self):
        """Manually trigger interrupt"""
        if self.interrupt_callback:
            self.interrupt_callback()


def create_interrupt_handler(interrupt_callback: Optional[Callable] = None) -> InterruptHandler:
    """Create appropriate interrupt handler based on available libraries"""
    if HAS_KEYBOARD:
        return InterruptHandler(interrupt_callback)
    else:
        print("Using simplified interrupt handler (keyboard library not available)")
        return SimpleInterruptHandler(interrupt_callback) 