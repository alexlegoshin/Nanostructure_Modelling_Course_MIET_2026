File {
	Grid = "sh1_msh.grd"
	Doping = "sh1_msh.dat"
	Param = "m20"
	Plot = "Lm20.dat"
	Current = "Lm20.plt"
	Output = "Lm20.log"
}
Electrode {
	{ Name="Anode"   Voltage=0.0 }
	{ Name="Cathode" Voltage=0.0 }
}
Physics {
	Mobility( DopingDep HighFieldsat Enormal )
	EffectiveIntrinsicDensity(BandGapNarrowing (OldSlotboom))
	Recombination ( SRH(DopingDep) )
	HeavyIon (
		Direction = (0,1)
		Location  = (0.0,-0.5)
		Time      = 100e-12
		Length    = 1e-4
		Wt_hi     = 0.05e-4
		LET_f     = 0.07593
		Gaussian
		PicoCoulomb
	)
}
Plot { eDensity hDensity Potential SpaceCharge }
Math { Extrapolate Derivatives RelErrControl NewDiscretization }
Solve {
	Poisson
	Coupled { Poisson Electron Hole}
	Quasistationary ( MaxStep=0.1 Goal { Name="Anode" Voltage=-2 } )
	{ Coupled { Poisson Electron Hole} }
	NewCurrent="L_"
	Transient (
		InitialTime=0 FinalTime=4e-8
		InitialStep=1e-13 MaxStep=4e-10 MinStep=1e-16
	)
	{ Coupled { Poisson Electron Hole} }
}
