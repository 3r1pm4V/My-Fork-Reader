import logging
import pyttsx3
import re
from PyQt6.QtCore import QObject, pyqtSignal, QThread, pyqtSlot, QMetaObject, Q_ARG, Qt


class TTSWorker(QObject):
    """
    Worker class to handle pyttsx3 engine in a separate thread.
    """
    sentence_started = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._engine = None
        self._is_running = False
        self._is_paused = False

    def setup(self):
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', self.config.tts.rate)
            self._engine.setProperty('volume', self.config.tts.volume)
            
            # Connect internal events
            self._engine.connect('started-utterance', self._on_start)
            self._engine.connect('finished-utterance', self._on_finish)
            self._engine.connect('error', self._on_error)
        except Exception as e:
            self.error.emit(str(e))

    def _on_start(self, name):
        self.sentence_started.emit(name)

    def _on_finish(self, name, completed):
        pass

    def _on_error(self, name, exception):
        self.error.emit(str(exception))

    @pyqtSlot(str)
    def speak(self, text: str):
        if not self._engine:
            self.setup()
        
        self._is_running = True
        
        # Split text into sentences for better granular control and highlighting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        try:
            for sentence in sentences:
                if not self._is_running:
                    break
                
                clean_sentence = sentence.strip()
                if not clean_sentence:
                    continue
                
                # We use the sentence itself as the 'name' to track it in signals
                self._engine.say(clean_sentence, clean_sentence)
                self._engine.runAndWait()
                
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._is_running = False

    @pyqtSlot()
    def stop(self):
        self._is_running = False
        if self._engine:
            self._engine.stop()

    @pyqtSlot(int)
    def set_rate(self, rate: int):
        if self._engine:
            self._engine.setProperty('rate', rate)

    @pyqtSlot(str)
    def set_voice(self, voice_id: str):
        if self._engine:
            self._engine.setProperty('voice', voice_id)

    def list_voices(self) -> list[dict]:
        if not self._engine:
            self.setup()
        voices = self._engine.getProperty('voices')
        return [{"id": v.id, "name": v.name, "lang": v.languages} for v in voices]


class TTSEngine(QObject):
    """
    Main TTS interface for the application.
    Manages the lifecycle of the TTSWorker in a QThread.
    """
    sentence_started = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.thread = QThread()
        self.worker = TTSWorker(config)
        self.worker.moveToThread(self.thread)
        
        # Connect worker signals to engine signals
        self.worker.sentence_started.connect(self.sentence_started)
        self.worker.finished.connect(self.finished)
        self.worker.error.connect(self.error)
        
        self.thread.start()

    def speak(self, text: str):
        QMetaObject.invokeMethod(self.worker, "speak", Qt.ConnectionType.QueuedConnection, Q_ARG(str, text))

    def stop(self):
        QMetaObject.invokeMethod(self.worker, "stop", Qt.ConnectionType.QueuedConnection)

    def set_rate(self, rate: int):
        QMetaObject.invokeMethod(self.worker, "set_rate", Qt.ConnectionType.QueuedConnection, Q_ARG(int, rate))

    def set_voice(self, voice_id: str):
        QMetaObject.invokeMethod(self.worker, "set_voice", Qt.ConnectionType.QueuedConnection, Q_ARG(str, voice_id))

    def get_voices(self):
        return self.worker.list_voices()

    def __del__(self):
        self.thread.quit()
        self.thread.wait()

__all__ = ["TTSEngine"]
