import os
import boto3
from io import StringIO, BytesIO
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

class CloudStorage:
    def __init__(self):
        self.env = os.environ.get('AMBIENTE', 'LOCAL')
        self.bucket_name = os.environ.get('BUCKET_NAME', 'bucket-teste')
        self.local_path = 'data' 
        
        if self.env == 'PROD':
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
                region_name=os.environ.get('AWS_REGION', 'us-east-1')
            )
        else:
            if not os.path.exists(self.local_path):
                os.makedirs(self.local_path)

    def salvar(self, df, nome_arquivo):
        """Salva DF no S3 (Prod) ou na pasta data/ (Local)"""
        try:
            if self.env == 'PROD':
                csv_buffer = StringIO()
                df.to_csv(csv_buffer, index=False)
                self.s3_client.put_object(
                    Bucket=self.bucket_name, 
                    Key=nome_arquivo, 
                    Body=csv_buffer.getvalue()
                )
                print(f"☁️ Upload S3 concluído: {nome_arquivo}")
            else:
                caminho = os.path.join(self.local_path, nome_arquivo)
                df.to_csv(caminho, index=False)
                print(f"💾 Salvo localmente: {caminho}")
        except Exception as e:
            print(f"❌ Erro ao salvar: {e}")

    def ler_csv(self, nome_arquivo):
        """Lê CSV do S3 (Prod) ou da pasta data/ (Local)"""
        try:
            if self.env == 'PROD':
                print(f"☁️ Baixando do S3: {nome_arquivo}...")
                obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=nome_arquivo)
                return pd.read_csv(obj['Body'])
            else:
                print(f"📂 Lendo do disco local: {nome_arquivo}...")
                caminho = os.path.join(self.local_path, nome_arquivo)
                if os.path.exists(caminho):
                    return pd.read_csv(caminho)
                else:
                    raise FileNotFoundError(f"Arquivo não encontrado localmente: {caminho}")
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
            return None