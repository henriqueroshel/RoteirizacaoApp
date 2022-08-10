# -*- coding: latin-1 -*-

from email.policy import default
import re
import sys
import os
import kivy
import tkinter as tk
import pandas as pd

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ObjectProperty, StringProperty, DictProperty, NumericProperty
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.clock import Clock

from tkinter import filedialog as fd

sys.path.append(os.path.abspath("./"))
from Roteirizacao import *

class AppLayout(Widget):
    input_df = pd.DataFrame()
    output_df = pd.DataFrame()

    colunas = DictProperty(defaultvalue={ 
        'origem':Orig_COL, 'origemUF':ufOrig_COL,
        'destino':Dest_COL, 'destinoUF':ufDest_COL
    })
    
    cont = StringProperty('0')
    total = StringProperty('0')

    def getInputFileButton(self):

        # Abre caixa de diálogo para selecao do arquivo
        filename = fd.askopenfilename(filetypes =[
            ('Planilhas Excel', '.xls .xlsx .xlsm'), 
            ('Arquivos CSV', '*.csv')
            ])
        if filename not in [None,'']:
            self.ids.inputfile.text = filename
        
        dropdowns = [ self.ids.dropdown_orig, self.ids.dropdown_origUF, 
                      self.ids.dropdown_dest, self.ids.dropdown_destUF ]
        for dropdown in dropdowns:
                dropdown.values = []
    
    def openInputFileButton(self):

        # Abre o arquivo selecionado numa tabela pandas
        filename = self.ids.inputfile.text
        if re.search('[.]csv$', filename):
            input_df = pd.read_csv( filename, encoding='latin-1',
                                    delimiter=';', decimal=',', index_col=None )
        elif re.search('[.]xls.?$', filename):
            input_df = pd.read_excel(filename, index_col=None)

        dropdowns = [ self.ids.dropdown_orig, self.ids.dropdown_origUF, 
                      self.ids.dropdown_dest, self.ids.dropdown_destUF ]
        cols = list(input_df.columns)
        for dropdown in dropdowns:
            dropdown.values = []
            
            if cols:
                dropdown.text = "Selecione"
                for coluna in cols:
                    dropdown.values.append(coluna)
        
        return input_df

    def ROTEIRIZACAO(self):
        self.input_df.rename( columns={
            self.colunas['origem']    : Orig_COL,
            self.colunas['origemUF']  : ufOrig_COL,
            self.colunas['destino']   : Dest_COL,
            self.colunas['destinoUF'] : ufDest_COL,
        }, inplace=True )
        
        self.output_df = roteirizacao(self.input_df) # pbar_screen=self)
        print(f'\n{ self.input_df} \n\n{self.output_df}')
        


Window.size = (810, 300)
Window.minimum_width, Window.minimum_height = Window.size

# Designate Our .kv design file 
Builder.load_file('RoteirizaApp.kv')

class RoteirizacaoApp(App):

    def build(self):
        return AppLayout()


if __name__ == '__main__':
    RoteirizacaoApp().run()