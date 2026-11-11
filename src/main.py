"""Menu do SIFSM: preserva as opções do menu original da equipe."""
import oracledb
import crud
import database
from resultados_simulacao import exibir_resumo_simulacao, menu_previsao_consumo, alerta_energia


def main():
    conexao = None
    try:
        while True:
            print("\n==============================")
            print("  SISTEMA DE GERENCIAMENTO SISFM")
            print("==============================")
            print("    1. Cadastrar Módulo")
            print("    2. Consultar Módulos")
            print("    3. Alterar Módulo")
            print("    4. Excluir Módulo")
            print("    5. Excluir TODOS os Módulos")
            print("    6. Sair")
            print("\n  Opções de Análise:")
            print("    7. Resumo da Simulação Energética")
            print("    8. Previsão de Consumo")
            print("    9. Testar Alerta Energético")
            print("   10. Regerar Simulação e Gráficos")
            opcao = input("    Escolha uma opção: ").strip()
            if opcao == "6":
                print("Saindo do sistema...")
                break
            if opcao not in {str(i) for i in range(1, 11)}:
                print("Opção inválida. Escolha uma opção do menu.")
                continue
            try:
                if opcao in {"1", "2", "3", "4", "5"}:
                    if conexao is None:
                        conexao = database.conectar()
                        print("Conexão estabelecida com sucesso!")
                    if opcao in {"1", "2"}:
                        crud.executar(conexao, opcao)
                    elif opcao == "3":
                        crud.executar(conexao, "4")
                    elif opcao == "4":
                        crud.executar(conexao, "5")
                    else:
                        print("ATENÇÃO: esta operação apaga TODOS os módulos do Oracle.")
                        print("Não utilize esta opção durante a gravação do vídeo.")
                        if input("Digite EXCLUIR TODOS para confirmar: ").strip() == "EXCLUIR TODOS":
                            with conexao.cursor() as cursor:
                                cursor.execute("DELETE FROM MODULOS")
                                quantidade = cursor.rowcount
                            conexao.commit()
                            print(f"{quantidade} módulo(s) excluído(s).")
                        else:
                            print("Exclusão cancelada.")
                elif opcao == "7":
                    exibir_resumo_simulacao()
                elif opcao == "8":
                    menu_previsao_consumo()
                elif opcao == "9":
                    soc = crud.numero(input("Carga da bateria (%): "), minimo=0)
                    if soc > 100:
                        raise ValueError("A carga deve estar entre 0 e 100%.")
                    falta = crud.numero(input("Energia não suprida (kWh): "), minimo=0)
                    print("ALERTA ENERGÉTICO" if alerta_energia(soc / 100, falta) else "Operação sem alerta.")
                elif opcao == "10":
                    from analise_simulacao import executar
                    executar(verbose=True)
                    print("Simulação e gráficos atualizados.")
            except (ValueError, OSError, oracledb.Error, KeyError, ImportError) as erro:
                print(f"Não foi possível executar a operação: {erro}")
                if isinstance(erro, oracledb.Error) and conexao is not None:
                    try:
                        conexao.rollback()
                    except oracledb.Error:
                        pass
            except KeyboardInterrupt:
                print("\nOperação interrompida.")
    finally:
        if conexao is not None:
            conexao.close()


if __name__ == "__main__":
    main()
