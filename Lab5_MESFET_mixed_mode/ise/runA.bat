@echo off
:wait
findstr /c:"ALL DONE" C:\tcad\L4\pAll.txt >nul 2>&1
if errorlevel 1 (ping -n 61 127.0.0.1 >nul & goto wait)
echo START > C:\tcad\L5\pA.txt
cd /d C:\tcad\L5\task2
C:\ISE\bin\mesh -t t > m.log 2>&1
echo mesh >> C:\tcad\L5\pA.txt
C:\ISE\bin\dessis t_gate_des.cmd > r_t_gate.log 2>&1
echo t_gate_des.cmd >> C:\tcad\L5\pA.txt
C:\ISE\bin\dessis t_family_2_des.cmd > r_t_family_2.log 2>&1
echo t_family_2_des.cmd >> C:\tcad\L5\pA.txt
C:\ISE\bin\dessis t_family_des.cmd > r_t_family.log 2>&1
echo t_family_des.cmd >> C:\tcad\L5\pA.txt
C:\ISE\bin\dessis t_des.cmd > r_t.log 2>&1
echo t_des.cmd >> C:\tcad\L5\pA.txt
echo ALL DONE >> C:\tcad\L5\pA.txt
