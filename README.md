Da extração web à previsão de preços com Machine Learning.

![Status](https://img.shields.io/badge/Status-Concluído-green)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![AWS](https://img.shields.io/badge/AWS-S3-orange)

## 📋 Sobre o Projeto

Este projeto tem como objetivo coletar, processar e modelar dados do mercado automotivo brasileiro para entender a precificação de veículos usados. 

A solução foi construída com uma arquitetura híbrida, capaz de rodar tanto em ambiente local quanto na nuvem (AWS), graças a uma camada de abstração de armazenamento.

**Principais Funcionalidades:**
* **Web Scraping Automatizado:** Coleta dados de portais de venda utilizando Selenium.
* **Armazenamento Híbrido:** Sistema inteligente que salva/lê dados localmente ou no AWS S3 dependendo do ambiente (`dev` vs `prod`).
* **Engenharia de Atributos:** Criação de features como `Potência do Motor`, `Idade` e `KM/Ano` para enriquecer o modelo.
* **Machine Learning:** Clusterização para segmentação de mercado e Regressão (Random Forest) para precificação.

---

## 🏗️ Arquitetura do Projeto

```text
aws-scraper-carros/
│
├── src/
│   ├── scraper.py       # Robô de extração de dados (Headless Chrome)
│   └── storage.py       # Classe de abstração para S3/Local Filesystem
│
├── notebooks/
│   ├── 01_analise_exploratoria.ipynb  # EDA, Correlações e Visualizações
│   └── 02_machine_learning.ipynb      # K-Means, Random Forest e Avaliação
│
├── data/                # Armazenamento local (ignorado pelo git)
├── models/              # Modelos treinados .pkl (ignorado pelo git)
└── requirements.txt     # Dependências do projeto
```


📊 Resultados do ModeloO modelo final (Random Forest Regressor) obteve uma performance sólida na previsão de preços, superando abordagens mais simples como Árvores de Decisão.MétricaResultadoInterpretaçãoR² Score0.77O modelo explica 77% da variação de preço dos carros.MAER$ 2.659Erro médio absoluto por previsão.RMSER$ 3.800Penaliza erros maiores (outliers).Insights de DadosFeature Importance: A Idade do veículo e a Potência do Motor (ex: 1.0 vs 2.0) foram os fatores mais determinantes para o preço, superando a Quilometragem bruta.Segmentação: O algoritmo K-Means identificou com sucesso 3 clusters claros de veículos: Econômicos, Intermediários e Premium.🛠️ Tecnologias UtilizadasLinguagem: PythonExtração: Selenium, Webdriver ManagerProcessamento: Pandas, NumPyCloud: AWS S3, Boto3, Python-DotenvMachine Learning: Scikit-Learn (RandomForest, KMeans, StandardScaler)Visualização: Matplotlib, Seaborn🚀 Como Executar
1. Clone o repositório
```text
    git clone https://github.com/VictorCPena/aws-scraper-carros
    cd aws-scraper-carros
```
1. Instale as dependências
```text
   pip install -r requirements.txt 
   ```

1. Configuração de Ambiente
   Crie um arquivo .env na raiz do projeto.
   Para rodar localmente (sem AWS): 
   TOMLAMBIENTE=LOCAL

2. Para rodar integrado à AWS:
```text
    TOMLAMBIENTE=PROD
    BUCKET_NAME=nome-do-seu-bucket
    AWS_ACCESS_KEY_ID=sua-chave
    AWS_SECRET_ACCESS_KEY=seu-segredo
   AWS_REGION=us-east-1
```
3. Executando o Pipeline
   
   Coleta de Dados: src/scraper.py

4. Análise e Modelagem:
   
   Abra os arquivos na pasta notebooks/ utilizando o Jupyter Notebook ou VS Code.