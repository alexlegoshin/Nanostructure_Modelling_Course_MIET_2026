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
		MaxStep=0.05 MinStep=1e-6
		Goal {Name="Gate" Voltage=0}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.05}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.1}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.15}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.25}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.3}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.35}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.45}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.5}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.55}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.6}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.65}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.7}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.75}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.8}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.85}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.9}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=0.95}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=1}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=1.05}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=1.1}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=1.15}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=1.2}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=1.25}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=1.3}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=1.35}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=1.4}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=1.45}
	) {
		Coupled { Poisson Electron Hole }
	}
	Quasistationary (
		InitialStep=1 MaxStep=1 MinStep=0.99
		Goal {Name="Gate" Voltage=1.5}
	) {
		Coupled { Poisson Electron Hole }
	}
}
