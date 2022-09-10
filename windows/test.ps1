cd E:\github\nas-tools
xcopy /y .\web C:\Users\sjtum\.virtualenvs\nas-tools-ZERBK7XY\Lib\site-packages\web\ /e
xcopy /y .\config C:\Users\sjtum\.virtualenvs\nas-tools-ZERBK7XY\Lib\site-packages\config\ /e
copy third-party.txt .\windows
cd windows
pyinstaller nas-tools.spec
del third-party.txt
pause