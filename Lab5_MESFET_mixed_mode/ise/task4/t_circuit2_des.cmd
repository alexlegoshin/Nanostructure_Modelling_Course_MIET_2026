Device MESFET {
	File {
		Grid = "t_msh.grd"
		Doping = "t_msh.dat"
		Param = "Ion.par"
		Plot = "des.dat"
		Current = "des.plt"
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
}

System {
	Vsource_pset v1 (n1 n0) { dc = -5.63 }
	Vsource_pset v2 (n2 n1) { sine = ( 0.0 0.4 9000 0.0 0.0) }
	Vsource_pset v3 (n3 n2) { sine = ( 0.0 0.25 1000 0.0 0.0) }
	Vsource_pset v4 (n6 n0) { dc = 1 }
	Resistor_pset r (n5 n0) { resistance = 1 }
	Resistor_pset r1 (n4 n6) { resistance = 30 }
	Capacitor_pset c (n4 n6) { capacitance = 1.25e-06 }
	Inductor_pset l (n4 n6) { inductance = 0.0002502 }
	MESFET fet ( "source"=n5 "gate"=n3 "drain"=n4 )
	Set (n0 = 0)
	Set (n5 = 0.0)
	Plot "nodes.plt" (time() n0 n1 n2 n3 n4 n5 n6)
}

Plot {
	eDensity hDensity eCurrent hCurrent
	Potential SpaceCharge ElectricField
	eMobility hMobility eVelocity hVelocity
	Doping DonorConcentration AcceptorConcentration
	Current/Vector
}
Math {
	Iterations = 13
	Extrapolate
	Derivatives
	RelErrControl
	NewDiscretization
	NoCheckTransientError
}

Solve {
	Coupled { Poisson }
	Coupled { Poisson Electron Hole Contact Circuit }
	Unset (n4)
	Unset (n5)
	NewCurrent="New_"
	Transient (
		InitialTime=0 FinalTime=0.004
		InitialStep=1e-7 MaxStep=2e-05 MinStep=1e-36
		Increment=1.1
	) {
		Coupled { Poisson Electron Hole Contact Circuit }
	}
}
