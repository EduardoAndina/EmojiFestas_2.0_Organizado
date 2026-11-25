import re
from datetime import date, datetime
from database.banco import Banco
from models.entidades import CalendarioSalao, Funcionario

PREPOSICOES_NOME = {"da", "das", "de", "do", "dos", "e"}


def formatar_nome_pessoa(nome: str) -> str:
    partes = [p for p in re.sub(r"\s+", " ", nome.strip()).split(" ") if p]
    resultado = []
    for idx, parte in enumerate(partes):
        minuscula = parte.lower()
        if idx > 0 and minuscula in PREPOSICOES_NOME:
            resultado.append(minuscula)
        else:
            resultado.append("-".join(sub.capitalize() for sub in minuscula.split("-")))
    return " ".join(resultado)


def validar_e_formatar_nome(nome: str) -> tuple[bool, str]:
    limpo = re.sub(r"\s+", " ", nome.strip())
    if len(limpo) < 2:
        return False, "O nome deve ter pelo menos 2 caracteres."
    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ\s\-']+", limpo):
        return False, "O nome deve conter apenas letras (sem números ou símbolos)."
    return True, formatar_nome_pessoa(limpo)


def validar_e_formatar_celular(celular: str) -> tuple[bool, str]:
    digitos = re.sub(r"\D", "", celular)
    if len(digitos) not in (10, 11):
        return False, "Celular/telefone inválido! Informe DDD + número com 10 ou 11 dígitos (ex: 51980623155)."
    if len(digitos) == 11 and digitos[2] != "9":
        return False, "Celular de 11 dígitos deve começar com 9 após o DDD (ex: 51980623155)."
    if len(set(digitos)) == 1:
        return False, "Número de telefone inválido (dígitos repetidos)."
    if len(digitos) == 11:
        formatado = f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    else:
        formatado = f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    return True, formatado


def validar_e_formatar_cpf(cpf: str) -> tuple[bool, str]:
    digitos = re.sub(r"\D", "", cpf)
    if len(digitos) != 11:
        return False, "CPF inválido! Deve conter exatamente 11 dígitos numéricos."
    if len(set(digitos)) == 1:
        return False, "CPF inválido (todos os dígitos iguais)."
    soma1 = sum(int(digitos[i]) * (10 - i) for i in range(9))
    dv1 = (soma1 * 10) % 11
    dv1 = 0 if dv1 == 10 else dv1
    if dv1 != int(digitos[9]):
        return False, "CPF inválido! Primeiro dígito verificador não confere."
    soma2 = sum(int(digitos[i]) * (11 - i) for i in range(10))
    dv2 = (soma2 * 10) % 11
    dv2 = 0 if dv2 == 10 else dv2
    if dv2 != int(digitos[10]):
        return False, "CPF inválido! Segundo dígito verificador não confere."
    formatado = f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    return True, formatado


def validar_data_festa(data_str: str) -> tuple[bool, str]:
    limpa = data_str.strip()
    try:
        dt = date.fromisoformat(limpa)
    except ValueError:
        return False, "Data inválida! Use o formato AAAA-MM-DD (ex: 2026-12-20) com dia e mês reais."
    if dt < date.today():
        return False, "A data da festa não pode ser no passado."
    return True, dt.isoformat()


def validar_hora_festa(hora_str: str) -> tuple[bool, str]:
    limpa = hora_str.strip()
    if not re.fullmatch(r"\d{2}:\d{2}", limpa):
        return False, "Horário inválido! Use o formato HH:MM (ex: 14:00)."
    try:
        hr = datetime.strptime(limpa, "%H:%M").time()
    except ValueError:
        return False, "Horário inválido! Informe horas entre 00:00 e 23:59."
    return True, hr.strftime("%H:%M")


def _perguntar_tentar_novamente(mensagem_erro: str) -> bool:
    print(f"Erro: {mensagem_erro}")
    while True:
        resp = input("Deseja tentar cadastrar/digitar novamente? (s/n): ").strip().lower()
        if resp in ("s", "sim"):
            return True
        if resp in ("n", "nao", "não"):
            return False
        print("Digite 's' para sim ou 'n' para não.")


def _ler_int(
    mensagem: str,
    permitir_vazio: bool = False,
    padrao: int | None = None,
    minimo: int | None = None,
    maximo: int | None = None,
) -> int | None:
    while True:
        entrada = input(mensagem).strip()
        if not entrada and permitir_vazio:
            return padrao
        try:
            valor = int(entrada)
            if minimo is not None and valor < minimo:
                print(f"O valor deve ser maior ou igual a {minimo}.")
                continue
            if maximo is not None and valor > maximo:
                print(f"O valor deve ser menor ou igual a {maximo}.")
                continue
            return valor
        except ValueError:
            print("Entrada inválida! Digite um número inteiro.")


def _ler_float(mensagem: str, minimo: float | None = None) -> float:
    while True:
        entrada = input(mensagem).strip().replace(",", ".")
        try:
            valor = float(entrada)
            if minimo is not None and valor < minimo:
                print(f"O valor deve ser maior ou igual a {minimo:.2f}.")
                continue
            return valor
        except ValueError:
            print("Entrada inválida! Digite um valor numérico (ex: 250.00).")


class SistemaCLI:
    def __init__(self, db: Banco):
        self.db = db
        self.usuario_logado: Funcionario | None = None

    def login(self) -> bool:
        print("=" * 44)
        print("      EMOJIFESTAS - LOGIN DO SISTEMA      ")
        print("=" * 44)
        print("(Dica: marina / 1234 [Proprietária] ou lucas / 1234 [Atendente])")
        for tentativa in range(3):
            usuario = input("Usuário: ")
            senha = input("Senha: ")
            func = self.db.autenticar(usuario, senha)
            if func:
                self.usuario_logado = func
                print(f"\nBem-vindo(a), {func.nome} ({func.perfil.capitalize()})!")
                return True
            print(f"Credenciais inválidas ({2 - tentativa} tentativa(s) restante(s)).")
        return False

    def executar(self):
        if not self.login():
            print("Número máximo de tentativas excedido. Encerrando.")
            return

        while True:
            print("\n" + "=" * 44)
            print("       EMOJIFESTAS - MENU PRINCIPAL       ")
            print("=" * 44)
            print("1. Listar Espaços (Salões), Combos e Extras")
            print("2. Listar Clientes")
            print("3. Cadastrar Novo Cliente")
            print("4. Agendar Festa (com verificação de agenda)")
            print("5. Listar Agendamentos (Festas)")
            print("6. Ver Calendário Mensal por Espaço")
            print("7. Registrar / Consultar Pagamentos")
            if self.usuario_logado and self.usuario_logado.eh_proprietaria():
                print("8. [Proprietária] Cadastrar Novo Espaço")
                print("9. [Proprietária] Cancelar Festa")
            print("0. Sair")
            print()
            opcao = input("Escolha uma opção: ").strip()

            if opcao == "1":
                self._exibir_catalogo()
            elif opcao == "2":
                self._listar_clientes()
            elif opcao == "3":
                self._cadastrar_cliente()
            elif opcao == "4":
                self._agendar_festa()
            elif opcao == "5":
                self._listar_festas()
            elif opcao == "6":
                self._ver_calendario_espaco()
            elif opcao == "7":
                self._gerenciar_pagamentos()
            elif opcao == "8" and self.usuario_logado and self.usuario_logado.eh_proprietaria():
                self._cadastrar_salao()
            elif opcao == "9" and self.usuario_logado and self.usuario_logado.eh_proprietaria():
                self._cancelar_festa()
            elif opcao == "0":
                print("Saindo do sistema... Até logo!")
                break
            else:
                print("Opção inválida ou sem permissão de acesso.")

    def _exibir_catalogo(self):
        print("\n--- ESPAÇOS EMOJIFESTAS ---")
        saloes = self.db.listar_saloes()
        if not saloes:
            print("Nenhum espaço cadastrado.")
        else:
            for s in saloes:
                print(f"[{s.id}] {s.nome} | Capacidade: até {s.capacidade} convidados | Acréscimo: R$ {s.acrescimo:,.2f}")
                if s.endereco:
                    print(f"    Endereço: {s.endereco}")
                if s.diferencial:
                    print(f"    Diferencial: {s.diferencial}")
                if s.estrutura:
                    print(f"    Estrutura: {s.estrutura}")

        print("\n--- COMBOS ---")
        for c in self.db.listar_combos():
            print(f"[{c.id}] {c.nome} - R$ {c.preco:,.2f} ({c.descricao})")

        print("\n--- EXTRAS ---")
        for e in self.db.listar_extras():
            print(f"[{e.id}] {e.nome} - R$ {e.preco:,.2f}")
        input("\nPressione Enter para voltar ao menu...")

    def _listar_clientes(self):
        print("\n--- CLIENTES CADASTRADOS ---")
        clientes = self.db.listar_clientes()
        if not clientes:
            print("Nenhum cliente cadastrado.")
        else:
            for c in clientes:
                print(f"[{c.id}] {c.nome} | Contato: {c.contato} | Doc: {c.documento}")
        input("\nPressione Enter para voltar ao menu...")

    def _cadastrar_cliente(self):
        while True:
            print("\n--- NOVO CLIENTE ---")
            ok_nome, nome_ou_erro = validar_e_formatar_nome(input("Nome completo: "))
            if not ok_nome:
                if _perguntar_tentar_novamente(nome_ou_erro):
                    continue
                return

            ok_cel, cel_ou_erro = validar_e_formatar_celular(input("Celular com DDD (ex: 51980623155): "))
            if not ok_cel:
                if _perguntar_tentar_novamente(cel_ou_erro):
                    continue
                return

            ok_cpf, cpf_ou_erro = validar_e_formatar_cpf(input("CPF (apenas números ou 000.000.000-00): "))
            if not ok_cpf:
                if _perguntar_tentar_novamente(cpf_ou_erro):
                    continue
                return

            try:
                cid = self.db.cadastrar_cliente(nome_ou_erro, cel_ou_erro, cpf_ou_erro)
                print(f"Cliente '{nome_ou_erro}' cadastrado com sucesso! ID: {cid}")
                return
            except ValueError as err:
                if not _perguntar_tentar_novamente(str(err)):
                    return

    def _mostrar_calendario_salao(self, salao_id: int, ano: int, mes: int):
        salao = self.db.salao(salao_id)
        if not salao:
            return
        festas_mes = self.db.listar_festas_por_salao_e_mes(salao_id, ano, mes)
        cal = CalendarioSalao(salao, ano, mes, festas_mes)
        print()
        print(cal())
        if cal.festas_mes:
            print(f"Horários já ocupados em {salao.nome} ({cal.nome_mes}/{ano}):")
            for f in cal.festas_mes:
                cli = self.db.cliente(f.cliente_id)
                print(
                    f"  - Dia {f.data.split('-')[2]} ({f.data}): {f.inicio} às {f.hora_fim_str()} "
                    f"[Festa #{f.id} - {cli.nome if cli else 'Cliente'}]"
                )
        else:
            print(f"Nenhuma reserva em {salao.nome} para {cal.nome_mes}/{ano}. Todos os dias livres!")

    def _ver_calendario_espaco(self):
        saloes = self.db.listar_saloes()
        if not saloes:
            print("\nNenhum espaço cadastrado.")
            return
        print("\n--- CALENDÁRIO POR ESPAÇO ---")
        ids_saloes = {s.id for s in saloes}
        for s in saloes:
            print(f"[{s.id}] {s.nome} (até {s.capacidade} convidados)")
        salao_id = _ler_int("Escolha o ID do Espaço: ", minimo=1)
        assert salao_id is not None
        if salao_id not in ids_saloes:
            print("Espaço não encontrado.")
            return
        hoje = date.today()
        ano = _ler_int(f"Ano (Enter para {hoje.year}): ", permitir_vazio=True, padrao=hoje.year, minimo=2020, maximo=2100)
        mes = _ler_int(f"Número do mês [1 a 12] (Enter para {hoje.month}): ", permitir_vazio=True, padrao=hoje.month, minimo=1, maximo=12)
        assert ano is not None and mes is not None
        self._mostrar_calendario_salao(salao_id, ano, mes)
        input("\nPressione Enter para voltar ao menu...")

    def _agendar_festa(self):
        while True:
            print("\n--- NOVO AGENDAMENTO ---")
            saloes = self.db.listar_saloes()
            ids_saloes = {s.id for s in saloes}
            for s in saloes:
                print(f"[{s.id}] {s.nome} | Até {s.capacidade} convidados | Acréscimo: R$ {s.acrescimo:,.2f}")
            salao_id = _ler_int("ID do Espaço: ", minimo=1)
            assert salao_id is not None
            if salao_id not in ids_saloes:
                if _perguntar_tentar_novamente("ID de espaço inexistente!"):
                    continue
                return

            clientes = self.db.listar_clientes()
            ids_clientes = {c.id for c in clientes}
            for c in clientes:
                print(f"[{c.id}] {c.nome} ({c.documento})")
            cliente_id = _ler_int("ID do Cliente: ", minimo=1)
            assert cliente_id is not None
            if cliente_id not in ids_clientes:
                if _perguntar_tentar_novamente("ID de cliente inexistente!"):
                    continue
                return

            ok_data, data_ou_erro = validar_data_festa(input("Data (AAAA-MM-DD): "))
            if not ok_data:
                if _perguntar_tentar_novamente(data_ou_erro):
                    continue
                return

            dt_escolhida = date.fromisoformat(data_ou_erro)
            self._mostrar_calendario_salao(salao_id, dt_escolhida.year, dt_escolhida.month)

            ok_hora, hora_ou_erro = validar_hora_festa(input("\nHorário de Início (HH:MM): "))
            if not ok_hora:
                if _perguntar_tentar_novamente(hora_ou_erro):
                    continue
                return

            combos = self.db.listar_combos()
            ids_combos = {cb.id for cb in combos}
            for cb in combos:
                print(f"[{cb.id}] {cb.nome} (R$ {cb.preco:,.2f})")
            combo_id = _ler_int("ID do Combo (ou Enter para nenhum): ", permitir_vazio=True, padrao=None, minimo=1)
            if combo_id is not None and combo_id not in ids_combos:
                if _perguntar_tentar_novamente("ID de combo inexistente!"):
                    continue
                return

            horas_extra = _ler_int("Horas extras (Enter para 0): ", permitir_vazio=True, padrao=0, minimo=0)
            assert horas_extra is not None

            extras = self.db.listar_extras()
            ids_extras = {ext.id for ext in extras}
            print("Extras disponíveis:")
            for ext in extras:
                print(f"[{ext.id}] {ext.nome} (R$ {ext.preco:,.2f})")

            extras_ids: list[int] = []
            extras_ok = True
            while True:
                extras_input = input("IDs dos extras separados por vírgula (ex: 1,3) ou Enter para nenhum: ").strip()
                if not extras_input:
                    break
                try:
                    candidatos = [int(x.strip()) for x in extras_input.split(",") if x.strip()]
                    invalidos = [eid for eid in candidatos if eid not in ids_extras]
                    if invalidos:
                        print(f"Extra(s) inexistente(s): {invalidos}")
                        extras_ok = False
                        break
                    extras_ids = candidatos
                    break
                except ValueError:
                    print("Digite apenas números separados por vírgula (ex: 1,3).")

            if not extras_ok:
                if _perguntar_tentar_novamente("Um ou mais extras informados não existem."):
                    continue
                return

            obs = input("Observações: ").strip()
            sucesso, mensagem = self.db.agendar_festa(
                salao_id, cliente_id, data_ou_erro, hora_ou_erro, combo_id, extras_ids, horas_extra, obs
            )
            print(mensagem)
            if sucesso:
                return
            if not _perguntar_tentar_novamente("Não foi possível concluir o agendamento."):
                return

    def _listar_festas(self):
        print("\n--- LISTA DE FESTAS AGENDADAS ---")
        festas = self.db.listar_festas()
        if not festas:
            print("Nenhuma festa agendada.")
        else:
            for f in festas:
                cliente = self.db.cliente(f.cliente_id)
                salao = self.db.salao(f.salao_id)
                pago = self.db.total_pago(f.id)
                saldo = max(0.0, round(f.total - pago, 2))
                status_pgto = "QUITADA" if saldo == 0 else f"Falta R$ {saldo:,.2f}"
                print(
                    f"Festa #{f.id} | {salao.nome if salao else 'N/A'} | "
                    f"Cliente: {cliente.nome if cliente else 'N/A'} | "
                    f"Data: {f.data} ({f.inicio} às {f.hora_fim_str()}) | "
                    f"Total: R$ {f.total:,.2f} | Pago: R$ {pago:,.2f} ({status_pgto})"
                )
        input("\nPressione Enter para voltar ao menu...")

    def _gerenciar_pagamentos(self):
        festas = self.db.listar_festas()
        if not festas:
            print("\nNenhuma festa agendada para gerenciar pagamentos.")
            return
        self._listar_festas()
        festa_id = _ler_int("\nInforme o ID da Festa: ", minimo=1)
        assert festa_id is not None
        festa = self.db.festa(festa_id)
        if not festa:
            print("Festa não encontrada.")
            return
        pagamentos = self.db.listar_pagamentos(festa_id)
        print(f"\n--- HISTÓRICO DE PAGAMENTOS (Festa #{festa.id}) ---")
        for p in pagamentos:
            print(f"[{p.id}] {p.data} - {p.tipo}: R$ {p.valor:,.2f}")
        pago = self.db.total_pago(festa_id)
        saldo = round(festa.total - pago, 2)
        print(f"Total da festa: R$ {festa.total:,.2f} | Total pago: R$ {pago:,.2f} | Saldo devedor: R$ {saldo:,.2f}")
        if saldo <= 0:
            print("Esta festa já está totalmente quitada.")
            return
        while True:
            registrar = input("Deseja registrar um novo pagamento agora? (s/n): ").strip().lower()
            if registrar in ("n", "nao", "não"):
                return
            if registrar not in ("s", "sim"):
                continue
            valor = _ler_float("Valor do pagamento (R$): ", minimo=0.01)
            tipo = input("Tipo (Sinal / Parcela / Quitação): ").strip() or "Parcela"
            ok, msg = self.db.registrar_pagamento(festa_id, valor, tipo)
            print(msg)
            if ok or not _perguntar_tentar_novamente("Pagamento não registrado."):
                return

    def _cadastrar_salao(self):
        while True:
            print("\n--- CADASTRAR NOVO ESPAÇO ---")
            nome_raw = input("Nome do espaço (ex: Espaço 4 - Garden): ").strip()
            if len(nome_raw) < 2:
                if _perguntar_tentar_novamente("O nome do espaço deve ter pelo menos 2 caracteres."):
                    continue
                return
            capacidade = _ler_int("Capacidade máxima de convidados: ", minimo=1)
            acrescimo = _ler_float("Acréscimo no valor (R$): ", minimo=0.0)
            endereco = input("Endereço (opcional): ").strip()
            diferencial = input("Diferencial (opcional): ").strip()
            estrutura = input("Estrutura (opcional): ").strip()
            assert capacidade is not None
            try:
                sid = self.db.criar_salao(nome_raw, capacidade, acrescimo, endereco, diferencial, estrutura)
                print(f"Espaço '{nome_raw}' cadastrado com sucesso! ID: {sid}")
                return
            except ValueError as err:
                if not _perguntar_tentar_novamente(str(err)):
                    return

    def _cancelar_festa(self):
        festas = self.db.listar_festas()
        if not festas:
            print("\nNenhuma festa agendada para cancelar.")
            return
        self._listar_festas()
        festa_id = _ler_int("\nID da Festa para cancelar (ou 0 para voltar): ", minimo=0)
        assert festa_id is not None
        if festa_id == 0:
            return
        _, msg = self.db.cancelar_festa(festa_id)
        print(msg)
