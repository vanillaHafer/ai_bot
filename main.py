import pyaudio
import sys
import json
import os
import pyttsx3
from vosk import Model, KaldiRecognizer
from ollama import chat, list as ollama_list
from ollama import ChatResponse
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QWidget, QHBoxLayout, QVBoxLayout,
    QButtonGroup, QLabel, QFrame, QScrollArea, QMessageBox, QSizePolicy, QComboBox,
    QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QCursor

class SpeechRecognitionThread(QThread):
    result_signal = pyqtSignal(str)

    def __init__(self, model_path, device_index=None):
        super().__init__()
        self.model_path = model_path
        self.device_index = device_index
        self._running = True

    def run(self):
        model = Model(self.model_path)
        recognizer = KaldiRecognizer(model, 16000)
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8192,
            input_device_index=self.device_index
        )
        stream.start_stream()
        understanding = False
        result = None

        while self._running:
            data = stream.read(4096, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                understanding = True
                result = json.loads(recognizer.Result())
            else:
                if understanding:
                    text = result.get("text", "")
                    if text:
                        self.result_signal.emit(text)
                    understanding = False

        stream.stop_stream()
        stream.close()
        p.terminate()

    def stop(self):
        self._running = False

class TextToSpeechThread(QThread):
    tts_done = pyqtSignal()

    def __init__(self, text, language="English"):
        super().__init__()
        self.text = text
        self.language = language

    def run(self):
        try:
            engine = pyttsx3.init()
            if self.language == "Japanese":
                voices = engine.getProperty('voices')
                for voice in voices:
                    if 'japanese' in voice.name.lower() or 'ja' in voice.id.lower():
                        engine.setProperty('voice', voice.id)
                        break
                engine.setProperty('rate', 150)
            elif self.language == "Portuguese":
                voices = engine.getProperty('voices')
                for voice in voices:
                    if 'portuguese' in voice.name.lower() or 'pt' in voice.id.lower():
                        engine.setProperty('voice', voice.id)
                        break
                engine.setProperty('rate', 160)
            else:
                engine.setProperty('rate', 175)
            engine.setProperty('volume', 0.8)
            engine.say(self.text)
            engine.runAndWait()
            engine.stop()
        finally:
            self.tts_done.emit()

class MainWindow(QMainWindow):
    ai_response_signal = pyqtSignal(str, object)

    def __init__(self):
        super().__init__()

        self.language = "English"
        self.setWindowTitle("My App")
        self.messages = []
        self.selected_agent = "llama3.2"
        self.tts_enabled = False

        self.resize(1200, 600)

        self.supported_languages = {
            "English": "vosk-model-small-en-us-0.15",
            "Japanese": "vosk-model-ja-0.22", 
            "Portuguese": "vosk-model-small-pt-0.3"
        }
        
        self.available_models = self.scan_vosk_models()
        
        if not self.available_models:
            QMessageBox.critical(
                self, 
                "No Language Models Found", 
                "No compatible language models were found in the /Models directory.\n\n"
                "Please download one of the supported language models from Vosk's website:\n"
                "https://alphacephei.com/vosk/models\n\n"
                "Supported models:\n"
                "• English: vosk-model-small-en-us-0.15\n"
                "• Japanese: vosk-model-ja-0.22\n"
                "• Portuguese: vosk-model-small-pt-0.3"
            )
            sys.exit(1)
        
        self.language_buttons = {}
        self.create_language_buttons()

        self.listenButton = QPushButton("Start Speaking")
        self.listenButton.setObjectName("startListenButton")
        self.listenButton.clicked.connect(self.start_listening)
        self.stopListenButton = QPushButton("Stop Speaking")
        self.stopListenButton.setObjectName("stopListenButton")
        self.stopListenButton.setEnabled(False)
        self.stopListenButton.clicked.connect(self.stop_listening)
        self.listenButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.stopListenButton.setCursor(QCursor(Qt.PointingHandCursor))

        self.ttsButton = QPushButton("🔇 TTS: OFF")
        self.ttsButton.setObjectName("ttsButton")
        self.ttsButton.setCheckable(True)
        self.ttsButton.setChecked(False)
        self.ttsButton.clicked.connect(self.toggle_tts)
        self.ttsButton.setCursor(QCursor(Qt.PointingHandCursor))

        self.microphoneComboBox = QComboBox()
        self.microphoneComboBox.setMinimumWidth(250)
        self.microphoneComboBox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.microphone_devices = self.enumerate_microphones()
        for idx, name in self.microphone_devices:
            self.microphoneComboBox.addItem(name, idx)
        self.selected_device_index = self.microphone_devices[0][0] if self.microphone_devices else None
        self.microphoneComboBox.currentIndexChanged.connect(self.on_microphone_changed)

        self.agentComboBox = QComboBox()
        self.agentComboBox.setMinimumWidth(250)
        self.agentComboBox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.enumerate_ollama_models()
        self.agentComboBox.currentIndexChanged.connect(self.on_agent_changed)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        
        for language in self.supported_languages.keys():
            if language in self.language_buttons:
                self.button_group.addButton(self.language_buttons[language])

        language_layout = QHBoxLayout()
        language_layout.addStretch()
        for button in self.language_buttons.values():
            language_layout.addWidget(button)
        language_layout.addStretch()

        listen_layout = QHBoxLayout()
        listen_layout.addStretch()
        listen_layout.addWidget(self.listenButton)
        listen_layout.addWidget(self.stopListenButton)
        listen_layout.addWidget(self.ttsButton)
        listen_layout.addStretch()

        mic_layout = QHBoxLayout()
        mic_layout.addStretch()
        mic_layout.addWidget(self.microphoneComboBox)
        mic_layout.addStretch()

        agent_layout = QHBoxLayout()
        agent_layout.addStretch()
        agent_layout.addWidget(self.agentComboBox)
        agent_layout.addStretch()

        you_box = QFrame()
        you_box.setFrameShape(QFrame.StyledPanel)
        you_box.setObjectName("youBox")
        you_layout = QVBoxLayout()
        you_label = QLabel("YOU")
        you_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        you_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 12px;")
        you_layout.addWidget(you_label)

        self.you_emoji_label = QLabel("👤")
        self.you_emoji_label.setAlignment(Qt.AlignHCenter)
        self.you_emoji_label.setStyleSheet("font-size: 48px; margin-bottom: 12px;")
        you_layout.addWidget(self.you_emoji_label)

        you_layout.addStretch()
        you_box.setLayout(you_layout)
        you_box.setFixedSize(400, 400)

        ai_box = QFrame()
        ai_box.setFrameShape(QFrame.StyledPanel)
        ai_box.setObjectName("aiBox")
        ai_layout = QVBoxLayout()
        ai_label = QLabel("AI")
        ai_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        ai_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 12px;")
        ai_layout.addWidget(ai_label)

        self.ai_emoji_label = QLabel("🤖")
        self.ai_emoji_label.setAlignment(Qt.AlignHCenter)
        self.ai_emoji_label.setStyleSheet("font-size: 48px; margin-bottom: 12px;")
        ai_layout.addWidget(self.ai_emoji_label)

        ai_layout.addStretch()
        ai_box.setLayout(ai_layout)
        ai_box.setFixedSize(400, 400)

        self.conversation_log_widget = QWidget()
        self.conversation_log_layout = QVBoxLayout()
        self.conversation_log_layout.addStretch()
        self.conversation_log_widget.setLayout(self.conversation_log_layout)

        # Create text input bar and send button
        self.text_input_layout = QHBoxLayout()
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type your message here...")
        self.text_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #cccccc;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                background: white;
            }
            QLineEdit:focus {
                border: 2px solid #0078d7;
            }
        """)
        self.text_input.returnPressed.connect(self.send_text_message)
        
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("sendButton")
        self.send_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.send_button.clicked.connect(self.send_text_message)
        self.send_button.setStyleSheet("""
            #sendButton {
                background-color: #0078d7;
                color: white;
                border: 2px solid #0078d7;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 60px;
            }
            #sendButton:hover {
                background-color: #005a9e;
                border: 2px solid #005a9e;
            }
            #sendButton:disabled {
                background-color: #cccccc;
                border: 2px solid #cccccc;
                color: #666666;
            }
        """)
        
        self.text_input_layout.addWidget(self.text_input, stretch=1)
        self.text_input_layout.addWidget(self.send_button)
        
        # Add text input to conversation log widget
        self.conversation_log_layout.addLayout(self.text_input_layout)

        self.conversation_log_area = QScrollArea()
        self.conversation_log_area.setWidgetResizable(True)
        self.conversation_log_area.setWidget(self.conversation_log_widget)
        self.conversation_log_area.setMinimumWidth(400)
        self.conversation_log_area.setStyleSheet("""
            QScrollArea {
                background: #f9f9f9;
                border: 2px solid #cccccc;
                border-radius: 10px;
            }
        """)
        self.conversation_log_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        boxes_layout = QHBoxLayout()
        boxes_layout.addStretch()
        boxes_layout.addWidget(you_box)
        boxes_layout.addSpacing(20)
        boxes_layout.addWidget(self.conversation_log_area, stretch=1)
        boxes_layout.addSpacing(20)
        boxes_layout.addWidget(ai_box)
        boxes_layout.addStretch()

        main_layout = QVBoxLayout()
        main_layout.addLayout(language_layout)
        main_layout.addLayout(listen_layout)
        main_layout.addLayout(mic_layout)
        main_layout.addLayout(agent_layout)
        main_layout.addLayout(boxes_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #333;
                border: 2px solid #0078d7;
                border-radius: 8px;
                padding: 8px 24px;
                font-weight: bold;
                max-width: 100px;
            }
            QPushButton:checked {
                background-color: #0078d7;
                color: white;
            }
            QPushButton:disabled {
                background-color: #555555;
                border: 2px solid #555555;
                color: gray;
            }
            QPushButton:enabled:hover {
                background-color: #91b9fa;
            }
            #startListenButton:enabled {
                border: 2px solid #28a745;
                background-color: #e0e0e0;
            }
            #stopListenButton:enabled {
                border: 2px solid #d70000;
                background-color: #e0e0e0;
            }
            #startListenButton:enabled:hover {
                border: 2px solid #28a745;
                background-color: #c0c0c0;
            }
            #stopListenButton:enabled:hover {
                border: 2px solid #d70000;
                background-color: #c0c0c0;
            }
            #ttsButton:disabled {
                background-color: #666666;
                border: 2px solid #666666;
                color: #999999;
            }
            #youBox {
                background: #f5faff;
                border: 2px solid #0078d7;
                border-radius: 12px;
                min-width: 200px;
                min-height: 150px;
                max-width: 200px;
                max-height: 150px;
            }
            #aiBox {
                background: #fff5fa;
                border: 2px solid #d70078;
                border-radius: 12px;
                min-width: 200px;
                min-height: 150px;
                max-width: 200px;
                max-height: 150px;
            }
        """)

        self.speech_thread = None
        self.tts_thread = None
        self.ai_response_signal.connect(self.update_ai_response)

    def scan_vosk_models(self):
        available_models = {}
        models_dir = "Models"
        
        if not os.path.exists(models_dir):
            return available_models
            
        for item in os.listdir(models_dir):
            item_path = os.path.join(models_dir, item)
            if os.path.isdir(item_path):
                for language, pattern in self.supported_languages.items():
                    if pattern in item:
                        available_models[language] = item_path
                        break
        
        return available_models

    def create_language_buttons(self):
        language_emojis = {
            "English": "🇺🇸",
            "Japanese": "🇯🇵", 
            "Portuguese": "🇧🇷"
        }
        
        for language in self.supported_languages.keys():
            if language in self.available_models:
                button = QPushButton(f"{language}")
                button.setCheckable(True)
                button.setCursor(QCursor(Qt.PointingHandCursor))
                
                if language == "English":
                    button.setChecked(True)
                elif not self.available_models.get("English") and len(self.language_buttons) == 0:
                    button.setChecked(True)
                    self.language = language
                
                button.clicked.connect(lambda checked, lang=language: self.language_button_was_clicked(lang))
                
                self.language_buttons[language] = button

    def language_button_was_clicked(self, language):
        self.language = language
        self.set_language_system_message()
        
        language_emojis = {
            "English": "🇺🇸",
            "Japanese": "🇯🇵", 
            "Portuguese": "🇧🇷"
        }
        
        emoji = language_emojis.get(language, "")
        self.add_message_to_log(f"{emoji} Language set to {language}", sender="system")

    def add_message_to_log(self, text, sender="user"):
        if sender == "user":
            display_text = f"You: {text}"
            label = QLabel(display_text)
            label.setStyleSheet("color: #0078d7; font-weight: bold; margin: 6px 0;")
        elif sender == "system":
            display_text = f"{text}"
            label = QLabel(display_text)
            label.setStyleSheet("color: #ff9800; font-weight: bold; margin: 6px 0;")
        else:
            display_text = f"AI: {text}"
            label = QLabel(display_text)
            label.setStyleSheet("color: #d70078; font-weight: bold; margin: 6px 0;")
        label.setWordWrap(True)
        self.conversation_log_layout.insertWidget(self.conversation_log_layout.count() - 1, label)
        QTimer.singleShot(50, lambda: (
            QApplication.processEvents(),
            self.conversation_log_area.ensureWidgetVisible(label)
        ))

    def start_listening(self):
        if self.language in self.available_models:
            model_path = self.available_models[self.language]
        else:
            model_path = list(self.available_models.values())[0]

        device_index = self.selected_device_index
        self.listenButton.setEnabled(False)
        self.stopListenButton.setEnabled(True)
        
        for button in self.language_buttons.values():
            button.setEnabled(False)
            
        self.microphoneComboBox.setEnabled(False)
        self.agentComboBox.setEnabled(False)
        self.ttsButton.setEnabled(False)
        
        # Disable text input controls
        self.text_input.setEnabled(False)
        self.send_button.setEnabled(False)
        
        self.speech_thread = SpeechRecognitionThread(model_path, device_index)
        self.speech_thread.result_signal.connect(self.handle_speech_result)
        self.speech_thread.finished.connect(self.on_listen_finished)
        self.speech_thread.start()
        self.pulse_emoji(self.you_emoji_label, start=True)

    def handle_speech_result(self, text):
        if text == "quit":
            QMessageBox.information(self, "Quit", "I am now quitting the application! Thank you!")
            QApplication.quit()
            return

        if text == "reset":
            self.add_message_to_log("🔄 Conversation reset.", sender="system")
            self.messages = []
            self.stop_listening()
            return

        if text:
            self.add_message_to_log(text, sender="user")
            self.messages.append({'role': 'user', 'content': text})
            
            if self.speech_thread and self.speech_thread.isRunning():
                self.speech_thread.finished.disconnect()
                self.speech_thread.stop()
                self.speech_thread.wait()
            self.pulse_emoji(self.you_emoji_label, start=False)

            self.stopListenButton.setEnabled(False)

            thinking_label = QLabel("AI is thinking...")
            thinking_label.setStyleSheet("color: #d70078; margin: 6px 0;")
            thinking_label.setWordWrap(True)
            self.conversation_log_layout.insertWidget(self.conversation_log_layout.count() - 1, thinking_label)
            self.conversation_log_area.verticalScrollBar().setValue(self.conversation_log_area.verticalScrollBar().maximum())

            self.ai_emoji_label.setText("🤔")
            self.pulse_emoji(self.ai_emoji_label, start=True)

            def get_ai_response():
                response: ChatResponse = chat(model=self.selected_agent, messages=self.messages)
                self.messages.append({'role': 'assistant', 'content': response.message.content})
                self.ai_response_signal.emit(response.message.content, thinking_label)

            from threading import Thread
            Thread(target=get_ai_response).start()

    def stop_listening(self):
        if self.speech_thread and self.speech_thread.isRunning():
            self.speech_thread.stop()
            self.speech_thread.wait()
        self.listenButton.setEnabled(True)
        self.stopListenButton.setEnabled(False)
        
        for button in self.language_buttons.values():
            button.setEnabled(True)
            
        self.microphoneComboBox.setEnabled(True)
        self.agentComboBox.setEnabled(True)
        self.ttsButton.setEnabled(True)
        
        # Re-enable text input controls
        self.text_input.setEnabled(True)
        self.send_button.setEnabled(True)
        
        self.pulse_emoji(self.you_emoji_label, start=False)

    def on_listen_finished(self):
        self.listenButton.setEnabled(True)
        self.stopListenButton.setEnabled(False)
        
        for button in self.language_buttons.values():
            button.setEnabled(True)
            
        self.microphoneComboBox.setEnabled(True)
        self.agentComboBox.setEnabled(True)
        self.ttsButton.setEnabled(True)
        
        # Re-enable text input controls
        self.text_input.setEnabled(True)
        self.send_button.setEnabled(True)

    def closeEvent(self, event):
        if self.speech_thread and self.speech_thread.isRunning():
            self.speech_thread.stop()
            self.speech_thread.wait()
        event.accept()

    def update_ai_response(self, response_text, thinking_label):
        thinking_label.setText(f"AI: {response_text}")
        self.pulse_emoji(self.ai_emoji_label, start=False)
        self.ai_emoji_label.setText("🤖")
        self.speak_text(response_text)
        
        # Re-enable all controls
        self.listenButton.setEnabled(True)
        self.stopListenButton.setEnabled(False)
        self.text_input.setEnabled(True)
        self.send_button.setEnabled(True)
        
        for button in self.language_buttons.values():
            button.setEnabled(True)
            
        self.microphoneComboBox.setEnabled(True)
        self.agentComboBox.setEnabled(True)
        self.ttsButton.setEnabled(True)
        
        QTimer.singleShot(50, lambda: (
            QApplication.processEvents(),
            self.conversation_log_area.ensureWidgetVisible(thinking_label)
        ))

    def set_language_system_message(self):
        self.messages = [
            m for m in self.messages
            if m.get('role') != 'system' or not m.get('content', '').startswith(('Please respond', '日本語だけで返答してください', 'Responda apenas'))
        ]
        if self.language == "English":
            lang_msg = "Please respond in English."
        elif self.language == "Japanese":
            lang_msg = "日本語だけで返答してください。英語や他の言語は使わないでください。"
        elif self.language == "Portuguese":
            lang_msg = "Responda apenas em português brasileiro. Não use inglês ou outros idiomas."
        else:
            lang_msg = f"Please respond in {self.language}."
        self.messages.insert(0, {'role': 'system', 'content': lang_msg})

    def pulse_emoji(self, label, start=True):
        if not hasattr(label, "_pulse_timer"):
            label._pulse_timer = QTimer()
            label._pulse_grow = True
            label._pulse_size = 48

        def do_pulse():
            if label._pulse_grow:
                label._pulse_size += 4
                if label._pulse_size >= 60:
                    label._pulse_grow = False
            else:
                label._pulse_size -= 4
                if label._pulse_size <= 48:
                    label._pulse_grow = True
            label.setStyleSheet(f"font-size: {label._pulse_size}px; margin-bottom: 12px;")

        if start:
            label._pulse_timer.timeout.connect(do_pulse)
            label._pulse_timer.start(100)
        else:
            try:
                label._pulse_timer.timeout.disconnect()
            except Exception:
                pass
            label._pulse_timer.stop()
            label.setStyleSheet("font-size: 48px; margin-bottom: 12px;")

    def enumerate_microphones(self):
        p = pyaudio.PyAudio()
        devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:
                devices.append((i, f"{info['name']}"))
        p.terminate()
        if not devices:
            devices.append((None, "No microphone found"))
        return devices

    def on_microphone_changed(self, index):
        self.selected_device_index = self.microphoneComboBox.itemData(index)

    def on_agent_changed(self, index):
        self.selected_agent = self.agentComboBox.currentText()

    def enumerate_ollama_models(self):
        try:
            models = ollama_list()
            if models and hasattr(models, 'models') and models.models:
                for model in models.models:
                    model_name = model.model
                    if model_name.endswith(':latest'):
                        model_name = model_name[:-7]
                    self.agentComboBox.addItem(model_name)
                
                first_model = models.models[0].model
                if first_model.endswith(':latest'):
                    first_model = first_model[:-7]
                self.selected_agent = first_model
            else:
                QMessageBox.critical(
                    self, 
                    "No AI Models Found", 
                    "No Ollama language models were detected.\n\n"
                    "Please install at least one language model using Ollama:\n"
                    "• Download Ollama from: https://ollama.com/download\n"
                    "• Install a model: ollama run llama3.2\n"
                    "• Or try other models: ollama run mistral, ollama run codellama, etc.\n\n"
                    "For more models, visit: https://ollama.com/library"
                )
                sys.exit(1)
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Ollama Connection Error", 
                f"Failed to connect to Ollama: {str(e)}\n\n"
                "Please ensure:\n"
                "• Ollama is installed and running\n"
                "• You can run 'ollama list' in terminal\n"
                "• At least one model is installed\n\n"
                "Download Ollama from: https://ollama.com/download"
            )
            sys.exit(1)

    def toggle_tts(self):
        self.tts_enabled = self.ttsButton.isChecked()
        if self.tts_enabled:
            self.ttsButton.setText("🔊 TTS: ON")
        else:
            self.ttsButton.setText("🔇 TTS: OFF")

    def speak_text(self, text):
        if self.tts_enabled and text:
            try:
                engine = pyttsx3.init()
                if self.language == "Japanese":
                    voices = engine.getProperty('voices')
                    for voice in voices:
                        if 'japanese' in voice.name.lower() or 'ja' in voice.id.lower():
                            engine.setProperty('voice', voice.id)
                            break
                    engine.setProperty('rate', 150)
                elif self.language == "Portuguese":
                    voices = engine.getProperty('voices')
                    for voice in voices:
                        if 'portuguese' in voice.name.lower() or 'pt' in voice.id.lower():
                            engine.setProperty('voice', voice.id)
                            break
                    engine.setProperty('rate', 160)
                else:
                    engine.setProperty('rate', 175)
                engine.setProperty('volume', 0.8)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                print(f"TTS Error (main thread): {e}")

    def send_text_message(self):
        text = self.text_input.text().strip()
        if text:
            self.add_message_to_log(text, sender="user")
            self.messages.append({'role': 'user', 'content': text})
            self.text_input.clear()
            
            # Disable input controls while waiting for response
            self.text_input.setEnabled(False)
            self.send_button.setEnabled(False)
            self.listenButton.setEnabled(False)
            self.stopListenButton.setEnabled(False)
            
            for button in self.language_buttons.values():
                button.setEnabled(False)
                
            self.microphoneComboBox.setEnabled(False)
            self.agentComboBox.setEnabled(False)
            self.ttsButton.setEnabled(False)
            
            thinking_label = QLabel("AI is thinking...")
            thinking_label.setStyleSheet("color: #d70078; margin: 6px 0;")
            thinking_label.setWordWrap(True)
            # Insert thinking label at the end (before the text input layout)
            self.conversation_log_layout.insertWidget(self.conversation_log_layout.count() - 1, thinking_label)
            self.conversation_log_area.verticalScrollBar().setValue(self.conversation_log_area.verticalScrollBar().maximum())

            self.ai_emoji_label.setText("🤔")
            self.pulse_emoji(self.ai_emoji_label, start=True)

            def get_ai_response():
                response: ChatResponse = chat(model=self.selected_agent, messages=self.messages)
                self.messages.append({'role': 'assistant', 'content': response.message.content})
                self.ai_response_signal.emit(response.message.content, thinking_label)

            from threading import Thread
            Thread(target=get_ai_response).start()

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
