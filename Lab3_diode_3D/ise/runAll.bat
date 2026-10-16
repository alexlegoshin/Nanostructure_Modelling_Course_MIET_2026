@echo off
cd /d C:\tcad\L3v2
echo START > pa.txt
C:\ISE\bin\mesh -t sA > mA.log 2>&1
echo mesh A >> pa.txt
C:\ISE\bin\dessis sA_des.cmd > sA_run.log 2>&1
echo solve A >> pa.txt
C:\ISE\bin\mesh -t sB > mB.log 2>&1
echo mesh B >> pa.txt
C:\ISE\bin\dessis sB_des.cmd > sB_run.log 2>&1
echo solve B >> pa.txt
C:\ISE\bin\dfisetools -cut sA_msh.grd sA_des.dat < cutAy.txt > c1.log 2>&1
ren sA_msh_cut.grd Ay.grd
ren sA_des_cut.dat Ay.dat
C:\ISE\bin\dfisetools -cut sB_msh.grd sB_des.dat < cutBy.txt > c2.log 2>&1
ren sB_msh_cut.grd By.grd
ren sB_des_cut.dat By.dat
C:\ISE\bin\dfisetools -cut sB_msh.grd sB_des.dat < cutBx75.txt > c3.log 2>&1
ren sB_msh_cut.grd Bx75.grd
ren sB_des_cut.dat Bx75.dat
C:\ISE\bin\dfisetools -cut sB_msh.grd sB_des.dat < cutBx25.txt > c4.log 2>&1
ren sB_msh_cut.grd Bx25.grd
ren sB_des_cut.dat Bx25.dat
C:\ISE\bin\dfisetools -plot Ay.grd Ay.dat < topline.txt > pl1.log 2>&1
ren Ay_plt.plt AyTop.plt
C:\ISE\bin\dfisetools -plot By.grd By.dat < topline.txt > pl2.log 2>&1
ren By_plt.plt ByTop.plt
echo ALL DONE >> pa.txt
