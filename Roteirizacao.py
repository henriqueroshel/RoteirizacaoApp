# -*- coding: latin-1 -*-
"""
Roteirizacao.py
author: Henrique Roschel

O presente arquivo apresenta funcoes para gerar 
tabelas de roteirização rodoviaria entre cidades.
Os dados são acessados no website https://www.mapeia.com.br/
"""

import pandas as pd
import numpy as np

#from kivy.clock import Clock
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Variavel global com a base de dados a ser acessada e completada
DB_filename = 'DB_ParesOD_roteirizados.csv'

# Nomes das colunas no dataframe de entrada
Orig_COL = 'cidade_orig'
ufOrig_COL = 'uf_orig'
Dest_COL = 'cidade_dest'
ufDest_COL = 'uf_dest'

def DRIVER():
    # Definicao do selenium.webdriver utilizado nas queries
    options = webdriver.ChromeOptions()
    #options.add_argument('--headless')
    #options.add_argument('--no-sandbox')
    #options.add_argument('--disable-dev-shm-usage')
    #options.add_argument('--ignore-certificate-errors')
    d = webdriver.Chrome('chromedriver',options=options)
    return d

def get_estado(uf):
    # Converte um determinado valor de UF para o nome do respectivo Estado
    uf_estados = {
        "AC":"Acre", "AL":"Alagoas", "AP":"Amapá", "AM":"Amazonas", "BA":"Bahia", 
        "CE":"Ceará", "ES":"Espírito Santo", "GO":"Goiás", "MA":"Maranhão", 
        "MT":"Mato Grosso", "MS":"Mato Grosso do Sul", "MG":"Minas Gerais", 
        "PA":"Pará", "PB":"Paraíba", "PR":"Paraná", "PE":"Pernambuco", 
        "PI":"Piauí", "RJ":"Rio de Janeiro", "RN":"Rio Grande do Norte", 
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
    Concatena os dfs gerados em um só e salva na base de dados utilizada

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

def roteirizacao(df_paresOD):
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

    origens = df_paresOD[[Orig_COL, ufOrig_COL]].drop_duplicates().to_numpy()
    destinos = df_paresOD[[Dest_COL, ufDest_COL]].drop_duplicates().to_numpy()

    df_paresOD['Par_OD'] =  df_paresOD[Orig_COL] +' '+ df_paresOD[ufOrig_COL] +' '
    df_paresOD['Par_OD'] += df_paresOD[Dest_COL] +' '+ df_paresOD[ufDest_COL]
    
    # carrega os trajetos ja buscados
    BASE_DADOS = pd.read_csv(DB_filename, encoding='latin-1', delimiter=';', decimal=',', index_col=None)  
    # Lista com dfs a serem concatenados
    dfs = [ BASE_DADOS ]

    # Variaveis auxiliares para mapear a execucao
    cont=0                      # contador
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
            aux = df_paresOD[ (df_paresOD[Orig_COL]==orig_nome) & (df_paresOD[ufOrig_COL]==orig_uf) ]
            dict_paresOD[ tuple(origem) ] = aux[[ Dest_COL,ufDest_COL ]].to_numpy()

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
            aux = df_paresOD[ (df_paresOD['cidade_destino']==dest_nome) & (df_paresOD['uf_destino']==dest_uf) ]
            dict_paresOD[ tuple(destino) ] = aux[[ 'cidade_origem','uf_origem' ]].to_numpy()

        coluna_maior = 'Origem'
        coluna_menor = 'Destino'
        input_maior_el = driver.find_elements(By.ID, "origin")[0]
        input_menor_el = driver.find_element(By.ID, "destination")
        dropdown_maior_id = 'ui-id-1'
        dropdown_menor_id = 'ui-id-2'

        # Adaptacao da funcao de geracao de uma identidade única para o parOD
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

            if parOD not in BASE_DADOS.Par_OD.to_list():
                # Apenas calcula a rota se o par OD nao estiver na base de dados
                continue

            #inicio = time.time()
            try:
                cont+=1
    
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
        'Municipio Origem':Orig_COL, 'UF Origem':ufOrig_COL,
        'Municipio Terminal':Dest_COL,'UF Terminal':ufDest_COL
    })
    
    BASE_DADOS = pd.read_csv(DB_filename, encoding='latin-1', delimiter=';', decimal=',', index_col=None)
    #BASE_DADOS = pd.read_excel(DB_filename.replace('csv','xlsx'), index_col=None)


    newdf = roteirizacao(df)
    print(f'\n{df} \n\n{newdf}')