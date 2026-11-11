"""Testes isolados: não conectam ao Oracle da FIAP."""
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest
# Ambiente de avaliação sem driver Oracle: simula apenas o módulo externo.
try:
    import oracledb
except ImportError:
    from types import ModuleType
    oracledb = ModuleType("oracledb")
    oracledb.Error = type("OracleError", (Exception,), {})
    sys.modules["oracledb"] = oracledb
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import crud
import database


def test_numeros_validos_e_invalidos():
    assert crud.numero("12,5", minimo=0) == 12.5
    for valor in ("nan", "inf", "-1", "texto"):
        with pytest.raises(ValueError):
            crud.numero(valor, minimo=0)


def test_cadastrar_usa_parametros_e_commit():
    conn = MagicMock()
    dados = dict(nome="Teste", tipo="HABITACAO", consumo=10.0, temperatura=22.0, status="ATIVO")
    database.cadastrar(conn, dados)
    query, parametros = conn.cursor.return_value.__enter__.return_value.execute.call_args.args
    assert ":nome" in query and "Teste" not in query
    assert parametros == dados
    conn.commit.assert_called_once()


def test_alterar_usa_colunas_corretas():
    conn = MagicMock()
    dados = dict(nome="Teste", tipo="HABITACAO", consumo=10.0, temperatura=22.0, status="ATIVO")
    database.alterar(conn, 2, dados)
    query, parametros = conn.cursor.return_value.__enter__.return_value.execute.call_args.args
    assert "CONSUMO_KWH" in query and "TEMPERATURA_C" in query
    assert parametros["id"] == 2


def test_excluir_por_id_nao_apaga_tudo():
    conn = MagicMock()
    database.excluir(conn, 3)
    query, parametros = conn.cursor.return_value.__enter__.return_value.execute.call_args.args
    assert "WHERE ID=:id" in query
    assert parametros == {"id": 3}
