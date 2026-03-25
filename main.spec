#import os
#block_cipher = None
#
#a = Analysis(
#    ['src\\main.py'],
#    pathex=['E:\\python_projects\\Pr0j3ct'],
#    binaries=[],
#    datas=[
#        ('icons', 'icons'),
#        ('Audio', 'Audio'),
#        ('models', 'models'),
#        ('logs', 'logs'),
#        ('.env', '.'),
#        ('E:\\python_projects\\Pr0j3ct\\venv_312\\Lib\\site-packages\\vosk', 'vosk'),
#        ('E:\\huggingface_cache\\hub', 'transformers_cache'),
#    ],
#    hiddenimports=[
#        'vosk',
#        'transformers',
#        'torch',
#        'customtkinter',
#        'tkinter',
#        'pydub',
#        'numpy',
#        'librosa',
#        'langdetect',
#        'langid',
#        'deep-translator',
#        'googletrans',
#        'pygame',
#    ],
#    hookspath=[],
#    runtime_hooks=[],
#    excludes=['pandas', 'pytz'],
#    win_no_prefer_redirects=False,
#    win_private_assemblies=False,
#    cipher=block_cipher,
#    noarchive=False,
#)
#
## Додаємо бінарні файли (DLL) вручну
#for dll in ['libvosk.dll', 'libgcc_s_seh-1.dll', 'libstdc++-6.dll', 'libwinpthread-1.dll']:
#    a.binaries.append((
#        dll,
#        os.path.join('E:\\python_projects\\Pr0j3ct\\venv_312\\Lib\\site-packages\\vosk', dll),
#        'BINARY'
#    ))
#
#pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
#
#exe = EXE(
#    pyz,
#    a.scripts,
#    [],  # Залишаємо порожнім для --onedir
#    exclude_binaries=True,  # Виключаємо бінарники з EXE
#    name='AudioTranslator',
#    debug=False,
#    bootloader_ignore_signals=False,
#    strip=False,
#    upx=False,
#    upx_exclude=[],
#    runtime_tmpdir=None,
#    console=False,
#    icon='icons\\img.ico',
#)
#
#coll = COLLECT(
#    exe,
#    a.binaries,
#    a.zipfiles,
#    a.datas,
#    strip=False,
#    upx=False,
#    upx_exclude=[],
#    name='AudioTranslator',
#)

import os
block_cipher = None

a = Analysis(
    ['src\\main.py'],
    pathex=['E:\\python_projects\\Pr0j3ct'],
    binaries=[],
    datas=[
        ('icons', 'icons'),
        ('Audio', 'Audio'),
        ('models', 'models'),
        ('logs', 'logs'),
        ('.env', '.'),
        ('E:\\python_projects\\Pr0j3ct\\venv_312\\Lib\\site-packages\\vosk', 'vosk'),
        ('E:\\huggingface_cache\\hub', 'transformers_cache'),
    ],
    hiddenimports=[
        'vosk',
        'transformers',
        'torch',
        'customtkinter',
        'tkinter',
        'pydub',
        'numpy',
        'librosa',
        'langdetect',
        'langid',
        'deep-translator',
        'googletrans',
        'pygame',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['pandas', 'pytz'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

for dll in ['libvosk.dll', 'libgcc_s_seh-1.dll', 'libstdc++-6.dll', 'libwinpthread-1.dll']:
    a.binaries.append((
        dll,
        os.path.join('E:\\python_projects\\Pr0j3ct\\venv_312\\Lib\\site-packages\\vosk', dll),
        'BINARY'
    ))

a.binaries.append((
    'python312.dll',
    'C:\\Python312\\python312.dll',
    'BINARY'
))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AudioTranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon='icons\\img.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AudioTranslator',
)