@echo off
cd /d C:\tcad\L3v2
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
echo CUTS DONE > pc.txt
