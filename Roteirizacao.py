# -*- coding: latin-1 -*-
"""
Roteirizacao.py
author: Henrique Roschel

O presente arquivo apresenta funcoes para gerar 
tabelas de roteirização rodoviaria entre cidades.
Os dados sao acessados no website https://www.mapeia.com.br/
"""

#from logging import root
import pandas as pd
import numpy as np
import tkinter as tk
import time

from tkinter import ttk
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Variavel global com a base de dados a ser acessada e completada
DB_filename = 'DB_ParesOD_roteirizados.csv'

# Nomes das colunas no dataframe de entrada
ORIG_COL = 'cidade_orig'
UFORIG_COL = 'uf_orig'
DEST_COL = 'cidade_dest'
UFDEST_COL = 'uf_dest'

def DRIVER():
    # Definicao do selenium.webdriver utilizado nas queries
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--ignore-certificate-errors')
    d = webdriver.Chrome('chromedriver',options=options)
    return d

def get_estado(uf):
    # Converte um determinado valor de UF para o nome do respectivo Estado
    uf_estados = {
        "AC":"Acre", "AL":"Alagoas", "AP":"Amapá", "AM":"Amazonas", "BA":"Bahia", 
        "CE":"Ceará", "ES":"Espí­rito Santo", "GO":"Goiás", "MA":"Maranhão", 
        "MT":"Mato Grosso", "MS":"Mato Grosso do Sul", "MG":"Minas Gerais", 
        "PA":"Pará", "PB":"Paraí­ba", "PR":"Paraná", "PE":"Pernambuco", 
        "PI":"Piauí­", "RJ":"Rio de Janeiro", "RN":"Rio Grande do Norte", 
        "RS":"Rio Grande do Sul", "RO":"Rondônia", "RR":"Roraima", 
        "SC":"Santa Catarina", "SP":"São Paulo", "SE":"Sergipe", 
        "TO":"Tocantins", "DF":"Distrito Federal" 
    }
    return uf_estados[uf]

def join_parOD(origem, origemUF, destino, destinoUF):
    # Dado os nome dos municipios e suas UF, gera uma
    # string única para identificá-los, separada por espaços
    return " ".join([origem, origemUF, destino, destinoUF])

def save(dfs, filename = DB_filename):
    """
    Concatena os dfs gerados em um so e salva na base de dados utilizada

    Parameters
    dfs : list of DataFrames
        dfs a serem reunidos e salvos em um arquivo
    filename : str
        nome do arquivo a ser salvo com extensão .csv

    Returns
    df : lista de um df apos salvar as queries
    """
    df = pd.concat(dfs).drop_duplicates()
    df = df[['Origem', 'OrigemUF', 'Destino', 'DestinoUF', 'Par_OD', 'Rodo', 'Pedagio']]
    df = df.sort_values(['OrigemUF', 'Origem', 'DestinoUF', 'Destino']).reset_index(drop=True)
    df.to_csv(filename, encoding='latin-1', index=False, sep=';', decimal=',')

    return [ df ]

class tk_window():
    # Define a janela tkinter com a barra de progresso
    def __init__(self, n_pbar):
        PRIMARY_COLOR = '#dcdcaf'
        SECONDARY_COLOR = '#022333'
        
        self.window = tk.Tk()
        self.window.title = 'Roteirizacao'
        self.window.eval('tk::PlaceWindow . center')
        self.window['background']=PRIMARY_COLOR
        self.window.geometry("300x150+400+200")

        self.pbar = ttk.Progressbar(self.window, orient='horizontal',
                                    length=200, maximum=n_pbar)
        self.pbar.grid(row=0, column=0, padx=10, pady=10)
        self.percent = tk.StringVar()
        self.text = tk.StringVar()

        self.percentLabel = tk.Label(self.window, textvariable=self.percent, 
                            bg=PRIMARY_COLOR, fg=SECONDARY_COLOR, font=('Helvetica 14 bold'))
        self.percentLabel.grid(row=0, column=1, padx=10, pady=10)
        self.taskLabel = tk.Label(self.window, textvariable=self.text, 
                            bg=PRIMARY_COLOR, fg=SECONDARY_COLOR, font=('Helvetica 14 bold'))
        self.taskLabel.grid(row=1, column=0, columnspan=2, rowspan=1, padx=10, pady=10)

    def update_idletasks(self):
        self.window.update_idletasks()
    def destroy(self):
        self.window.destroy()



def roteirizacao(df_paresOD, window=None):
    """
    Parameters
    ----------
    df_paresOD : pd.DataFrame
        DataFrame com os pares OD a serem buscados;
        contem as colunas cidOrig_COL, ufOrig_COL,
        cidDest_COL, udDest_COL

    Returns
    -------
        df com distâncias e valores de pedagio entre cidades cruzando as
        listas origem e destino
    """

    origens = df_paresOD[[ORIG_COL, UFORIG_COL]].drop_duplicates().to_numpy()
    destinos = df_paresOD[[DEST_COL, UFDEST_COL]].drop_duplicates().to_numpy()

    df_paresOD['Par_OD'] =  df_paresOD[ORIG_COL] +' '+ df_paresOD[UFORIG_COL] +' '
    df_paresOD['Par_OD'] += df_paresOD[DEST_COL] +' '+ df_paresOD[UFDEST_COL]
    
    # carrega os trajetos ja buscados
    BASE_DADOS = pd.read_csv(DB_filename, encoding='latin-1', delimiter=';', decimal=',', index_col=None)  
    # Lista com dfs a serem concatenados
    dfs = [ BASE_DADOS ]

    # Variaveis auxiliares para mapear a execucao
    cont=0                      # contador
    n_pares = len(df_paresOD)   # numero de pares buscados
    tempo_qry=[]                # armazenamento dos tempos de cada iteracao
    qry_mean = "0.00sec/qry"    # string para o tempo medio de busca

    driver = DRIVER()
    wait = WebDriverWait(driver, 10)
    home_page = "https://www.mapeia.com.br/"
    driver.get(home_page)
    wait.until( EC.visibility_of_element_located((By.XPATH, '/html/body/div[1]/div/a')) ).click()

    '''
    Para otimizacao do codigo comparam-se os numeros de origens e destinos
    de forma que aquele com menos valores unicos fica no loop externo
    e o outro no loop interno.
    Para isso, define-se um dicionario onde as chaves serao as cidades do 
    loop externo, e os valores serao uma lista com as cidades que se deseja
    roteirizar (loop interno)
    '''
    dict_paresOD = {}
    paresOD_ids = []
    if len(origens) <= len(destinos):
        for origem in origens:
            orig_nome, orig_uf = origem
            # Filtra os pares desejados apenas para uma cidade origem 
            aux = df_paresOD[ (df_paresOD[ORIG_COL]==orig_nome) & (df_paresOD[UFORIG_COL]==orig_uf) ]
            dict_paresOD[ tuple(origem) ] = aux[[ DEST_COL,UFDEST_COL ]].to_numpy()

        coluna_maior = 'Destino'
        coluna_menor = 'Origem'
        input_maior_el = driver.find_element(By.ID, "destination")
        input_menor_el = driver.find_elements(By.ID, "origin")[0]
        dropdown_maior_id = 'ui-id-2'
        dropdown_menor_id = 'ui-id-1'

        # Adaptacao da funcao de geracao de uma identidade única para o parOD
        parOD_id = lambda A_nome, A_uf, B_nome, B_uf : join_parOD(A_nome, A_uf, B_nome, B_uf)

    else: #len(origens) > len(destinos)
        for destino in destinos:
            dest_nome, dest_uf = destino
            # Filtra os pares desejados apenas para uma cidade destino
            aux = df_paresOD[ (df_paresOD[DEST_COL]==dest_nome) & (df_paresOD[UFDEST_COL]==dest_uf) ]
            dict_paresOD[ tuple(destino) ] = aux[[ ORIG_COL,UFORIG_COL ]].to_numpy()

        coluna_maior = 'Origem'
        coluna_menor = 'Destino'
        input_maior_el = driver.find_elements(By.ID, "origin")[0]
        input_menor_el = driver.find_element(By.ID, "destination")
        dropdown_maior_id = 'ui-id-1'
        dropdown_menor_id = 'ui-id-2'

        # Adaptacao da funcao de geracao de uma identidade unica para o parOD
        parOD_id = lambda A_nome, A_uf, B_nome, B_uf : join_parOD(B_nome, B_uf, A_nome, A_uf)

    # Elemento botao para calculo da rota    
    calc_el = driver.find_element(By.ID, "calc")
    
    # Loop externo
    for cidadeA in dict_paresOD:
        cidadeA_nome, cidadeA_uf = cidadeA
        
        # Preenche a query da cidade A no input da lista menor
        cidadeA_qry = cidadeA_nome + ' ' + get_estado( cidadeA_uf )
        input_menor_el.send_keys(Keys.CONTROL + "a" + Keys.DELETE)
        input_menor_el.send_keys(cidadeA_qry)
            
        # Aguarda carregar a lista suspensa e seleciona o primeiro item
        wait.until( EC.visibility_of_element_located((By.ID, dropdown_menor_id)) )
        dropdown_menor_el = driver.find_element(By.ID, dropdown_menor_id)
        dropdown_menor_el = dropdown_menor_el.find_elements(By.CLASS_NAME, 'ui-menu-item')
        dropdown_menor_el[0].click()
    
        # Loop interno     
        for i, cidadeB in enumerate( dict_paresOD[ cidadeA ] ):
            cidadeB_nome, cidadeB_uf = cidadeB
            
            parOD = parOD_id(cidadeA_nome, cidadeA_uf, cidadeB_nome, cidadeB_uf)
            paresOD_ids.append(parOD)

            if parOD in BASE_DADOS.Par_OD.to_list():
                # Apenas calcula a rota se o par OD nao estiver na base de dados
                continue

            #inicio = time.time()
            try:
                # Preenche a query da cidade B no input da lista maior
                cidadeB_qry = cidadeB_nome + ' ' + get_estado( cidadeB_uf )
                input_maior_el.send_keys(Keys.CONTROL + "a" + Keys.DELETE)
                input_maior_el.send_keys(cidadeB_qry)
                
                # Aguarda carregar a lista suspensa e seleciona o primeiro item
                wait.until( EC.visibility_of_element_located((By.ID, dropdown_maior_id)) )
                dropdown_maior_el = driver.find_element(By.ID, dropdown_maior_id)
                dropdown_maior_el = dropdown_maior_el.find_elements(By.CLASS_NAME, 'ui-menu-item')
                dropdown_maior_el[0].click()

                # Calcula o trajeto com distancia e pedagio
                calc_el.click()
                road_el = driver.find_element(By.ID, "dist-value")
                toll_el = driver.find_element(By.ID, "toll-value")

                # Aguarda elemementos aparecerem
                cont_tentativas = 0
                wait2 = WebDriverWait(driver, 3)
                while (road_el.text,toll_el.text)==('','') and cont_tentativas<5:
                    cont_tentativas+=1
                    try:
                        road_el = wait2.until(EC.visibility_of_element_located((By.ID, "dist-value")))
                        toll_el = wait2.until(EC.visibility_of_element_located((By.ID, "toll-value")))

                    except TimeoutException:
                        # Calcula novamente caso demore a carregar
                        calc_el.click()
                    
                # Extrai o texto dos elementos de distancia e pedagio
                Rodo = int(road_el.text[:-3])
                Toll = float(toll_el.text[2:].replace(',','.'))
                
                # Calcula media dos tempos de query para display em pbar
                #tempo_qry.append(time.time() - inicio)
                #qry_mean = '{:.2f}sec/qry'.format(np.mean(tempo_qry))
                
                # Reune dados da query em um df
                qry_df = pd.DataFrame(
                    data = [[cidadeA_nome,cidadeA_uf,
                             cidadeB_nome,cidadeB_uf,
                             Rodo,Toll,parOD]],
                    columns=[coluna_menor,coluna_menor+'UF',
                             coluna_maior,coluna_maior+'UF',
                            'Rodo','Pedagio','Par_OD']
                    )                
                dfs.append( qry_df )
                
            except Exception as e:
                qry_df = pd.DataFrame(
                    data = [[cidadeA_nome,cidadeA_uf,
                             cidadeB_nome,cidadeB_uf,
                             np.nan,np.nan,parOD]],
                    columns=[coluna_menor,coluna_menor+'UF',
                             coluna_maior,coluna_maior+'UF',
                            'Rodo','Pedagio','Par_OD']
                )
                dfs.append( qry_df )
            
            if window:
                time.sleep(0.01)
                cont+=1
                window.pbar['value'] = cont
                window.percent.set(str(int((cont/n_pares)*100))+"%")
                window.text.set(str(cont)+"/"+str(n_pares)+" pares OD\nroteirizados")
                window.update_idletasks()

            if cont % 10 == 0:
                # A cada 10 queries salva o progresso
                dfs = save(dfs)
                
        # A cada municipio do loop externo salva o progresso
        if len(dfs)==1:
            # Espera caso nenhuma query tenha sido feito
            # Nao precisa salvar
            pass
        else:
            dfs = save(dfs)

    # Apos calcular as roteirizacoes, reune os valores para os pares solicitados
    df = dfs[0][['Par_OD', 'Rodo', 'Pedagio']]
    df = df[ df.Par_OD.isin(paresOD_ids) ]
    df.set_index('Par_OD', inplace=True)

    df = df_paresOD.join(df, rsuffix='out', on='Par_OD')
    df.reset_index(drop=True, inplace=True)
    
    df_paresOD.drop(columns=['Par_OD'], inplace=True)
    df.drop(columns=['Par_OD'], inplace=True)

    driver.quit()
    return df

if __name__ == '__main__':
    df = pd.read_excel('Pares Teste.xlsx', index_col=None)
    #df = pd.read_csv('Pares Teste.csv', encoding='latin-1', delimiter=';', decimal=',', index_col=None)
    df = df.rename(columns={
        'Municipio Origem':ORIG_COL, 'UF Origem':UFORIG_COL,
        'Municipio Terminal':DEST_COL,'UF Terminal':UFDEST_COL
    })
    
    BASE_DADOS = pd.read_csv(DB_filename, encoding='latin-1', delimiter=';', decimal=',', index_col=None)
    #BASE_DADOS = pd.read_excel(DB_filename.replace('csv','xlsx'), index_col=None)

    window = tk_window(len(df))
    
    newdf = roteirizacao(df, window=window)
    
    window.window.mainloop()
    #print(f'\n{df} \n\n{newdf}')