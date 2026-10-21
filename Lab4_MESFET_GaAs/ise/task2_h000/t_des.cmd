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
	Quasistationary (
		MaxStep=0.1
		Goal {Name="Drain" Voltage=2}
		Goal {Name="Gate" Voltage=-3}
	) {
		Coupled { Poisson Electron Hole }
	}
	NewCurrent="New_"
	Quasistationary (
		MaxStep=0.05
		Goal {Name="Gate" Voltage=1.5}
	) {
		Coupled { Poisson Electron Hole }
	}
}
