### Description

This is just a proof of concept app that I made to test playing with 2 tools:

- [Vosk](https://alphacephei.com/vosk/) voice recognition tool
- [Ollama](https://ollama.com/) local AI agents

### Installation and Requirements

You're going to need Python, models for your chosen languages provided by [Vosk](https://alphacephei.com/vosk/), at least one local LLM provided by [Ollama](https://ollama.com/) and portaudio.

> Downloaded voice recognition models should go into your Models folder.

You can download your voice recognition language models from Vosk [here](https://alphacephei.com/vosk/models).

You can download Ollama [here](https://ollama.com/download) and go through their setup to choose a local LLM to install.

To install portaudio on MacOS run:

```sh
brew install portaudio
```

Now, we need to install some Python dependencies:

```sh
pip3 install vosk pyaudio ollama PyQt5
```

After you have Ollama set up, run this to download the LLMs used on this app:
(or just run the LLM(s) you plan on using and adjust the code accordingly)

```sh
ollama run llama3.2
```

```sh
ollama run deepseek-r1
```

You should be good to go at this point.

### Running

To run this simply use the following command:

```sh
python3 main.py
```

This will now open up a window allowing you to select your voice recognition language and AI agent language (Default English).

You can also select which microphone to use from the detected inputs.

Once you are ready to speak to the AI agent, press "Start Listening" and then start talking into your microphone. The system will detect when the speaking stops and send it to the AI agent.

#### Example

<img width="1312" alt="image" src="https://github.com/user-attachments/assets/4b34091a-6548-412f-985d-0bbbf107ca8e" />

### Voice Commands

There are a few voice commands to perform different functions. Here is what is available at the moment:

- **quit**

  - This will quit and close the application

- **reset**
  - This will reset the current session history with AI agent, essentially starting from scratch
