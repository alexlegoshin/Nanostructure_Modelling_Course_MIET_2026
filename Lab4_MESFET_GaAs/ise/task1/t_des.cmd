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
		Goal {Name="Gate" Voltage=0.8}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_p08_")
	Quasistationary (
		MaxStep=0.1
		Goal {Name="Gate" Voltage=-0.8}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_m08_")
	Quasistationary (
		MaxStep=0.1
		Goal {Name="Gate" Voltage=-1.6}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_m16_")
	Quasistationary (
		MaxStep=0.1
		Goal {Name="Gate" Voltage=-2.4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Save (FilePrefix="Vg_m24_")
	Load (FilePrefix="Vg_00_")
	NewCurrent="Vg_00_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="Drain" Voltage=4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vg_p08_")
	NewCurrent="Vg_p08_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="Drain" Voltage=4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vg_m08_")
	NewCurrent="Vg_m08_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="Drain" Voltage=4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vg_m16_")
	NewCurrent="Vg_m16_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="Drain" Voltage=4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Load (FilePrefix="Vg_m24_")
	NewCurrent="Vg_m24_"
	Quasistationary (
		MaxStep=0.02
		Goal {Name="Drain" Voltage=4}
	) {
		Coupled { Poisson Electron Hole }
	}
}
