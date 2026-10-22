Title "Transistor"

Definitions {
    Refinement "Default Region"
    {
      MaxElementSize = (0.2 0.02 )
      MinElementSize = (0.02 0.002 )
      RefineFunction = MaxTransDiff(Variable = "DopingConcentration", Value = 1)
    }
    Refinement "Mesh1"
    {
      MaxElementSize = (0.1 0.01 )
      MinElementSize = (0.01 0.001 )
      RefineFunction = MaxTransDiff(Variable = "DopingConcentration", Value = 1)
    }
    AnalyticalProfile "P1"
    {
      Species = "PhosphorusActiveConcentration"
      Function = Gauss(PeakPos = 0, PeakVal = 8.0e+017, StdDev = 0.05)
      LateralFunction = Gauss(Factor = 0)
    }
    AnalyticalProfile "P2"
    {
      Species = "PhosphorusActiveConcentration"
      Function = Gauss(PeakPos = 0, PeakVal = 3e+018, StdDev = 0.02)
      LateralFunction = Gauss(Factor = 0)
    }
    Constant "P3"
    {
      Species = "PhosphorusActiveConcentration"
      Value = 1e+014
    }
}

Placements {
    Refinement "Default Region" { Reference = "Default Region" }
    Refinement "Mesh1" { Reference = "Mesh1" RefineWindow = rectangle [( 1.25 0.04 ) , ( 2.75 0.2 )] }
    AnalyticalProfile "P1" { Reference = "P1" ReferenceElement { Element = line [( 0 0.1157 ) , ( 4 0.1157 )] } }
    AnalyticalProfile "P2" { Reference = "P2" ReferenceElement { Element = line [( 0 0 ) , ( 4 0 )] } }
    Constant "P3" { Reference = "P3" EvaluateWindow { Element = rectangle [( 0 0 ) , ( 4 0.36 )] DecayLength = 0 } }
}
