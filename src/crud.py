"""Validação e interface textual do CRUD de módulos."""
import math
import database

CAMPOS = ("nome", "tipo", "consumo", "temperatura", "status")


def numero(texto, *, minimo=None):
    valor = float(texto.replace(",", ".").strip())
    if not math.isfinite(valor) or (minimo is not None and valor < minimo):
        raise ValueError("Número inválido ou fora do intervalo permitido.")
    return valor


def ler_id():
    identificador = int(input("ID do módulo: ").strip())
    if identificador <= 0:
        raise ValueError("O ID deve ser positivo.")
    return identificador


def ler_dados():
    nome = input("Nome: ").strip()
    tipo = input("Tipo: ").strip().upper()
    consumo = numero(input("Consumo (kWh): "), minimo=0)
    temperatura = numero(input("Temperatura (°C): "))
    status = input("Status: ").strip().upper()
    if not nome or not tipo or not status:
        raise ValueError("Nome, tipo e status são obrigatórios.")
    if len(nome)>100 or len(tipo)>50 or len(status)>20:
        raise ValueError("Texto excede o tamanho permitido pela tabela.")
    return dict(nome=nome, tipo=tipo, consumo=consumo, temperatura=temperatura, status=status)


def mostrar(conn):
    registros = database.listar(conn)
    if not registros:
        print("Nenhum módulo cadastrado.")
        return
    for r in registros:
        print(f"ID: {r[0]} | {r[1]} | {r[2]} | {r[3]} kWh | {r[4]} °C | {r[5]}")


def executar(conn, opcao):
    if opcao == "1":
        database.cadastrar(conn, ler_dados())
        print("Módulo cadastrado.")
    elif opcao == "2":
        mostrar(conn)
    elif opcao == "3":
        identificador = ler_id()
        registro = database.buscar(conn, identificador)
        print(registro if registro else "Módulo não encontrado.")
    elif opcao == "4":
        identificador = ler_id()
        if not database.buscar(conn, identificador):
            print("Módulo não encontrado.")
        else:
            database.alterar(conn, identificador, ler_dados())
            print("Módulo atualizado.")
    elif opcao == "5":
        identificador = ler_id()
        if not database.buscar(conn, identificador):
            print("Módulo não encontrado.")
        elif input(f"Confirma excluir ID {identificador}? (S/N): ").strip().upper() == "S":
            database.excluir(conn, identificador)
            print("Módulo excluído.")
        else:
            print("Exclusão cancelada.")
