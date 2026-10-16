@echo off
cd /d C:\tcad\SCAN
echo START2 > progress2.txt
C:\ISE\bin\dessis Lm00.cmd > Lm00.log 2>&1
echo done Lm00 >> progress2.txt
C:\ISE\bin\dessis Lm10.cmd > Lm10.log 2>&1
echo done Lm10 >> progress2.txt
C:\ISE\bin\dessis Lm20.cmd > Lm20.log 2>&1
echo done Lm20 >> progress2.txt
echo ALL DONE 2 >> progress2.txt
