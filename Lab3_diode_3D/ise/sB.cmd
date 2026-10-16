Title "3D Sharp Diode"

Definitions
{
    Refinement "Mesh1"
    {
      MaxElementSize = (0.25, 0.25, 0.1)
      MinElementSize = (0.05, 0.05, 0.02)
      RefineFunction = MaxTransDiff(Variable = "DopingConcentration", Value = 1)
    }
    Refinement "Mesh2"
    {
      MaxElementSize = (0.1, 0.1, 0.04)
      MinElementSize = (0.02, 0.02, 0.01)
    }
    Refinement "MeshEdge"
    {
      MaxElementSize = (0.04, 0.08, 0.025)
      MinElementSize = (0.01, 0.02, 0.006)
    }
    Constant "BW"  { Species = "BoronActiveConcentration"   Value = 1.4e+17 }
    Constant "AsW" { Species = "ArsenicActiveConcentration" Value = 1.0e+17 }
}

Placements
{
    Refinement "Mesh1" { Reference = "Mesh1" }
    Refinement "Mesh2" { Reference = "Mesh2"
      RefineWindow = cuboid [(0,0.7,0.64) (1,2.3,0.8)] }
    Refinement "MeshEdge" { Reference = "MeshEdge"
      RefineWindow = cuboid [(0.38,0.85,0.6) (0.62,2.15,0.8)] }
    Constant "BW"  { Reference = "BW"
      EvaluateWindow { Element = cuboid [(0,0,0.4) (1,3,0.8)] DecayLength = 0 } }
    Constant "AsW" { Reference = "AsW"
      EvaluateWindow { Element = cuboid [(0,0,0) (1,3,0.4)] DecayLength = 0 } }
}
