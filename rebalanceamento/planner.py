"""
Functions for creating a investing plan

"""

def computePlan(planDf,capital):
    """
    Rebalacing and investing
    Does rebalancing using a greedy approach
    That minimizes the distance 
        between the planned and actual %
    """
    df = planDf.copy()

    waitFor = None
    df['QuantidadeParaComprar'] = 0
    nonAllocatedCapital = capital
    
    df['Valor'] = df['Preço'] * df['Quantidade']
    df['PorcentagemAtual'] = \
        df['Valor'] * 100 / df['Valor'].sum()
    df['distance'] = \
        df['PorcentagemAlvo'] - df['PorcentagemAtual']
    
    df.sort_values(
        ['distance','PVP'], 
        ascending=[False, True], 
        inplace=True
    )
    
    for _,row in df.iterrows():
        targetValue = \
            (df['Valor'].sum() + capital) \
            * row['PorcentagemAlvo'] / 100
        targetValue = \
            round(targetValue, 2)

        if row['Valor'] < targetValue:   
            valueToAdd = targetValue - row['Valor']
            quant = valueToAdd // row['Preço'] 
            if row['Preço'] > nonAllocatedCapital \
                or nonAllocatedCapital < valueToAdd:
                    # rebalancing not possible
                    # buy as much as possible
                    waitFor = row['Ticker'] 
                    quant = nonAllocatedCapital // row['Preço']        
            nonAllocatedCapital -= row['Preço'] * quant
            df.loc[row.name,'QuantidadeParaComprar'] += quant
        if waitFor:          
            break
    if not waitFor:
        waitForAux = None
        # rebalancing done without problems
        # invest the remaining capital
        
        totalQuant = df['Quantidade'] + df['QuantidadeParaComprar']
        totalValue = totalQuant * df['Preço']
        df['ValorPlanejado'] = \
            totalValue \
            + df['PorcentagemAlvo'] * nonAllocatedCapital
        df['PorcentagemPlanejada'] = \
            df['ValorPlanejado'] * 100 \
            / df['ValorPlanejado'].sum()
        df['distancePlanned'] = \
            df['PorcentagemAlvo'] - df['PorcentagemPlanejada']
        df.sort_values(
            ['distancePlanned', 'PVP'],
            ascending=[False, True], 
            inplace=True
        )
        
        for _,row in df.iterrows():
            distanceNow = abs(
                row['PorcentagemAlvo'] \
                - row['PorcentagemPlanejada']
            )
            
            quant = 0
            while True:
                quant += 1





                totalValue = row['ValorPlanejado'] + quant * row['Preço']
                percent = totalValue * 100 \
                    / df['ValorPlanejado'].sum()
                distanceBuyMore = abs(row['PorcentagemAlvo'] - percent)
                if distanceBuyMore <= distanceNow:
                    if row['Preço'] * quant <= nonAllocatedCapital:
                         continue
                    else:
                        # not enough capital
                        quant -= 1
                        waitForAux = row['Ticker']
                        break
                else:
                    # distance can't be minimized
                    quant -= 1
                    break
            if quant == 0 and row['Preço']  <= nonAllocatedCapital: 
                # buy at least one
                quant = 1
            nonAllocatedCapital -= row['Preço'] * quant
            df.loc[row.name,'QuantidadeParaComprar'] += quant
            if waitForAux:
                break
    
    df['ValorPlanejado'] = \
        (df['Quantidade'] + df['QuantidadeParaComprar']) \
        * df['Preço']
    df['PorcentagemPlanejada'] = \
        df['ValorPlanejado'] * 100 \
        / df['ValorPlanejado'].sum()
    df['distancePlanned'] = \
        df['PorcentagemAlvo'] \
        - df['PorcentagemPlanejada']

    if nonAllocatedCapital != capital:
        waitFor = None
    return df, nonAllocatedCapital, waitFor