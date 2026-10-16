File {
	Grid = "sA_msh.grd"
	Doping = "sA_msh.dat"
	Plot = "sA_des.dat"
	Current = "sA_des.plt"
	Output = "sA_des.log"
}

Electrode {
	{ Name="Anode"   Voltage=0.0 }
	{ Name="Cathode" Voltage=0.0 }
}

Physics {
	Mobility( DopingDep HighFieldsat Enormal )
	EffectiveIntrinsicDensity(BandGapNarrowing (OldSlotboom))
}

Plot {
	eDensity hDensity eCurrent hCurrent
	Potential SpaceCharge ElectricField
	Doping DonorConcentration AcceptorConcentration
	Current/Vector
}

Math {
	Extrapolate
	Derivatives
	RelErrControl
	NewDiscretization

	iterations=5
	method=slip
}

Solve {
	Poisson
	Coupled { Poisson Electron Hole}
	Quasistationary ( MaxStep=0.05 Goal { Name="Anode" Voltage=4 } )
	{ Coupled { Poisson Electron Hole} }
}
