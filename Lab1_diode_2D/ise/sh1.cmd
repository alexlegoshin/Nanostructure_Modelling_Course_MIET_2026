Title "Sharp Diode"

Definitions {
    Refinement "Mesh1"
    {
      MaxElementSize = (0.5 0.2)
      MinElementSize = (0.1 0.04)
      RefineFunction = MaxTransDiff(Variable = "DopingConcentration", Value = 1)
    }
    Refinement "Mesh2"
    {
      MaxElementSize = (0.2 0.08)
      MinElementSize = (0.01 0.004)
    }
    Constant "BW"  { Species = "BoronActiveConcentration"   Value = 1.4e+17 }
    Constant "AsW" { Species = "ArsenicActiveConcentration" Value = 1e+17 }
}

Placements {
    Refinement "Mesh1" { Reference = "Mesh1"
      RefineWindow = rectangle [( -1.5 -0.4 ) , ( 1.5 0.4 )] }
    Refinement "Mesh2" { Reference = "Mesh2"
      RefineWindow = rectangle [( -1.0 -0.4 ) , ( 1.0 -0.2 )] }
    Constant "BW"  { Reference = "BW"
      EvaluateWindow { Element = rectangle [( -1.5 -0.4 ) , ( 1.5 0 )] DecayLength = 0 } }
    Constant "AsW" { Reference = "AsW"
      EvaluateWindow { Element = rectangle [( -1.5 0 ) , ( 1.5 0.4 )] DecayLength = 0 } }
}
