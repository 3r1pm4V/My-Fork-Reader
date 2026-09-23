import asyncio
import logging
import threading
import functools
from typing import Any, Callable
from PyQt6.QtCore import QThread, pyqtSignal, QObject, QThreadPool

def main_thread_only(func: Callable):
    """Decorator to ensure a function is only called from the main thread."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if threading.current_thread() is not threading.main_thread():
            logging.error(f"Thread violation: {func.__name__} called from {threading.current_thread().name}")
            raise RuntimeError(f"Function {func.__name__} must be called from main thread.")
        return func(*args, **kwargs)
    return wrapper

class TaskRunner(QThread):
    """Standard QThread wrapper for long-running UI tasks."""
    started_task = pyqtSignal(str)
    finished_task = pyqtSignal(str, object)
    failed_task = pyqtSignal(str, str)

    def __init__(self, task_name: str, fn: Callable, *args, **kwargs):
        super().__init__()
        self.task_name = task_name
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        tid = threading.get_native_id()
        logging.info(f"[Thread {tid}] Task '{self.task_name}' started")
        self.started_task.emit(self.task_name)
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.finished_task.emit(self.task_name, result)
            logging.info(f"[Thread {tid}] Task '{self.task_name}' finished")
        except Exception as e:
            error_msg = str(e)
            self.failed_task.emit(self.task_name, error_msg)
            logging.error(f"[Thread {tid}] Task '{self.task_name}' failed: {error_msg}")

class AsyncRunner(QObject):
    """Manages an asyncio event loop in a dedicated background thread for async operations."""
    def __init__(self):
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._start_loop()

    def _start_loop(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="AsyncRunnerThread")
        self._thread.start()

    def _run_loop(self):
        tid = threading.get_native_id()
        logging.info(f"[Thread {tid}] AsyncRunner loop started")
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
        logging.info(f"[Thread {tid}] AsyncRunner loop stopped")

    def submit(self, coro):
        """Submit a coroutine to the background loop."""
        if self._loop and self._loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, self._loop)
        return None

    def stop(self):
        """Gracefully stop the background loop."""
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread:
                self._thread.join(timeout=2)
            self._loop = None

# Global instance
_async_runner_instance: AsyncRunner | None = None

def get_async_runner() -> AsyncRunner:
    global _async_runner_instance
    if _async_runner_instance is None:
        _async_runner_instance = AsyncRunner()
    return _async_runner_instance

def shutdown_concurrency():
    """Stops all background runners and thread pools."""
    global _async_runner_instance
    if _async_runner_instance:
        _async_runner_instance.stop()
        _async_runner_instance = None
    
    QThreadPool.globalInstance().waitForDone(5000)
    logging.info("Concurrency shutdown complete.")

__all__ = [
    "main_thread_only", "TaskRunner", "AsyncRunner", 
    "get_async_runner", "shutdown_concurrency"
]
