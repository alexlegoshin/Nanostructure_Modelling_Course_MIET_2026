@echo off
echo START > C:\tcad\L5\pB.txt
cd /d C:\tcad\L5\task3
C:\ISE\bin\mesh -t t > m.log 2>&1
C:\ISE\bin\dessis t_circuit_des.cmd > run.log 2>&1
echo task3 >> C:\tcad\L5\pB.txt
cd /d C:\tcad\L5\task4
C:\ISE\bin\mesh -t t > m.log 2>&1
C:\ISE\bin\dessis t_circuit2_des.cmd > run.log 2>&1
echo task4 >> C:\tcad\L5\pB.txt
echo ALL DONE >> C:\tcad\L5\pB.txt
