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
	Quasistationary (
		MaxStep=0.1
		Goal {Name="drain" Voltage=1}
		Goal {Name="gate" Voltage=-10}
	) {
		Coupled { Poisson Electron Hole }
	}
	NewCurrent="New_"
	Quasistationary (
		InitialStep=1e-3 MaxStep=0.01 MinStep=1e-15
		Goal {Name="gate" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
}
