@echo off
cd /d C:\tcad\SCAN
echo START3 > progress3.txt
C:\ISE\bin\dessis Tm00.cmd > Tm00.log 2>&1
echo done Tm00 >> progress3.txt
C:\ISE\bin\dessis Tm10.cmd > Tm10.log 2>&1
echo done Tm10 >> progress3.txt
C:\ISE\bin\dessis Tm20.cmd > Tm20.log 2>&1
echo done Tm20 >> progress3.txt
echo ALL DONE 3 >> progress3.txt
