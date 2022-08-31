# -*- coding: latin-1 -*-

from base64 import encode
from email.policy import default
import re
import sys
import os
import kivy
import tkinter as tk
import pandas as pd

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ObjectProperty, StringProperty, DictProperty, NumericProperty
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.clock import Clock

from tkinter import filedialog as fd

sys.path.append(os.path.abspath("./"))
from Roteirizacao import *

class MessagePopup(Popup):
    text = StringProperty('')

class FinalPopup(Popup):
    text = StringProperty('')

class AppLayout(Widget):
    input_df = pd.DataFrame()
    output_df = pd.DataFrame()

    colunas = DictProperty(defaultvalue={ 
        'origem':ORIG_COL, 'origemUF':UFORIG_COL,
        'destino':DEST_COL, 'destinoUF':UFDEST_COL
    })
    
    cont = StringProperty('0')
    total = StringProperty('0')

    def getInputFileButton(self):

        # Abre caixa de dialogo para selecao do arquivo
        filename = fd.askopenfilename(filetypes =[
            ('Pasta de trabalho do Excel', '.xls .xlsx .xlsm'), 
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
        popup = MessagePopup()
        
        if self.ids.inputfile.text == '':
            label = 'Por favor selecione um arquivo.'
            popup.text = label
            popup.open()
            return        
        
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
        
        if self.ids.outputfolder.text == '':
            self.ids.outputfolder.text = os.path.dirname(filename)
        if self.ids.outputfile.text == '':
            basename = ''.join(os.path.basename(filename).split('.')[:-1])
            self.ids.outputfile.text = f'{basename}_output'

        return input_df

    def getOutputFolderButton(self):
        # Abre caixa de dialogo para selecao do arquivo
        foldername = fd.askdirectory()
        
        if foldername not in [None,'']:
            self.ids.outputfolder.text = foldername

    def saveOutputFile(self):
        outputfilepath = f'{self.ids.outputfolder.text}/{self.ids.outputfile.text}.xlsx'
        
        if self.output_df.empty:
            popup = MessagePopup()
            label = 'N\u00e3o foi poss\u00edvel salvar seu arquivo.\n'
            label+= 'Tabela vazia. Realize a roteiriza\u00e7\u00e3o novamente.'
            popup.text = label
            popup.open()
            return
        
        popup = FinalPopup()
        self.output_df.to_excel(outputfilepath)
        popup.text = "Arquivo salvo com sucesso."
        popup.open()
        

    def ROTEIRIZACAO(self):
        # Realiza a roteirizacao para o arquivo e colunas escolhidas
        
        popup = MessagePopup()
        if self.input_df.empty:
            popup.text = 'Por favor selecione seu arquivo e\nas colunas de entrada e tente novamente.'
            popup.open()
            return            
        
        popup.text = 'Aguarde.\nRoteiriza\u00e7\u00e3o em andamento.'
        popup.auto_dismiss = False
        popup.open()


        self.input_df.rename( columns={
            self.colunas['origem']    : ORIG_COL,
            self.colunas['origemUF']  : UFORIG_COL,
            self.colunas['destino']   : DEST_COL,
            self.colunas['destinoUF'] : UFDEST_COL,
        }, inplace=True )
        
        window = tk_window(len(self.input_df))       

        self.output_df = roteirizacao(self.input_df, window=window)

        window.update_idletasks()
        time.sleep(1)
        window.destroy()

        self.output_df.rename( columns={
            ORIG_COL   : self.colunas['origem'],
            UFORIG_COL : self.colunas['origemUF'],
            DEST_COL   : self.colunas['destino'],
            UFDEST_COL : self.colunas['destinoUF'],
        }, inplace=True )
        
        popup.text = 'Roteiriza\u00e7\u00e3o completa!\nSalve seu arquivo.'
        popup.auto_dismiss = True
    
    def resetApp(self):
        # Reseta todas as informacoes do app
        self.ids.inputfile.text = ''
        self.ids.outputfile.text = ''
        self.ids.outputfolder.text = ''
        input_df = pd.DataFrame()
        output_df = pd.DataFrame()

        dropdowns = [ self.ids.dropdown_orig, self.ids.dropdown_origUF, 
                      self.ids.dropdown_dest, self.ids.dropdown_destUF ]
        for dropdown in dropdowns:
            dropdown.values = []
            dropdown.text = ""

Window.size = (810, 490)
Window.minimum_width, Window.minimum_height = Window.size

# Designate Our .kv design file 
Builder.load_file('RoteirizaApp.kv')

class RoteirizacaoApp(App):

    def build(self):
        return AppLayout()


if __name__ == '__main__':
    RoteirizacaoApp().run()