File {
	Grid = "t_msh.grd"
	Doping = "t_msh.dat"
	Param = "Ion.par"
	Plot = "t_des.dat"
	Current = "t_des.plt"
	Output = "t_des.log"
}
Electrode {
	{ Name="source" Voltage=0.0 }
	{ Name="drain" Voltage=0.0 }
	{ Name="gate" Schottky barrier=0.75 Voltage=0 }
}
Physics {
	AreaFactor = 1000
	IncompleteIonization
	Mobility ( DopingDependence HighFieldSaturation )
}
Plot {
	eDensity hDensity eCurrent hCurrent
	Potential SpaceCharge ElectricField
	eMobility hMobility eVelocity hVelocity
	Doping DonorConcentration AcceptorConcentration
	Current/Vector
}
Math {
	Extrapolate
	Derivatives
	RelErrControl
	NewDiscretization
}

Solve {
	Coupled ( Iterations=100 ) { Poisson }
	Coupled { Poisson Electron Hole }
	Save (FilePrefix="VdVg_00")
	Load (FilePrefix="VdVg_00")
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.1 MinStep=1e-15
		Goal {Name="drain" Voltage=0.1}
		Goal {Name="gate" Voltage=-10}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vd_010")
	Load (FilePrefix="VdVg_00")
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.1 MinStep=1e-15
		Goal {Name="drain" Voltage=0.2}
		Goal {Name="gate" Voltage=-10}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vd_020")
	Load (FilePrefix="VdVg_00")
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.1 MinStep=1e-15
		Goal {Name="drain" Voltage=0.5}
		Goal {Name="gate" Voltage=-10}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vd_050")
	Load (FilePrefix="VdVg_00")
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.1 MinStep=1e-15
		Goal {Name="drain" Voltage=0.8}
		Goal {Name="gate" Voltage=-10}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vd_080")
	Load (FilePrefix="VdVg_00")
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.1 MinStep=1e-15
		Goal {Name="drain" Voltage=1}
		Goal {Name="gate" Voltage=-10}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vd_100")
	Load (FilePrefix="VdVg_00")
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.1 MinStep=1e-15
		Goal {Name="drain" Voltage=1.5}
		Goal {Name="gate" Voltage=-10}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vd_150")
	Load (FilePrefix="VdVg_00")
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.1 MinStep=1e-15
		Goal {Name="drain" Voltage=2}
		Goal {Name="gate" Voltage=-10}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vd_200")
	Load (FilePrefix="Vd_010")
	NewCurrent="Vd_010_"
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.01 MinStep=1e-15
		Increment = 1.1
		Goal {Name="gate" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vd_020")
	NewCurrent="Vd_020_"
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.01 MinStep=1e-15
		Increment = 1.1
		Goal {Name="gate" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vd_050")
	NewCurrent="Vd_050_"
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.01 MinStep=1e-15
		Increment = 1.1
		Goal {Name="gate" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vd_080")
	NewCurrent="Vd_080_"
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.01 MinStep=1e-15
		Increment = 1.1
		Goal {Name="gate" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vd_100")
	NewCurrent="Vd_100_"
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.01 MinStep=1e-15
		Increment = 1.1
		Goal {Name="gate" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vd_150")
	NewCurrent="Vd_150_"
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.01 MinStep=1e-15
		Increment = 1.1
		Goal {Name="gate" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vd_200")
	NewCurrent="Vd_200_"
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.01 MinStep=1e-15
		Increment = 1.1
		Goal {Name="gate" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
}
