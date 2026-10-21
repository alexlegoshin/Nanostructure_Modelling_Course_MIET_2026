File {
	Grid = "t_msh.grd"
	Doping = "t_msh.dat"
	Plot = "t_des.dat"
	Current = "t_msh.plt"
	Output = "t_des.log"
}

Electrode {
	{ Name="Source" Voltage=0.0 }
	{ Name="Drain" Voltage=0.0 }
	{ Name="Gate" Schottky barrier=0.75 Voltage=0 }
}

Physics {
	AreaFactor = 1000
	Mobility ( DopingDependence HighFieldSaturation Enormal )
	EffectiveIntrinsicDensity ( OldSlotboom )
	Recombination ( SRH ( DopingDependence ) )
}

Physics ( Material = "AlGaAs" ) {
	MoleFraction( RegionName="S5" XFraction=1.0 Grading=0.03 )
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
	Save (FilePrefix="Vg_00_")
	Quasistationary (
		MaxStep=0.1
		Goal {Name="Gate" Voltage=0.2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_02_")
	Quasistationary (
		MaxStep=0.1
		Goal {Name="Gate" Voltage=0.4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_04_")
	Quasistationary (
		MaxStep=0.1
		Goal {Name="Gate" Voltage=0.6}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_06_")
	Quasistationary (
		MaxStep=0.1
		Goal {Name="Gate" Voltage=0.8}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_08_")
	Load (FilePrefix="Vg_00_")
	NewCurrent="Vg_00_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="Drain" Voltage=4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vg_02_")
	NewCurrent="Vg_02_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="Drain" Voltage=4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vg_04_")
	NewCurrent="Vg_04_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="Drain" Voltage=4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vg_06_")
	NewCurrent="Vg_06_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="Drain" Voltage=4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vg_08_")
	NewCurrent="Vg_08_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="Drain" Voltage=4}
	) {
		Coupled { Poisson Electron Hole }
	}
}
