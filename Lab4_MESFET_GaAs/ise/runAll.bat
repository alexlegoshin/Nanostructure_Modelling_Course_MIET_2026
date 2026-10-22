@echo off
echo START > C:\tcad\L4\pAll.txt
cd /d C:\tcad\L4\task1
C:\ISE\bin\mesh -t t > m.log 2>&1
C:\ISE\bin\dessis t_des.cmd > run.log 2>&1
echo task1 >> C:\tcad\L4\pAll.txt
cd /d C:\tcad\L4\task2_h050
C:\ISE\bin\mesh -t t > m.log 2>&1
C:\ISE\bin\dessis t_des.cmd > run.log 2>&1
echo task2_h050 >> C:\tcad\L4\pAll.txt
cd /d C:\tcad\L4\task2_h040
C:\ISE\bin\mesh -t t > m.log 2>&1
C:\ISE\bin\dessis t_des.cmd > run.log 2>&1
echo task2_h040 >> C:\tcad\L4\pAll.txt
cd /d C:\tcad\L4\task2_h030
C:\ISE\bin\mesh -t t > m.log 2>&1
C:\ISE\bin\dessis t_des.cmd > run.log 2>&1
echo task2_h030 >> C:\tcad\L4\pAll.txt
cd /d C:\tcad\L4\task2_h020
C:\ISE\bin\mesh -t t > m.log 2>&1
C:\ISE\bin\dessis t_des.cmd > run.log 2>&1
echo task2_h020 >> C:\tcad\L4\pAll.txt
cd /d C:\tcad\L4\task2_h010
C:\ISE\bin\mesh -t t > m.log 2>&1
C:\ISE\bin\dessis t_des.cmd > run.log 2>&1
echo task2_h010 >> C:\tcad\L4\pAll.txt
cd /d C:\tcad\L4\task2_h000
C:\ISE\bin\mesh -t t > m.log 2>&1
C:\ISE\bin\dessis t_des.cmd > run.log 2>&1
echo task2_h000 >> C:\tcad\L4\pAll.txt
cd /d C:\tcad\L4\task2_h000_ladder
C:\ISE\bin\mesh -t t > m.log 2>&1
C:\ISE\bin\dessis t_des.cmd > run.log 2>&1
echo task2_h000_ladder >> C:\tcad\L4\pAll.txt
cd /d C:\tcad\L4\task3
C:\ISE\bin\mesh -t t > m.log 2>&1
C:\ISE\bin\dessis t_des.cmd > run.log 2>&1
echo task3 >> C:\tcad\L4\pAll.txt
cd /d C:\tcad\L4\task4
C:\ISE\bin\mesh -t t > m.log 2>&1
C:\ISE\bin\dessis t_des.cmd > run.log 2>&1
echo task4 >> C:\tcad\L4\pAll.txt
echo ALL DONE >> C:\tcad\L4\pAll.txt
