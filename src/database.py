"""Persistência Oracle para módulos da colônia. Sem conexão automática ao importar."""
import os
from pathlib import Path
from dotenv import load_dotenv
import oracledb

RAIZ = Path(__file__).resolve().parents[1]


def conectar():
    load_dotenv(RAIZ / ".env", override=True)
    usuario = os.getenv("ORACLE_USER", "").strip()
    senha = os.getenv("ORACLE_PASSWORD", "")
    host = os.getenv("ORACLE_HOST", "oracle.fiap.com.br").strip()
    porta = int(os.getenv("ORACLE_PORT", "1521"))
    sid = os.getenv("ORACLE_SID", "ORCL").strip()
    if not usuario or not senha:
        raise ValueError("Configure ORACLE_USER e ORACLE_PASSWORD no arquivo .env.")
    # A conexão do SQL Developer da FIAP usa SID (não SERVICE_NAME).
    dsn = oracledb.makedsn(host, porta, sid=sid)
    return oracledb.connect(user=usuario, password=senha, dsn=dsn)


def listar(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT ID, NOME, TIPO, CONSUMO_KWH, TEMPERATURA_C, STATUS FROM MODULOS ORDER BY ID")
        return cur.fetchall()


def buscar(conn, identificador):
    with conn.cursor() as cur:
        cur.execute("SELECT ID, NOME, TIPO, CONSUMO_KWH, TEMPERATURA_C, STATUS FROM MODULOS WHERE ID = :id", {"id": identificador})
        return cur.fetchone()


def cadastrar(conn, dados):
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO MODULOS (NOME, TIPO, CONSUMO_KWH, TEMPERATURA_C, STATUS)
                       VALUES (:nome, :tipo, :consumo, :temperatura, :status)""", dados)
    conn.commit()


def alterar(conn, identificador, dados):
    with conn.cursor() as cur:
        cur.execute("""UPDATE MODULOS SET NOME=:nome, TIPO=:tipo, CONSUMO_KWH=:consumo,
                       TEMPERATURA_C=:temperatura, STATUS=:status WHERE ID=:id""",
                    {**dados, "id": identificador})
        alterados = cur.rowcount
    conn.commit()
    return alterados


def excluir(conn, identificador):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM MODULOS WHERE ID=:id", {"id": identificador})
        excluidos = cur.rowcount
    conn.commit()
    return excluidos


if __name__ == "__main__":
    from main import main
    main()
