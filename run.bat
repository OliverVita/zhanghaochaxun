@echo off
echo 正在启动账号查询系统...

:: 检查依赖
echo 正在检查依赖项...
pip install -r requirements.txt

:: 启动程序
echo 正在启动程序...
python main.py

pause 