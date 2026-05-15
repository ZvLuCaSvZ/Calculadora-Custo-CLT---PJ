
from __future__ import annotations

import PyInstaller.__main__

from gui import (
    App,
)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

PyInstaller.__main__.run([
  '--noupx',
  '--name=Calculadora CLT x PJ',             
    '--icon=favicon.ico',          
    '--windowed',
    '--noconsole',
   'main.py'
])