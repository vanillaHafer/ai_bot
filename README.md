### Description

This is just a proof of concept app that I made to test playing with 2 tools:

- [Vosk](https://alphacephei.com/vosk/) voice recognition tool
- [Ollama](https://ollama.com/) local AI agents

### Installation and Requirements

You're going to need Python, a model for your language of choice provided by Vosk, and a local LLM provided by Ollama and portaudio.

> Downloaded voice recognition models should go into your Models folder.

You can download your voice recognition language models from Vosk [here](https://alphacephei.com/vosk/models).

You can download Ollama [here](https://ollama.com/download) and go through their setup to choose a local LLM to install.

To install portaudio on MacOS run:

```sh
brew install portaudio
```

Now, we need to install some Python dependencies:

```sh
pip3 install vosk pyaudio ollama
```

After you have Ollama set up, run this to download the LLM used on this app:

```sh
ollama run llama3.2
```

You should be good to go at this point.

### Running

To run this simply use the following command:

```sh
python3 main.py
```

> [!CAUTION]
> You may find that it's not running, spitting out some issue about about the stream with this error
> `OSError: [Errno -9998] Invalid number of channels`
>
> Run `tool.py` (instructions at the bottom) to get your list of available input sources.
> Use whatever input device id you want to use for `input_device_index` on `line 18` of `main.py`

It should now prompt you to go ahead and start talking to the AI.

Once you are finished speaking it will show you what you said (green text preceded by 👤:)

The AI will then respond in text (cyan text preceded by 🧠:)

#### Example

<img width="885" alt="image" src="https://github.com/user-attachments/assets/0a827d42-7799-4b88-b722-8738c4799561" />

### Voice Commands

There are a few voice commands to perform different functions. Here is what is available at the moment:

- **quit**

  - This will quit and close the application

- **reset**
  - This will reset the current session history with AI agent, essentially starting from scratch

### Extras

There is a tool.py script that will let you know what microphones exist, and what their ID is that you can use inside the app.

To run this simply run:

```sh
python3 tool.py
```

and you should see some output like this:

```
Input Device id 2: Some Microphone
Input Device id 3: Some Microphone
Input Device id 6: Some Microphone
Input Device id 8: Some Microphone
Input Device id 9: Some Microphone
```
