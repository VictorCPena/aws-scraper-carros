import time
import random
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

def get_driver():
    """Configura o Chrome de forma híbrida (Local ou Serverless)"""
    chrome_options = Options()
    
    # Se quiser ver o navegador abrindo, mude para False
    chrome_options.add_argument('--headless') 
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # Instala o driver automaticamente (Mágica para rodar local)
    servico = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=servico, options=chrome_options)
    return driver

def executar_scraping(qtd_paginas=1):
    driver = get_driver()
    dados = []
    
    print(f"--- Iniciando Scraping de {qtd_paginas} páginas ---")
    
    try:
        # URL EXMEPLO (ICarros)
        base_url = "https://www.icarros.com.br/ache/listaanuncios.jsp?pag={}&ord=35"
        
        for i in range(1, qtd_paginas + 1):
            url = base_url.format(i)
            print(f"Lendo URL: {url}")
            driver.get(url)
            time.sleep(2) # Espera carregar
            
            # --- SUA LÓGICA DE COLETA AQUI ---
            # Exemplo genérico pegando qualquer card
            elementos = driver.find_elements(By.CLASS_NAME, 'card-offer__main-content')
            
            for elem in elementos:
                try:
                    texto = elem.text.split('\n')
                    if len(texto) > 2:
                        dados.append({
                            'titulo': texto[0],
                            'preco': texto[2],
                            'data_coleta': datetime.now().strftime('%Y-%m-%d')
                        })
                except:
                    pass
            
            # Scroll simples
            body = driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(1)
            
    except Exception as e:
        print(f"Erro durante scraping: {e}")
    finally:
        driver.quit()
        
    return pd.DataFrame(dados)