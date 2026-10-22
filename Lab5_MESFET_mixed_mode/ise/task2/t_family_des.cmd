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
		Goal {Name="gate" Voltage=0.8}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_p08")
	Quasistationary (
		MaxStep=0.1
		Goal {Name="gate" Voltage=0}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_p00")
	Quasistationary (
		MaxStep=0.1
		Goal {Name="gate" Voltage=-0.8}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_m08")
	Quasistationary (
		MaxStep=0.1
		Goal {Name="gate" Voltage=-1.6}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_m16")
	Quasistationary (
		MaxStep=0.1
		Goal {Name="gate" Voltage=-2.4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_m24")
	Load (FilePrefix="Vg_p08")
	NewCurrent="Vg_p08_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="drain" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vg_p00")
	NewCurrent="Vg_p00_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="drain" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vg_m08")
	NewCurrent="Vg_m08_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="drain" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vg_m16")
	NewCurrent="Vg_m16_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="drain" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vg_m24")
	NewCurrent="Vg_m24_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="drain" Voltage=2}
	) {
		Coupled { Poisson Electron Hole }
	}
}
