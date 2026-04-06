# Photon Descent

Photon Descent is a fast-paced `pygame` dodge-survival game built around rotating phase mechanics, reactive movement, and escalating bullet patterns.

## Features

- Four gameplay phases: `light`, `gravity`, `hyper`, and `mirror`
- Permanent upgrades between phases and round-based active abilities
- Resizable window support and fullscreen toggle with `F11` or `Alt+Enter`
- Local persistence for high score, selected color, and volume
- Optional PyInstaller build configuration for Windows packaging

## Requirements

- Python `3.11+`
- `pygame-ce` `2.5+`

`pygame-ce` is the tested runtime dependency for this project and is imported as `pygame`.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Running

```powershell
python photon_descent.py
```

## Controls

- `WASD` or arrow keys: move
- `Space`: dash
- `E`: use slow-motion ability
- `R`: use bubble ability
- `Right Click`: use teleport tether ability
- `Left Click`: blink after it unlocks
- `F11` or `Alt+Enter`: toggle fullscreen
- `Esc`: quit

## Building A Windows Executable

Install PyInstaller if you want to package the game:

```powershell
python -m pip install pyinstaller
pyinstaller PhotonDescent.spec
```

## Project Layout

```text
photon_descent.py              # Thin entrypoint
photon_descent_game/           # Core game package
PhotonDescent.spec             # PyInstaller build spec
*.mp3 / game.ico               # Runtime assets
```

## Notes

- No `.env` file is required for this project.
- Save data is stored outside the repository in the user's local application data directory.

## License

This project is released under the MIT License. See [LICENSE](LICENSE).
