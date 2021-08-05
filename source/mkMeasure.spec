# -*- mode: python ; coding: utf-8 -*-
block_cipher = None


a = Analysis(['mkMeasure.py'],
             pathex=['/home/pi/mkMeasure/source'],
             binaries=[('SensBoxEnvSer','.')],
             datas=[('/home/kello/.local/lib/python3.6/site-packages/pyvisa_py','pyvisa_py')],
             hiddenimports=['KEITHLEY','NEWKEITHLEY','ESP100','NHQ201','EnvServ','pyvisa_py'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='mkMeasure',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='mkMeasure')
