@echo off
cd /d C:\tcad\L3v4
echo START > pB.txt
C:\ISE\bin\mesh -t sB > mB.log 2>&1
echo mesh B >> pB.txt
C:\ISE\bin\dessis sB_des.cmd > sB_run.log 2>&1
echo solve B >> pB.txt
if exist By.grd del By.grd
if exist By.dat del By.dat
if exist sB_msh_cut.grd del sB_msh_cut.grd
if exist sB_des_cut.dat del sB_des_cut.dat
C:\ISE\bin\dfisetools -cut sB_msh.grd sB_des.dat < cutBy.txt > c_By.log 2>&1
ren sB_msh_cut.grd By.grd
ren sB_des_cut.dat By.dat
if exist Bx75.grd del Bx75.grd
if exist Bx75.dat del Bx75.dat
if exist sB_msh_cut.grd del sB_msh_cut.grd
if exist sB_des_cut.dat del sB_des_cut.dat
C:\ISE\bin\dfisetools -cut sB_msh.grd sB_des.dat < cutBx75.txt > c_Bx75.log 2>&1
ren sB_msh_cut.grd Bx75.grd
ren sB_des_cut.dat Bx75.dat
if exist Bx25.grd del Bx25.grd
if exist Bx25.dat del Bx25.dat
if exist sB_msh_cut.grd del sB_msh_cut.grd
if exist sB_des_cut.dat del sB_des_cut.dat
C:\ISE\bin\dfisetools -cut sB_msh.grd sB_des.dat < cutBx25.txt > c_Bx25.log 2>&1
ren sB_msh_cut.grd Bx25.grd
ren sB_des_cut.dat Bx25.dat
if exist ByTop.plt del ByTop.plt
if exist By_plt.plt del By_plt.plt
C:\ISE\bin\dfisetools -plot By.grd By.dat < topline.txt > p_By.log 2>&1
ren By_plt.plt ByTop.plt
echo ALL DONE >> pB.txt
