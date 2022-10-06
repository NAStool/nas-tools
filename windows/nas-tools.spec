# -*- mode: python -*-

# <<< START ADDED PART
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT, BUNDLE, TOC


def collect_pkg_data(package, include_py_files=True, subdir=None):
    import os
    from PyInstaller.utils.hooks import get_package_paths, remove_prefix, PY_IGNORE_EXTENSIONS

    # Accept only strings as packages.
    if type(package) is not str:
        raise ValueError

    pkg_base, pkg_dir = get_package_paths(package)
    if subdir:
        pkg_dir = os.path.join(pkg_dir, subdir)
    # Walk through all file in the given package, looking for data files.
    data_toc = TOC()
    for dir_path, dir_names, files in os.walk(pkg_dir):
        for f in files:
            extension = os.path.splitext(f)[1]
            if include_py_files or (extension not in PY_IGNORE_EXTENSIONS):
                source_file = os.path.join(dir_path, f)
                dest_folder = remove_prefix(dir_path, os.path.dirname(pkg_base) + os.sep)
                dest_file = os.path.join(dest_folder, f)
                data_toc.append((dest_file, source_file, 'DATA'))

    return data_toc

pkg_data1 = collect_pkg_data('web')
pkg_data2 = collect_pkg_data('config') # <<< Put the name of your package here
# <<< END ADDED PART


# <<< START PATHEX PART
pathex_tp = []
with open("third_party.txt") as third_party:
    for third_party_lib in third_party:
        pathex_tp.append(('./../third_party/' + third_party_lib).replace("\n", ""))
# <<< END PATHEX PART

block_cipher = None


a = Analysis(
             ['./../run.py'],
             pathex=pathex_tp,
             binaries=[],
             datas=[],
             hiddenimports=['pkg_resources.py2_warn', 
                            'babelfish.converters.alpha2',
                            'babelfish.converters.alpha3b',
                            'babelfish.converters.alpha3t',
                            'babelfish.converters.name',
                            'babelfish.converters.countryname'],
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
a.datas += [('./nas-tools.ico', './nas-tools.ico', 'DATA')]
a.datas += [('./third_party.txt', './third_party.txt', 'DATA')]
exe = EXE(
          pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          pkg_data1,
          pkg_data2,
          [],
          name='nas-tools',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
	      icon='nas-tools.ico'
)
