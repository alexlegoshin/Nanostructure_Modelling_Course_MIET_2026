@echo off
cd /d C:\tcad\SCAN
echo START4 > progress4.txt
C:\ISE\bin\dessis Sm20.cmd > Sm20.log 2>&1
echo done Sm20 >> progress4.txt
