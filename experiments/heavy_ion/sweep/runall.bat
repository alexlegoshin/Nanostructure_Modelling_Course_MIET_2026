@echo off
cd /d C:\tcad\SCAN
echo START > progress.txt
C:\ISE\bin\dessis m00.cmd > m00.log 2>&1
echo done m00 >> progress.txt
C:\ISE\bin\dessis m01.cmd > m01.log 2>&1
echo done m01 >> progress.txt
C:\ISE\bin\dessis m02.cmd > m02.log 2>&1
echo done m02 >> progress.txt
C:\ISE\bin\dessis m10.cmd > m10.log 2>&1
echo done m10 >> progress.txt
C:\ISE\bin\dessis m11.cmd > m11.log 2>&1
echo done m11 >> progress.txt
C:\ISE\bin\dessis m12.cmd > m12.log 2>&1
echo done m12 >> progress.txt
C:\ISE\bin\dessis m20.cmd > m20.log 2>&1
echo done m20 >> progress.txt
C:\ISE\bin\dessis m21.cmd > m21.log 2>&1
echo done m21 >> progress.txt
C:\ISE\bin\dessis m22.cmd > m22.log 2>&1
echo done m22 >> progress.txt
echo ALL DONE >> progress.txt
