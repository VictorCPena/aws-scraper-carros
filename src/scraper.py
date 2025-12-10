import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from storage import CloudStorage
import re

def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def limpar_dados(df):
    
    df['Preço'] = df['Preço'].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df['Preço'] = pd.to_numeric(df['Preço'], errors='coerce')

    df['KM Rodado'] = df['KM Rodado'].astype(str).str.replace('Km', '', regex=False).str.replace('.', '', regex=False)
    df['KM Rodado'] = pd.to_numeric(df['KM Rodado'], errors='coerce').fillna(0).astype(int)

    df[['Cidade', 'Estado']] = df['Local'].astype(str).str.split(', ', n=1, expand=True)
    
    df['Ano'] = df['Ano'].astype(str).str.split('/').str[0].astype(int)

    df['Transmissão'] = df['Descrição'].apply(
        lambda x: 'Automático' if 'aut' in str(x).lower() or 'at' in str(x).lower() else 'Manual'
    )
    
    return df

def executar_scraping(paginas=5):
    driver = configurar_driver()
    dados_brutos = []

    try:
        for pag in range(1, paginas + 1):
            url = f'https://www.icarros.com.br/ache/listaanuncios.jsp?pag={pag}&ord=35'
            driver.get(url)
            time.sleep(random.uniform(2, 4)) 

            body = driver.find_element(By.TAG_NAME, "body")
            for _ in range(3):
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.5)

            elementos = driver.find_elements(By.CLASS_NAME, 'card-offer__main-content')

            for elemento in elementos:
                try:
                    textos = elemento.text.split('\n')
                    if len(textos) >= 6:
                        dados_brutos.append({
                            'Título': textos[0],
                            'Descrição': textos[1],
                            'Preço': textos[2],
                            'Local': textos[4],
                            'Ano': textos[5],
                            'KM Rodado': textos[6]
                        })
                except Exception:
                    continue
            
            print(f"Página {pag}: {len(elementos)} itens.")

    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        driver.quit()

    if not dados_brutos:
        return

    df = pd.DataFrame(dados_brutos)
    df_limpo = limpar_dados(df)

    storage = CloudStorage()
    storage.salvar(df_limpo, 'carros_dados_limpos.csv')

if __name__ == "__main__":
    executar_scraping(paginas=2)