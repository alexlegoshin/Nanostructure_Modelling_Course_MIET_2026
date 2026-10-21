@echo off
cd /d C:\tcad\L3v4
echo START > pA.txt
C:\ISE\bin\mesh -t sA > mA.log 2>&1
echo mesh A >> pA.txt
C:\ISE\bin\dessis sA_des.cmd > sA_run.log 2>&1
echo solve A >> pA.txt
if exist Ay.grd del Ay.grd
if exist Ay.dat del Ay.dat
if exist sA_msh_cut.grd del sA_msh_cut.grd
if exist sA_des_cut.dat del sA_des_cut.dat
C:\ISE\bin\dfisetools -cut sA_msh.grd sA_des.dat < cutAy.txt > c_Ay.log 2>&1
ren sA_msh_cut.grd Ay.grd
ren sA_des_cut.dat Ay.dat
if exist AyTop.plt del AyTop.plt
if exist Ay_plt.plt del Ay_plt.plt
C:\ISE\bin\dfisetools -plot Ay.grd Ay.dat < topline.txt > p_Ay.log 2>&1
ren Ay_plt.plt AyTop.plt
echo ALL DONE >> pA.txt
