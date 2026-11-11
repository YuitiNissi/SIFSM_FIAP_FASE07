import os
from dotenv import load_dotenv
import oracledb
import pandas as pd

load_dotenv()


try:
    senha = os.getenv("ORACLE_PASSWORD")
    dsn = os.getenv("ORACLE_DSN")
    usuario = os.getenv("ORACLE_USER")

    #Conexao com servidor
    dsnString = oracledb.makedsn("oracle.fiap.com.br", 1521, service_name="ORCL")

    #Conexao com usuario
    conn = oracledb.connect(user=usuario, password=senha, dsn=dsn)
    print("Conexão bem-sucedida!")

    #Cria as instruções SQL para cada modulo
    inst_cadastro = conn.cursor()
    inst_consulta = conn.cursor()
    inst_alteracao = conn.cursor()
    inst_exclusao = conn.cursor()
except oracledb.Error as e:
    print("Erro ao conectar ao banco de dados:", e)
    conexao = False
else:
    #Flag para executar a Aplicacao
    conexao = True
    input('Conexão estabelecida com sucesso! Pressione Enter para continuar...')

margem = ' ' * 4 #Define uma margem para a exibição das mensagens no terminal

#Enquanto o flag conexao estiver True, o programa continua executando
while conexao:
    #Limpa a tela via SO
    os.system('cls' if os.name == 'nt' else 'clear')

    #Apresenta o menu de opções
    print(f"{margem}==============================")
    print(f"{margem}  SISTEMA DE GERENCIAMENTO SISFM")
    print("""
    1. Cadastrar Módulo
    2. Consultar Módulos
    3. Alterar Módulo
    4. Excluir Módulo
    5. Excluir TODOS os Módulos
    6. Sair
    """)

    #Captura a opção escolhida pelo usuário
    opcao = input(f"{margem}Escolha uma opção: ")

    #Verficia se a opção escolhida é válida
    if opcao.isdigit():
        opcao = int(opcao)
    else:
        print(f"{margem}Opção inválida. Digite um número de 1 a 6.")
        input(f"{margem}Pressione Enter para continuar...")
        continue

    os.system('cls' if os.name == 'nt' else 'clear')  # Limpa a tela novamente

    #Verifica a escolha do usuário e executa a função correspondente
    match opcao:
        case 1:
            try:
                print(f"{margem}==============================")
                print(f"{margem}  CADASTRO DE MÓDULO")
                print(f"{margem}==============================")
                #Recebe valores
                nome_modulo = input(f"{margem}Digite o nome do módulo: ")
                tipo_modulo = input(f"{margem}Digite o tipo do módulo: ")
                consumo_modulo = input(f"{margem}Digite o consumo do módulo: ")
                temperatura_modulo = input(f"{margem}Digite a temperatura do módulo: ")
                status_modulo = input(f"{margem}Digite o status do módulo: ")
        

                #Monta as instruções SQL para inserção em uma string
                cadastro = f""" insert into modulos (nome, tipo, consumo_kwh, temperatura_c, status) values ('{nome_modulo}', '{tipo_modulo}', '{consumo_modulo}', '{temperatura_modulo}', '{status_modulo}') """
                #Executa e grava
                inst_cadastro.execute(cadastro)
                conn.commit()

            except ValueError:
                print(f"{margem}Erro: Digite um valor válido.")
            except oracledb.Error as e:
                print(f"{margem}Erro ao cadastrar módulo:", e)
            else:
                print(f"{margem}Módulo cadastrado com sucesso!")

        case 2:
            try:
                print(f"{margem}==============================")
                print(f"{margem}  CONSULTA DE MÓDULOS")
                print(f"{margem}==============================")
                #Monta as instruções SQL para consulta em uma string
                lista = []
                consulta = "select * from modulos"

                #Executa e grava
                inst_consulta.execute(consulta)
                resultado = inst_consulta.fetchall()

                #Capura os resultados em uma lista
                for r in resultado:
                    lista.append(r)

                #Ordena a lista
                lista = sorted(lista)

                #Cria um DataFrame com os resultados
                df = pd.DataFrame.from_records(lista, columns=['ID', 'Nome', 'Tipo', 'Consumo', 'Temperatura', 'Status'])

                #Verifica se o DataFrame está vazio
                if df.empty:
                    print(f"{margem}Nenhum módulo encontrado.")
                else:
                    #Exibe o DataFrame
                    print(df)
            except oracledb.Error as e:
                print(f"{margem}Erro ao consultar módulos:", e)
            else:
                print(f"{margem}Consulta realizada com sucesso!")

        case 3:
            try:
                print(f"{margem}==============================")
                print(f"{margem}  ALTERAÇÃO DE MÓDULO")
                print(f"{margem}==============================")
                #Recebe valores
                lista = []

                id_modulo = input(f"{margem}Digite o ID do módulo a ser alterado: ")

                #Constroi a instrução SQL para buscar o módulo pelo ID
                consulta_id = f""" select * from modulos where id={id_modulo} """
                inst_consulta.execute(consulta_id)
                resultado = inst_consulta.fetchall()

                # Preenche a lista com o registro encontrado
                for r in resultado:
                    lista.append(r)

                #Analisa se foi encontrado algo
                if len(lista) == 0:
                    print(f"{margem}Módulo não encontrado.")
                else:
                    #Recebe os novos valores
                    nome_modulo = input(f"{margem}Digite o novo nome do módulo: ")
                    tipo_modulo = input(f"{margem}Digite o novo tipo do módulo: ")
                    consumo_modulo = input(f"{margem}Digite o novo consumo do módulo: ")
                    temperatura_modulo = input(f"{margem}Digite a nova temperatura do módulo: ")
                    status_modulo = input(f"{margem}Digite o novo status do módulo: ")

                    #Monta as instruções SQL para alteração em uma string
                    alteracao = f""" update modulos set nome='{nome_modulo}', tipo='{tipo_modulo}', consumo='{consumo_modulo}', temperatura='{temperatura_modulo}', status='{status_modulo}' where id={id_modulo} """

                    #Executa e grava
                    inst_alteracao.execute(alteracao)
                    conn.commit()

            except ValueError:  
                print(f"{margem}Erro: Digite um valor válido.")
            except oracledb.Error as e:
                print(f"{margem}Erro ao alterar módulo:", e)
            else:
                print(f"{margem}Módulo alterado com sucesso!")

        case 4:
            try:
                print(f"{margem}==============================")
                print(f"{margem}  EXCLUSÃO DE MÓDULO")
                print(f"{margem}==============================")
                #Recebe valores
                lista = []

                id_modulo = input(f"{margem}Digite o ID do módulo a ser excluído: ")

                if id_modulo.isdigit():
                    #Constroi a instrução SQL para buscar o módulo pelo ID
                    consulta_id = f""" select * from modulos where id={id_modulo} """
                    inst_consulta.execute(consulta_id)
                    resultado = inst_consulta.fetchall()

                    # Preenche a lista com o registro encontrado
                    for r in resultado:
                        lista.append(r)

                    #Analisa se foi encontrado algo
                    if len(lista) == 0:
                        print(f"{margem}Módulo não encontrado.")
                    else:
                        #Monta as instruções SQL para exclusão em uma string
                        exclusao = f""" delete from modulos where id={id_modulo} """

                        #Executa e grava
                        inst_exclusao.execute(exclusao)
                        conn.commit()
            except ValueError:
                print(f"{margem}Erro: Digite um valor válido.")
            except oracledb.Error as e:
                print(f"{margem}Erro ao excluir módulo:", e)
            else:
                print(f"{margem}Módulo excluído com sucesso!")

        case 5:
            try:
                print(f"{margem}==============================")
                print(f"{margem}  EXCLUSÃO DE TODOS OS MÓDULOS")
                print(f"{margem}==============================")
                #Monta as instruções SQL para exclusão em uma string
                confirma_exclusao = input(f"{margem}Tem certeza que deseja excluir todos os módulos? (S/N): ")
                if confirma_exclusao.lower() == 's':
                    exclusao_todos = "delete from modulos"

                    inst_exclusao.execute(exclusao_todos)
                    conn.commit()

                    data_reset_ids = """ alter table modulos drop modify(id generated as identity(start with 1)) """
                    inst_exclusao.execute(data_reset_ids)
                    conn.commit()

                else:
                    print(f"{margem}Exclusão cancelada.")
                    continue
                #Executa e grava
            except oracledb.Error as e:
                print(f"{margem}Erro ao excluir todos os módulos:", e)
            else:
                print(f"{margem}Todos os módulos foram excluídos com sucesso!")

        case 6:
            print(f"{margem}Saindo do sistema...")
            conexao = False