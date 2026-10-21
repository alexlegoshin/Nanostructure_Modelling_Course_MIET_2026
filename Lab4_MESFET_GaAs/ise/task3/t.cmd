Title "Transistor"

Definitions {
    Refinement "Mesh"
    {
      MaxElementSize = (1.0, 0.5)
      MinElementSize = (0.1, 0.01)
      RefineFunction = MaxTransDiff(Variable="DopingConcentration",Value=1)
    }
    Refinement "Mesh_1"
    {
      MaxElementSize = (0.5, 0.05)
      MinElementSize = (0.01, 0.001)
      RefineFunction = MaxTransDiff(Variable="DopingConcentration",Value=1)
    }
    Refinement "M3" { MaxElementSize = (0.4 0.0006) MinElementSize = (0.02 0.0006) }
    Refinement "M4" { MaxElementSize = (0.4 0.004)  MinElementSize = (0.02 0.004) }
    Refinement "M5" { MaxElementSize = (0.4 0.001)  MinElementSize = (0.02 0.0005) }
    Refinement "M6" { MaxElementSize = (0.4 0.0003) MinElementSize = (0.02 0.0001) }
    Refinement "M7" { MaxElementSize = (0.4 0.02)   MinElementSize = (0.02 0.01) }

    Constant "P10"
    {
      Species = "PhosphorusActiveConcentration"
      Value = 1.00e+18
    }
    Constant "P11"
    {
      Species = "PhosphorusActiveConcentration"
      Value = 1.00e+18
    }
    Constant "P1"
    {
      Species = "PhosphorusActiveConcentration"
      Value = 1.00e+14
    }
    Constant "P2"
    {
      Species = "PhosphorusActiveConcentration"
      Value = 1.00e+14
    }
    Constant "P3"
    {
      Species = "PhosphorusActiveConcentration"
      Value = 7.00e+17
    }
    Constant "P5"
    {
      Species = "PhosphorusActiveConcentration"
      Value = 1.50e+18
    }
    Constant "P6"
    {
      Species = "PhosphorusActiveConcentration"
      Value = 1.00e+14
    }
    Constant "P7"
    {
      Species = "PhosphorusActiveConcentration"
      Value = 4.00e+17
    }
    Constant "P8"
    {
      Species = "PhosphorusActiveConcentration"
      Value = 1.00e+18
    }
    Constant "P4"
    {
      Species = "PhosphorusActiveConcentration"
      Value = 3.00e+17
    }
}

Placements {
    Refinement "Default Region" { Reference = "Mesh" }
    Refinement "M_Mesh_1" { Reference = "Mesh_1" RefineWindow = rectangle [(3, 0.0) (12, 0.75)] }
    Refinement "M_S7" { Reference = "M7" RefineWindow = rectangle [( 5 0.1 ) , ( 10 0.3 )] }
    Refinement "M_S6" { Reference = "M6" RefineWindow = rectangle [( 5 0.3 ) , ( 10 0.301 )] }
    Refinement "M_S5" { Reference = "M5" RefineWindow = rectangle [( 5 0.301 ) , ( 10 0.304 )] }
    Refinement "M_S4" { Reference = "M4" RefineWindow = rectangle [( 5 0.304 ) , ( 10 0.324 )] }
    Refinement "M_S3" { Reference = "M3" RefineWindow = rectangle [( 5 0.324 ) , ( 10 0.33 )] }

    Constant "P_S10"
    {
      Reference = "P10"
      EvaluateWindow
      {
        Element = rectangle [( 0 0 ) , ( 5 1.05 )]
        DecayLength = 0
      }
      Replace
    }
    Constant "P_S11"
    {
      Reference = "P11"
      EvaluateWindow
      {
        Element = rectangle [( 10 0 ) , ( 15 1.05 )]
        DecayLength = 0
      }
      Replace
    }
    Constant "P_S8"
    {
      Reference = "P8"
      EvaluateWindow
      {
        Element = rectangle [( 5 0 ) , ( 10 0.1 )]
        DecayLength = 0
      }
      Replace
    }
    Constant "P_S7"
    {
      Reference = "P7"
      EvaluateWindow
      {
        Element = rectangle [( 5 0.1 ) , ( 10 0.3 )]
        DecayLength = 0
      }
      Replace
    }
    Constant "P_S6"
    {
      Reference = "P6"
      EvaluateWindow
      {
        Element = rectangle [( 5 0.3 ) , ( 10 0.301 )]
        DecayLength = 0
      }
      Replace
    }
    Constant "P_S5"
    {
      Reference = "P5"
      EvaluateWindow
      {
        Element = rectangle [( 5 0.301 ) , ( 10 0.304 )]
        DecayLength = 0
      }
      Replace
    }
    Constant "P_S4"
    {
      Reference = "P4"
      EvaluateWindow
      {
        Element = rectangle [( 5 0.304 ) , ( 10 0.324 )]
        DecayLength = 0
      }
      Replace
    }
    Constant "P_S3"
    {
      Reference = "P3"
      EvaluateWindow
      {
        Element = rectangle [( 5 0.324 ) , ( 10 0.33 )]
        DecayLength = 0
      }
      Replace
    }
    Constant "P_S2"
    {
      Reference = "P2"
      EvaluateWindow
      {
        Element = rectangle [( 5 0.33 ) , ( 10 1.05 )]
        DecayLength = 0
      }
      Replace
    }
    Constant "P_S1"
    {
      Reference = "P1"
      EvaluateWindow
      {
        Element = rectangle [( 0 1.05 ) , ( 15 2.05 )]
        DecayLength = 0
      }
      Replace
    }
}
