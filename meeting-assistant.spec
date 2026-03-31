# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Meeting Assistant."""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all submodules for packages that have dynamic imports
hidden_imports = [
    # pywinauto and COM automation
    'pywinauto',
    'pywinauto.application',
    'pywinauto.findwindows',
    'pywinauto.controls',
    'pywinauto.controls.uiawrapper',
    'comtypes',
    'comtypes.client',
    'comtypes.stream',

    # Google Generative AI
    'google.generativeai',
    'google.ai.generativelanguage',
    'google.protobuf',

    # Speech Recognition
    'speech_recognition',

    # Audio
    'sounddevice',
    'numpy',
    'scipy',
    'scipy.io',
    'scipy.io.wavfile',

    # UI and keyboard
    'keyboard',
    'rich',
    'rich.console',
    'rich.panel',
    'rich.table',
    'rich.markdown',
    'rich.live',

    # Environment
    'dotenv',

    # Our modules
    'config',
    'ai',
    'ai.provider',
    'ai.gemini',
    'ai.grok',
    'ai.factory',
    'audio',
    'audio.capture',
    'transcription',
    'transcription.base',
    'transcription.factory',
    'transcription.windows',
    'transcription.macos',
    'assistant',
    'assistant.advisor',
    'summary',
    'summary.generator',
    'ui',
    'ui.console',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('.env.example', '.'),
        ('prompts.yaml', '.'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='meeting-assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Console mode for rich UI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='meeting-assistant',
)
