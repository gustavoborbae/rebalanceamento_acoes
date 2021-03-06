from django import forms
from django.forms import formset_factory
from django.forms import BaseFormSet

from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

from dal import autocomplete

import math 
import pandas as pd 
import numpy as np

from rebalanceamento import tickerData

def validate_file_size(value):
    filesize = value.size
    if filesize > 1000000:
        raise ValidationError("O tamanho limite para o envio é de 1MB")
    else:
        return value

class WalletDataForm(forms.Form):
    file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(['csv']), validate_file_size], 
        label='Arquivo CSV',
        widget=forms.FileInput(
            attrs={
                'class':'form-control-file border border-primary'
            }
        )
    )
 
    def clean_file(self):
        def processCSV(csvFile):
            df = pd.DataFrame([])
            try:
                data = pd.read_csv(csvFile,sep='\t')
                expectedColumns = [
                    'Ticker', 'Quantidade', 'Porcentagem alvo', 
                ]
                
                expectedColumnsInside = set(
                    expectedColumns).intersection(set(data.columns),
                )
                expectedColumnsInside = set(expectedColumns) == expectedColumnsInside

                def remove_fraction(ticker):
                    if ticker[-1] == 'F':
                        ticker = ticker[:-1]
                    return ticker
                data['Ticker'] = data['Ticker'].apply(remove_fraction)

                tickerRegex = '^[\dA-Z]{4}([345678]|11|12|13)$'
                if expectedColumnsInside \
                    and all(data['Quantidade'] >= 0) \
                    and all(data['Ticker'].str.contains(
                        tickerRegex, regex=True)):
                            data = data[['Ticker', 'Quantidade', 'Porcentagem alvo']]
                            data['Quantidade'] = data['Quantidade'].astype(int) 
                            data['Porcentagem alvo'] = data['Porcentagem alvo'].astype(float) 
                            df = data
                else:
                    raise Exception('Unexpected data')
            except Exception as e:
                # raise e
                pass
            return df

        df = processCSV(self.cleaned_data['file'])
        if df.empty:
            self.add_error(
                'file',
                'Conteúdo do arquivo não possui a formatação esperada'
            )
        return df

class CapitalForm(forms.Form):
    capital = forms.FloatField(
        label='Aporte', 
        required=True,
        min_value=0.01,
        widget=forms.NumberInput(
            attrs={
                'class':'form-control border border-primary'
            }
        )
    )
    def clean_capital(self):
        capital = self.cleaned_data['capital']
        return round(capital, 2)

class WalletPlanningForm(forms.Form):
    ticker = autocomplete.Select2ListChoiceField(
        choice_list=tickerData.getTickerList,
        widget=autocomplete.ListSelect2(
            url='stock-autocomplete',
            attrs={
                'class':'form-control p-0 m-0 border border-primary',
                'data-minimum-input-length': 3
            }
        )
    )
    quantity = forms.FloatField(
        required=True, label='Quantidade',
        min_value=0,
        initial=0,
        widget=forms.NumberInput(
            attrs={
                'class':'form-control form-control-sm border border-primary',
                'step': '1'
            }
        )
    )
    percent = forms.FloatField(
        label='Porcentagem',
        required=False, 
        min_value=0.00,
        widget=forms.NumberInput(
            attrs={
                'class':'form-control form-control-sm border border-primary',
                'step': '0.01'
            }
        )
    )
    
    def clean_ticker(self):
        ticker = self.cleaned_data['ticker']
        if ticker not in tickerData.getTickerList():
            self.add_error(
                'ticker',
                'Ticker inválido'
            )
        else:
            data = tickerData.getTickerInfo(ticker)
            if data:
                ticker = data  
            else:
                self.add_error(
                    'ticker',
                    'Ticker possui informações incompletas'
                )
        return ticker

class WalletPlanningFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
             return 
        notFilled = []
        percentTotal = 0
        for form in self.forms:
            percentAux = form.cleaned_data.get('percent')
            if percentAux:
                percentTotal += percentAux
            else: # mark for filling
                notFilled.append(form.cleaned_data)
        
        if round(percentTotal, 2) > 100:
            self.forms[0].add_error(
                'percent',
                f'Porcentagens não somam 100%. Soma calculada : {percentTotal:.2f}%'
            )
        else:
            if notFilled:
                percentLeft = 100 - percentTotal
                percentLeft = math.floor(100 * percentLeft / len(notFilled))/100.0 
                for form in notFilled:
                    form['percent'] = percentLeft
            elif round(percentTotal, 2) != 100:
                self.forms[0].add_error(
                'percent',
                f'Porcentagens não somam 100%. Soma calculada : {percentTotal:.2f}%'
            )
    
def createWalletPlanningForm(df=None):
    WalletFormSet = formset_factory(
        WalletPlanningForm,
        formset=WalletPlanningFormSet, extra=0, 
        min_num=1, validate_min=True
    )  
    formset = WalletFormSet
    if df is not None:
        nTickers = df.shape[0]
        initialData = [{ 
                'ticker': df['Ticker'].iloc[i],
                'quantity': df['Quantidade'].iloc[i],
                'percent': df['Porcentagem alvo'].iloc[i],
            } \
            for i in range(nTickers)
        ]
        formset = WalletFormSet(initial=initialData)
    return formset