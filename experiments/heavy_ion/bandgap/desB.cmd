File {
	Grid = "sh1_msh.grd"
	Doping = "sh1_msh.dat"
	Param = "egB"
	Plot = "pB.dat"
	Current = "pB.plt"
	Output = "pB.log"
}
Electrode {
	{ Name="Anode"   Voltage=0.0 }
	{ Name="Cathode" Voltage=0.0 }
}
Physics {
	Mobility( DopingDep HighFieldsat Enormal )
	EffectiveIntrinsicDensity(BandGapNarrowing (OldSlotboom))
}
Plot { eDensity hDensity Potential SpaceCharge Doping }
Math { Extrapolate Derivatives RelErrControl NewDiscretization }
Solve {
	Poisson
	Coupled { Poisson Electron Hole}
	Quasistationary ( MaxStep=0.02 Goal { Name="Anode" Voltage=4 } )
	{ Coupled { Poisson Electron Hole} }
}
