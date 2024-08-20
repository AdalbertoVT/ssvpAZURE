import azure.functions as func
import logging
import psycopg2
from psycopg2 import sql

async def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Função HTTP do Azure processada com sucesso.')

    conn = get_connection()
    try:
        init_database(conn)
        adicionar_colunas_faltantes(conn)
        resultado = listar_pessoas(conn)
        return func.HttpResponse(resultado, status_code=200)
    finally:
        conn.close()

def get_connection():
    """Estabelece uma conexão com o banco de dados PostgreSQL."""
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="admin",
        host="localhost",
        port="5432"
    )

def init_database(conn):
    """Inicializa o banco de dados criando as tabelas necessárias."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pessoa_responsavel (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    cpf VARCHAR(14) UNIQUE NOT NULL,
                    contato VARCHAR(20) NOT NULL,
                    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pessoa (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    endereco TEXT NOT NULL,
                    num_membros INT NOT NULL,
                    cpf VARCHAR(14) NOT NULL,
                    contato VARCHAR(20),
                    id_responsavel INT REFERENCES pessoa_responsavel(id),
                    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_distribuicao TIMESTAMP,
                    cestas_recebidas INT DEFAULT 0,
                    alimentos_distribuidos TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS estoque (
                    id SERIAL PRIMARY KEY,
                    alimento VARCHAR(255) NOT NULL,
                    quantidade INT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS distribuicao_cestas (
                    id SERIAL PRIMARY KEY,
                    pessoa_id INT REFERENCES pessoa(id),
                    data_distribuicao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    alimentos TEXT NOT NULL
                );
            """)
        conn.commit()
    except Exception as e:
        logging.error("Erro ao inicializar o banco de dados: %s", e)
        conn.rollback()

def adicionar_coluna_se_nao_existir(conn, tabela, coluna, tipo):
    """Adiciona uma coluna a uma tabela se ela não existir."""
    try:
        with conn.cursor() as cursor:
            query = sql.SQL("ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS {coluna} {tipo};").format(
                tabela=sql.Identifier(tabela),
                coluna=sql.Identifier(coluna),
                tipo=sql.SQL(tipo)
            )
            cursor.execute(query)
        conn.commit()
        logging.info(f"Coluna '{coluna}' adicionada à tabela '{tabela}' com sucesso!")
    except Exception as e:
        logging.error(f"Erro ao adicionar a coluna '{coluna}' à tabela '{tabela}': %s", e)
        conn.rollback()

def adicionar_colunas_faltantes(conn):
    """Adiciona as colunas cestas_recebidas e alimentos_distribuidos na tabela pessoa, se não existirem."""
    try:
        adicionar_coluna_se_nao_existir(conn, 'pessoa', 'cestas_recebidas', 'INT DEFAULT 0')
        adicionar_coluna_se_nao_existir(conn, 'pessoa', 'alimentos_distribuidos', 'TEXT')
    except Exception as e:
        logging.error("Erro ao adicionar colunas faltantes: %s", e)

def listar_pessoas(conn):
    """Lista todas as pessoas registradas no banco de dados."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.nome, p.endereco, p.num_membros, p.cpf, p.contato, p.data_registro, p.data_distribuicao, p.cestas_recebidas, p.alimentos_distribuidos,
                       r.nome AS nome_responsavel, r.cpf AS cpf_responsavel, r.contato AS contato_responsavel
                FROM pessoa p
                LEFT JOIN pessoa_responsavel r ON p.id_responsavel = r.id
            """)
            pessoas = cursor.fetchall()
            resultado = []
            for pessoa in pessoas:
                resultado.append(
                    f"ID: {pessoa[0]}, Nome: {pessoa[1]}, Endereço: {pessoa[2]}, Membros da Família: {pessoa[3]}, "
                    f"CPF: {pessoa[4]}, Contato: {pessoa[5]}, Responsável: {pessoa[10]} "
                    f"(CPF: {pessoa[11]}, Contato: {pessoa[12]}), Data Registro: {pessoa[6]}, "
                    f"Data Distribuição: {pessoa[7]}, Cestas Recebidas: {pessoa[8]}, Alimentos Distribuídos: {pessoa[9]}"
                )
            return "\n".join(resultado)
    except Exception as e:
        logging.error("Erro ao listar pessoas: %s", e)
        return "Erro ao listar pessoas."
