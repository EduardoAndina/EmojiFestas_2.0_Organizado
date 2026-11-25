import sqlite3
from datetime import date, datetime
from app.config import DB_FILE
from models.entidades import (
    Cliente,
    Combo,
    Extra,
    Festa,
    Funcionario,
    Pagamento,
    Salao,
)


class Banco:
    def __init__(self, db_path=None):
        caminho = db_path or DB_FILE
        self.conn = sqlite3.connect(caminho, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._criar_tabelas()
        if not self._tem_dados():
            self._dados_iniciais()

    def _criar_tabelas(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS funcionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                perfil TEXT NOT NULL,
                ativo INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS saloes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                capacidade INTEGER NOT NULL,
                acrescimo REAL NOT NULL,
                endereco TEXT DEFAULT '',
                diferencial TEXT DEFAULT '',
                estrutura TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS combos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                descricao TEXT
            );
            CREATE TABLE IF NOT EXISTS extras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                contato TEXT,
                documento TEXT
            );
            CREATE TABLE IF NOT EXISTS festas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salao_id INTEGER NOT NULL,
                cliente_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                inicio TEXT NOT NULL,
                combo_id INTEGER,
                horas_extra INTEGER DEFAULT 0,
                total REAL NOT NULL,
                obs TEXT,
                FOREIGN KEY (salao_id) REFERENCES saloes(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (combo_id) REFERENCES combos(id)
            );
            CREATE TABLE IF NOT EXISTS festa_extras (
                festa_id INTEGER NOT NULL,
                extra_id INTEGER NOT NULL,
                PRIMARY KEY (festa_id, extra_id),
                FOREIGN KEY (festa_id) REFERENCES festas(id) ON DELETE CASCADE,
                FOREIGN KEY (extra_id) REFERENCES extras(id)
            );
            CREATE TABLE IF NOT EXISTS pagamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                festa_id INTEGER NOT NULL,
                valor REAL NOT NULL,
                data TEXT NOT NULL,
                tipo TEXT NOT NULL,
                FOREIGN KEY (festa_id) REFERENCES festas(id) ON DELETE CASCADE
            );
        """)
        self.conn.commit()

    def _tem_dados(self) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM saloes")
        return cursor.fetchone()[0] > 0

    def _dados_iniciais(self):
        cursor = self.conn.cursor()
        cursor.executemany(
            "INSERT INTO funcionarios (id, nome, usuario, senha, perfil, ativo) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, "Marina Reis", "marina", "1234", "proprietaria", 1),
                (2, "Lucas Silva", "lucas", "1234", "atendente", 1),
            ],
        )
        cursor.executemany(
            """
            INSERT INTO saloes (id, nome, capacidade, acrescimo, endereco, diferencial, estrutura)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    1,
                    "Espaço 1 — Amplitude e Diversão Máxima",
                    100,
                    600.0,
                    "Av. Imperatriz Leopoldina - São Leopoldo",
                    "Área Kids com mais de 20 variedades de brinquedos",
                    "30 a 100 convidados | 4 banheiros, ambiente climatizado e estacionamento no local",
                ),
                (
                    2,
                    "Espaço 2 — Aconchegante e Intimista",
                    50,
                    0.0,
                    "Av. Imperatriz Leopoldina - São Leopoldo",
                    "Ambiente acolhedor com brinquedos para todas as idades",
                    "30 a 50 convidados (máx. 15 crianças pagantes) | 2 banheiros, climatizado e estacionamento",
                ),
                (
                    3,
                    "Espaço 3 — Moderno, Clean e Festivo",
                    80,
                    350.0,
                    "Rua Osvaldo Aranha, 68 - Centro, São Leopoldo",
                    "Pista de dança e bar integrados (ideal 15 anos, formaturas e casamentos)",
                    "30 a 80 convidados | 3 banheiros, ambiente climatizado e design clean",
                ),
            ],
        )
        cursor.executemany(
            "INSERT INTO combos (id, nome, preco, descricao) VALUES (?, ?, ?, ?)",
            [
                (1, "Básico", 1500.0, "Decoração simples, entradinhas inclusas e salgadinhos à vontade"),
                (2, "Festa", 2500.0, "Decoração completa, equipe especializada, buffet completo e bolo"),
                (3, "Mega", 3800.0, "Tudo do Festa + pista/brinquedos extras e animador"),
            ],
        )
        cursor.executemany(
            "INSERT INTO extras (id, nome, preco) VALUES (?, ?, ?)",
            [
                (1, "Salgados Extras", 350.0),
                (2, "Pacote Bebidas", 250.0),
                (3, "Pula-pula / Brinquedo", 400.0),
                (4, "Bolo Temático", 300.0),
                (5, "Animador / DJ", 450.0),
            ],
        )
        cursor.executemany(
            "INSERT INTO clientes (id, nome, contato, documento) VALUES (?, ?, ?, ?)",
            [
                (1, "Juliana Prado", "(51) 98888-1111", "123.456.789-00"),
                (2, "Rafael Mendes", "(51) 97777-2222", "987.654.321-00"),
            ],
        )
        self.conn.commit()

    def autenticar(self, usuario: str, senha: str) -> Funcionario | None:
        row = self.conn.execute(
            "SELECT id, nome, usuario, perfil, ativo FROM funcionarios WHERE usuario = ? AND senha = ? AND ativo = 1",
            (usuario.strip(), senha.strip()),
        ).fetchone()
        if not row:
            return None
        dados = dict(row)
        dados["ativo"] = bool(dados["ativo"])
        return Funcionario(**dados)

    def listar_saloes(self) -> list[Salao]:
        rows = self.conn.execute("SELECT * FROM saloes ORDER BY id").fetchall()
        return [Salao(**dict(row)) for row in rows]

    def listar_combos(self) -> list[Combo]:
        rows = self.conn.execute("SELECT * FROM combos ORDER BY id").fetchall()
        return [Combo(**dict(row)) for row in rows]

    def listar_extras(self) -> list[Extra]:
        rows = self.conn.execute("SELECT * FROM extras ORDER BY id").fetchall()
        return [Extra(**dict(row)) for row in rows]

    def listar_clientes(self) -> list[Cliente]:
        rows = self.conn.execute("SELECT * FROM clientes ORDER BY id").fetchall()
        return [Cliente(**dict(row)) for row in rows]

    def listar_festas(self, salao_id: int | None = None) -> list[Festa]:
        if salao_id is not None:
            rows = self.conn.execute(
                "SELECT * FROM festas WHERE salao_id = ? ORDER BY data, inicio",
                (salao_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM festas ORDER BY data, inicio"
            ).fetchall()

        festas = []
        for row in rows:
            festa_dict = dict(row)
            extras_rows = self.conn.execute(
                "SELECT extra_id FROM festa_extras WHERE festa_id = ? ORDER BY extra_id",
                (festa_dict["id"],),
            ).fetchall()
            festa_dict["extras"] = [extra["extra_id"] for extra in extras_rows]
            festas.append(Festa(**festa_dict))
        return festas

    def listar_festas_por_salao_e_mes(self, salao_id: int, ano: int, mes: int) -> list[Festa]:
        prefixo = f"{ano:04d}-{mes:02d}-%"
        rows = self.conn.execute(
            "SELECT * FROM festas WHERE salao_id = ? AND data LIKE ? ORDER BY data, inicio",
            (salao_id, prefixo),
        ).fetchall()
        festas = []
        for row in rows:
            festa_dict = dict(row)
            extras_rows = self.conn.execute(
                "SELECT extra_id FROM festa_extras WHERE festa_id = ? ORDER BY extra_id",
                (festa_dict["id"],),
            ).fetchall()
            festa_dict["extras"] = [extra["extra_id"] for extra in extras_rows]
            festas.append(Festa(**festa_dict))
        return festas

    def cliente(self, id_: int) -> Cliente | None:
        row = self.conn.execute("SELECT * FROM clientes WHERE id = ?", (id_,)).fetchone()
        return Cliente(**dict(row)) if row else None

    def salao(self, id_: int) -> Salao | None:
        row = self.conn.execute("SELECT * FROM saloes WHERE id = ?", (id_,)).fetchone()
        return Salao(**dict(row)) if row else None

    def combo(self, id_: int | None) -> Combo | None:
        if id_ is None:
            return None
        row = self.conn.execute("SELECT * FROM combos WHERE id = ?", (id_,)).fetchone()
        return Combo(**dict(row)) if row else None

    def extra(self, id_: int) -> Extra | None:
        row = self.conn.execute("SELECT * FROM extras WHERE id = ?", (id_,)).fetchone()
        return Extra(**dict(row)) if row else None

    def festa(self, id_: int) -> Festa | None:
        row = self.conn.execute("SELECT * FROM festas WHERE id = ?", (id_,)).fetchone()
        if not row:
            return None
        festa_dict = dict(row)
        extras_rows = self.conn.execute(
            "SELECT extra_id FROM festa_extras WHERE festa_id = ? ORDER BY extra_id",
            (id_,),
        ).fetchall()
        festa_dict["extras"] = [e["extra_id"] for e in extras_rows]
        return Festa(**festa_dict)

    def criar_salao(
        self,
        nome: str,
        capacidade: int,
        acrescimo: float,
        endereco: str = "",
        diferencial: str = "",
        estrutura: str = "",
    ) -> int:
        nome_formatado = nome.strip()
        if not nome_formatado:
            raise ValueError("O nome do espaço não pode ficar vazio!")
        if capacidade <= 0:
            raise ValueError("A capacidade deve ser maior que zero!")
        if acrescimo < 0:
            raise ValueError("O acréscimo não pode ser negativo!")

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO saloes (nome, capacidade, acrescimo, endereco, diferencial, estrutura)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                nome_formatado,
                capacidade,
                round(float(acrescimo), 2),
                endereco.strip(),
                diferencial.strip(),
                estrutura.strip(),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def cadastrar_cliente(self, nome: str, contato: str, documento: str) -> int:
        nome_limpo = nome.strip()
        contato_limpo = contato.strip()
        doc_limpo = documento.strip()
        if not nome_limpo:
            raise ValueError("O nome do cliente não pode ficar vazio!")
        if not doc_limpo:
            raise ValueError("O documento do cliente é obrigatório!")

        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO clientes (nome, contato, documento) VALUES (?, ?, ?)",
            (nome_limpo, contato_limpo, doc_limpo),
        )
        self.conn.commit()
        return cursor.lastrowid

    def agendar_festa(
        self,
        salao_id: int,
        cliente_id: int,
        data_evento: str,
        inicio: str,
        combo_id: int | None,
        extras_ids: list[int],
        horas_extra: int,
        obs: str,
    ) -> tuple[bool, str]:
        salao = self.salao(salao_id)
        if not salao:
            return False, "Espaço não encontrado!"

        cliente = self.cliente(cliente_id)
        if not cliente:
            return False, "Cliente não encontrado!"

        combo = self.combo(combo_id)
        if combo_id is not None and not combo:
            return False, "Combo informado não existe!"

        if horas_extra < 0:
            return False, "Horas extras não podem ser negativas!"

        data_limpa = data_evento.strip()
        inicio_limpo = inicio.strip()
        try:
            date.fromisoformat(data_limpa)
            datetime.fromisoformat(f"{data_limpa}T{inicio_limpo}")
        except ValueError:
            return False, "Data ou horário inválido! Use AAAA-MM-DD (ex: 2026-12-20) e HH:MM (ex: 14:00)."

        extras_unicos = list(dict.fromkeys(extras_ids))
        extras_objs = []
        for eid in extras_unicos:
            ext = self.extra(eid)
            if not ext:
                return False, f"Extra ID {eid} não encontrado!"
            extras_objs.append(ext)

        total = Festa.calcular_orcamento(salao, combo, extras_objs, horas_extra)
        nova_festa = Festa(
            id=0,
            salao_id=salao_id,
            cliente_id=cliente_id,
            data=data_limpa,
            inicio=inicio_limpo,
            combo_id=combo_id,
            horas_extra=horas_extra,
            total=total,
            obs=obs.strip(),
            extras=extras_unicos,
        )

        for festa_existente in self.listar_festas(salao_id=salao_id):
            if nova_festa.conflita_com(festa_existente):
                return (
                    False,
                    f"DUPLICAÇÃO BLOQUEADA! O '{salao.nome}' já possui reserva neste horário "
                    f"(Festa #{festa_existente.id}: {festa_existente.data} das {festa_existente.inicio} às {festa_existente.hora_fim_str()}).",
                )

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO festas (salao_id, cliente_id, data, inicio, combo_id, horas_extra, total, obs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                salao_id,
                cliente_id,
                data_limpa,
                inicio_limpo,
                combo_id,
                horas_extra,
                total,
                obs.strip(),
            ),
        )
        festa_id = cursor.lastrowid

        for extra_id in extras_unicos:
            cursor.execute(
                "INSERT INTO festa_extras (festa_id, extra_id) VALUES (?, ?)",
                (festa_id, extra_id),
            )

        self.conn.commit()
        return (
            True,
            f"Festa #{festa_id} agendada com sucesso para {cliente.nome} no {salao.nome} "
            f"({data_limpa} das {inicio_limpo} às {nova_festa.hora_fim_str()})! Total: R$ {total:,.2f}",
        )

    def cancelar_festa(self, festa_id: int) -> tuple[bool, str]:
        festa = self.festa(festa_id)
        if not festa:
            return False, "Festa não encontrada!"
        self.conn.execute("DELETE FROM festas WHERE id = ?", (festa_id,))
        self.conn.commit()
        return True, f"Festa #{festa_id} cancelada e removida da agenda."

    def listar_pagamentos(self, festa_id: int) -> list[Pagamento]:
        rows = self.conn.execute(
            "SELECT * FROM pagamentos WHERE festa_id = ? ORDER BY id", (festa_id,)
        ).fetchall()
        return [Pagamento(**dict(row)) for row in rows]

    def total_pago(self, festa_id: int) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(valor), 0) AS soma FROM pagamentos WHERE festa_id = ?",
            (festa_id,),
        ).fetchone()
        return round(float(row["soma"]), 2)

    def registrar_pagamento(
        self, festa_id: int, valor: float, tipo: str = "Parcela", data_pagamento: str | None = None
    ) -> tuple[bool, str]:
        festa = self.festa(festa_id)
        if not festa:
            return False, "Festa não encontrada!"
        if valor <= 0:
            return False, "O valor do pagamento deve ser maior que zero!"

        valor_limpo = round(float(valor), 2)
        ja_pago = self.total_pago(festa_id)
        restante = round(festa.total - ja_pago, 2)
        if restante <= 0:
            return False, "Esta festa já está 100% quitada!"
        if valor_limpo > restante:
            return False, f"Valor excede o saldo devedor atual (R$ {restante:,.2f})."

        data_reg = data_pagamento.strip() if data_pagamento else date.today().isoformat()
        date.fromisoformat(data_reg)

        self.conn.execute(
            "INSERT INTO pagamentos (festa_id, valor, data, tipo) VALUES (?, ?, ?, ?)",
            (festa_id, valor_limpo, data_reg, tipo.strip() or "Parcela"),
        )
        self.conn.commit()

        novo_saldo = round(restante - valor_limpo, 2)
        status = "QUITADA" if novo_saldo == 0 else f"Saldo restante: R$ {novo_saldo:,.2f}"
        return True, f"Pagamento de R$ {valor_limpo:,.2f} registrado! ({status})"

    def fechar(self):
        self.conn.close()
