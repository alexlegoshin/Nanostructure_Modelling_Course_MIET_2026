File {
	Grid = "sh1_msh.grd"
	Doping = "sh1_msh.dat"
	Plot = "see_des.dat"
	Current = "see_des.plt"
	Output = "see_des.log"
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
		LET_f     = 0.2
		Gaussian
		PicoCoulomb
	)
}

Plot {
	eDensity hDensity eCurrent hCurrent
	Potential SpaceCharge ElectricField
	Doping HeavyIonChargeDensity Current/Vector
}

Math { Extrapolate Derivatives RelErrControl NewDiscretization }

Solve {
	Poisson
	Coupled { Poisson Electron Hole}

	Quasistationary ( MaxStep=0.1 Goal { Name="Anode" Voltage=-2 } )
	{ Coupled { Poisson Electron Hole} }

	NewCurrent="ion_"

	Transient (
		InitialTime=0 FinalTime=2e-9
		InitialStep=1e-13 MaxStep=2e-11 MinStep=1e-16
	)
	{ Coupled { Poisson Electron Hole} }
}
