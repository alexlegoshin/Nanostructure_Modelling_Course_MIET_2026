File {
	Grid = "sh1_msh.grd"
	Doping = "sh1_msh.dat"
	Plot = "sh1_des.dat"
	Current = "sh1_des.plt"
	Output = "sh1_des.log"
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
	eMobility hMobility eVelocity hVelocity
	Doping DonorConcentration AcceptorConcentration
	Current/Vector
}

Math { Extrapolate Derivatives RelErrControl NewDiscretization }

Solve {
	Poisson
	Coupled { Poisson Electron Hole}
	Quasistationary ( MaxStep=0.01 Goal { Name="Anode" Voltage=4 } )
	{ Coupled { Poisson Electron Hole} }
}
