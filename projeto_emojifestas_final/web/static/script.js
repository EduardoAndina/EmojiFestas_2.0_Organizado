const state = {
  user: null,
  halls: [],
  combos: [],
  extras: [],
  clients: [],
  bookings: [],
  payments: [],
  calendarDate: new Date(),
};

const $ = (id) => document.getElementById(id);
const money = (value) => Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const dateBR = (value) => (value ? new Date(`${value}T12:00:00`).toLocaleDateString("pt-BR") : "—");
const initials = (name = "") => name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function toast(message, error = false) {
  const el = $("toast");
  el.textContent = message;
  el.classList.toggle("error", error);
  el.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove("show"), 3500);
}

async function api(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (_) {
    data = { error: text || `Erro HTTP ${res.status}` };
  }
  if (!res.ok) {
    throw new Error(data.error || data.message || `Erro HTTP ${res.status}`);
  }
  return data;
}

// LOGIN / SESSÃO
document.querySelectorAll(".chip-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    $("loginUser").value = btn.dataset.user;
    $("loginPass").value = btn.dataset.pass;
    $("loginForm").requestSubmit();
  });
});

$("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const fd = new FormData(e.target);
    const res = await api("/login", {
      method: "POST",
      body: JSON.stringify({ usuario: fd.get("usuario"), senha: fd.get("senha") }),
    });
    aplicarUsuario(res.usuario);
    toast(res.message);
    await loadAll();
  } catch (err) {
    toast(err.message, true);
  }
});

$("logoutButton").addEventListener("click", async () => {
  await api("/logout", { method: "POST" });
  state.user = null;
  $("appShell").classList.add("hidden");
  $("loginScreen").classList.remove("hidden");
});

function aplicarUsuario(user) {
  state.user = user;
  $("loginScreen").classList.add("hidden");
  $("appShell").classList.remove("hidden");
  $("userName").textContent = user.nome;
  $("welcomeName").textContent = user.nome.split(" ")[0];
  $("userRole").textContent = user.eh_proprietaria ? "Proprietária" : "Atendente";
  $("userAvatar").textContent = initials(user.nome);
  $("newHallButton").classList.toggle("hidden", !user.eh_proprietaria);
}

// NAVEGAÇÃO
function goTo(page) {
  document.querySelectorAll(".page-section").forEach((el) => el.classList.toggle("active", el.id === `page-${page}`));
  document.querySelectorAll(".nav-link").forEach((el) => el.classList.toggle("active", el.dataset.page === page));
  const active = document.querySelector(`.nav-link[data-page="${page}"]`);
  $("breadcrumbCurrent").textContent = active ? active.textContent.trim() : page;
  $("sidebar").classList.remove("open");
  if (page === "calendario") loadSpaceCalendar();
}

document.querySelectorAll("[data-page]").forEach((el) => el.addEventListener("click", () => goTo(el.dataset.page)));
document.querySelectorAll("[data-goto]").forEach((el) => el.addEventListener("click", () => goTo(el.dataset.goto)));
$("mobileMenu").addEventListener("click", () => $("sidebar").classList.toggle("open"));
$("refreshButton").addEventListener("click", loadAll);
$("todayLabel").textContent = new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long", year: "numeric" });

async function loadAll() {
  try {
    const [dashboard, halls, combos, extras, clients, bookings, payments] = await Promise.all([
      api("/dashboard"), api("/saloes"), api("/combos"), api("/extras"), api("/clientes"), api("/festas"), api("/pagamentos"),
    ]);
    state.halls = halls;
    state.combos = combos;
    state.extras = extras;
    state.clients = clients;
    state.bookings = bookings;
    state.payments = payments;

    renderDashboard(dashboard);
    renderBookings();
    renderClients();
    renderCatalog();
    renderPayments();
    renderReports();
    renderCalendar();
    populateSpaceFilter();
    await loadSpaceCalendar();
  } catch (err) {
    toast(err.message, true);
  }
}

function hallCard(h) {
  return `
    <div class="hall-card">
      <div class="hall-card-top">
        <div class="hall-symbol">✦</div>
        <div>
          <strong>${escapeHTML(h.nome)}</strong>
          <span class="hall-badge">Até ${h.capacidade} convidados · Acréscimo: ${money(h.acrescimo)}</span>
        </div>
      </div>
      ${h.endereco ? `<p class="hall-meta"><b>Endereço:</b> ${escapeHTML(h.endereco)}</p>` : ""}
      ${h.diferencial ? `<p class="hall-meta"><b>Diferencial:</b> ${escapeHTML(h.diferencial)}</p>` : ""}
      ${h.estrutura ? `<p class="hall-meta"><b>Estrutura:</b> ${escapeHTML(h.estrutura)}</p>` : ""}
    </div>
  `;
}

function renderDashboard(data) {
  $("statBookings").textContent = data.total_festas;
  $("statClients").textContent = data.total_clientes;
  $("statRevenue").textContent = money(data.valor_contratado);
  $("statReceived").textContent = money(data.valor_recebido);

  const upcoming = [...state.bookings].slice(0, 5);
  $("dashboardAgenda").innerHTML = upcoming.length
    ? upcoming.map((b) => `
      <div class="agenda-item">
        <div class="agenda-time">${escapeHTML(b.inicio)}</div>
        <div class="agenda-marker"></div>
        <div class="agenda-info">
          <strong>${escapeHTML(b.titulo)} — ${escapeHTML(b.cliente_nome)}</strong>
          <small>${dateBR(b.data)} (${b.inicio} às ${b.fim})</small>
        </div>
        <span class="agenda-hall">${escapeHTML(b.salao_nome)}</span>
      </div>
    `).join("")
    : `<div class="empty-state">Nenhuma festa agendada ainda. Clique em "+ Novo agendamento".</div>`;

  $("dashboardHalls").innerHTML = state.halls.map(hallCard).join("");
}

function renderBookings(filter = "") {
  const q = filter.toLocaleLowerCase("pt-BR");
  const rows = state.bookings.filter((b) => `${b.cliente_nome} ${b.salao_nome} ${b.titulo}`.toLocaleLowerCase("pt-BR").includes(q));
  $("bookingsTable").innerHTML = rows.length
    ? rows.map((b) => {
        const status = b.restante <= 0 ? "Quitado" : b.pago > 0 ? "Pago" : "Pendente";
        const canCancel = state.user && state.user.eh_proprietaria;
        return `
          <tr>
            <td><strong>${escapeHTML(b.titulo)}</strong><span class="sub-cell">#${b.id} · ${b.duracao}h de duração</span></td>
            <td><div class="person-cell"><span class="person-dot">${escapeHTML(initials(b.cliente_nome))}</span><strong>${escapeHTML(b.cliente_nome)}</strong></div></td>
            <td>${escapeHTML(b.salao_nome)}</td>
            <td>${dateBR(b.data)}<span class="sub-cell">${escapeHTML(b.inicio)} às ${escapeHTML(b.fim)}</span></td>
            <td><strong>${money(b.total)}</strong></td>
            <td><span class="status ${status.toLowerCase()}">${status}</span></td>
            <td>${canCancel ? `<button class="danger-mini" onclick="cancelarFesta(${b.id})">Cancelar</button>` : "—"}</td>
          </tr>
        `;
      }).join("")
    : `<tr><td colspan="7" class="empty-state">Nenhum agendamento encontrado.</td></tr>`;
}

window.cancelarFesta = async function (id) {
  if (!confirm(`Deseja realmente cancelar a Festa #${id}?`)) return;
  try {
    const res = await api(`/festas/${id}`, { method: "DELETE" });
    toast(res.message);
    await loadAll();
  } catch (err) {
    toast(err.message, true);
  }
};

function renderClients(filter = "") {
  const q = filter.toLocaleLowerCase("pt-BR");
  const rows = state.clients.filter((c) => `${c.nome} ${c.contato} ${c.documento}`.toLocaleLowerCase("pt-BR").includes(q));
  $("clientsTable").innerHTML = rows.length
    ? rows.map((c) => `
      <tr>
        <td><div class="person-cell"><span class="person-dot">${escapeHTML(initials(c.nome))}</span><strong>${escapeHTML(c.nome)}</strong></div></td>
        <td>${escapeHTML(c.contato)}</td>
        <td>${escapeHTML(c.documento)}</td>
        <td>#${c.id}</td>
      </tr>
    `).join("")
    : `<tr><td colspan="4" class="empty-state">Nenhum cliente encontrado.</td></tr>`;
}

function renderCatalog() {
  $("hallsGrid").innerHTML = state.halls.map(hallCard).join("");
  $("combosList").innerHTML = state.combos.map((c) => `
    <div class="catalog-item">
      <div><strong>${escapeHTML(c.nome)}</strong><small>${escapeHTML(c.descricao)}</small></div>
      <span class="catalog-price">${money(c.preco)}</span>
    </div>
  `).join("");
  $("extrasList").innerHTML = state.extras.map((e) => `
    <div class="catalog-item">
      <div><strong>${escapeHTML(e.nome)}</strong><small>Item opcional</small></div>
      <span class="catalog-price">${money(e.preco)}</span>
    </div>
  `).join("");
}

function renderPayments() {
  const total = state.bookings.reduce((s, b) => s + Number(b.total || 0), 0);
  const received = state.bookings.reduce((s, b) => s + Number(b.pago || 0), 0);
  $("payTotal").textContent = money(total);
  $("payReceived").textContent = money(received);
  $("payPending").textContent = money(Math.max(0, total - received));

  $("paymentsTable").innerHTML = state.bookings.length
    ? state.bookings.map((b) => {
        const status = b.restante <= 0 ? "Quitado" : b.pago > 0 ? "Pago" : "Pendente";
        return `
          <tr>
            <td><strong>${escapeHTML(b.cliente_nome)}</strong></td>
            <td>${escapeHTML(b.titulo)}<span class="sub-cell">${escapeHTML(b.salao_nome)} · ${dateBR(b.data)}</span></td>
            <td>${money(b.total)}</td>
            <td>${money(b.pago)}</td>
            <td>${money(b.restante)}</td>
            <td><span class="status ${status.toLowerCase()}">${status}</span></td>
          </tr>
        `;
      }).join("")
    : `<tr><td colspan="6" class="empty-state">Nenhuma festa cadastrada.</td></tr>`;
}

function renderReports() {
  $("reportBookings").textContent = state.bookings.length;
  $("reportClients").textContent = state.clients.length;
  $("reportRevenue").textContent = money(state.bookings.reduce((s, b) => s + Number(b.total || 0), 0));
  $("reportExtras").textContent = state.extras.length;

  const counts = state.halls.map((h) => ({
    name: h.nome,
    count: state.bookings.filter((b) => Number(b.salao_id) === Number(h.id)).length,
  }));
  const max = Math.max(1, ...counts.map((x) => x.count));
  $("reportHallRows").innerHTML = counts.map((x) => `
    <div class="report-row">
      <span>${escapeHTML(x.name)}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${(x.count / max) * 100}%"></div></div>
      <strong>${x.count}</strong>
    </div>
  `).join("");
}

// CALENDÁRIO GERAL (DASHBOARD)
function renderCalendar() {
  const d = state.calendarDate;
  const year = d.getFullYear();
  const month = d.getMonth();
  $("calendarMonth").textContent = d.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
  const first = new Date(year, month, 1).getDay();
  const days = new Date(year, month + 1, 0).getDate();
  const prevDays = new Date(year, month, 0).getDate();
  const today = new Date();
  let html = "";
  for (let i = 0; i < 42; i++) {
    let day, dateObj, muted = false;
    if (i < first) { day = prevDays - first + i + 1; dateObj = new Date(year, month - 1, day); muted = true; }
    else if (i >= first + days) { day = i - first - days + 1; dateObj = new Date(year, month + 1, day); muted = true; }
    else { day = i - first + 1; dateObj = new Date(year, month, day); }
    const iso = `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(2, "0")}-${String(dateObj.getDate()).padStart(2, "0")}`;
    const isToday = dateObj.toDateString() === today.toDateString();
    const has = state.bookings.some((b) => b.data === iso);
    html += `<button class="calendar-day ${muted ? "muted-day" : ""} ${isToday ? "today" : ""} ${has ? "has-event" : ""}">${day}</button>`;
  }
  $("calendarDays").innerHTML = html;
}
$("prevMonth").addEventListener("click", () => { state.calendarDate.setMonth(state.calendarDate.getMonth() - 1); renderCalendar(); });
$("nextMonth").addEventListener("click", () => { state.calendarDate.setMonth(state.calendarDate.getMonth() + 1); renderCalendar(); });

// CALENDÁRIO DEDICADO POR ESPAÇO (USA CalendarioSalao DO BACKEND)
function populateSpaceFilter() {
  const select = $("calSpaceSelect");
  const current = select.value;
  select.innerHTML = state.halls.map((h) => `<option value="${h.id}">${escapeHTML(h.nome)}</option>`).join("");
  if (current) select.value = current;
  if (!$("calYearInput").value) {
    const hoje = new Date();
    $("calYearInput").value = hoje.getFullYear();
    $("calMonthSelect").value = String(hoje.getMonth() + 1);
  }
}

async function loadSpaceCalendar() {
  if (!state.halls.length) return;
  const salaoId = $("calSpaceSelect").value || state.halls[0].id;
  const ano = $("calYearInput").value || new Date().getFullYear();
  const mes = $("calMonthSelect").value || (new Date().getMonth() + 1);
  try {
    const cal = await api(`/calendario?salao_id=${salaoId}&ano=${ano}&mes=${mes}`);
    $("spaceCalTitle").textContent = `${cal.salao_nome} — ${cal.nome_mes}/${cal.ano}`;
    let html = "";
    for (let i = 0; i < cal.dia_inicio_semana; i++) {
      html += `<span class="calendar-day muted-day"></span>`;
    }
    for (let d = 1; d <= cal.total_dias; d++) {
      const ocupado = cal.dias_ocupados.includes(d);
      html += `<button class="calendar-day ${ocupado ? "has-event" : ""}" title="${ocupado ? "Dia com reserva" : "Dia livre"}">${String(d).padStart(2, "0")}</button>`;
    }
    $("spaceCalendarDays").innerHTML = html;

    $("spaceReservationsList").innerHTML = cal.reservas.length
      ? cal.reservas.map((r) => `
        <div class="agenda-item">
          <div class="agenda-time">Dia ${String(r.dia).padStart(2, "0")}</div>
          <div class="agenda-marker"></div>
          <div class="agenda-info">
            <strong>${escapeHTML(r.cliente_nome)}</strong>
            <small>${dateBR(r.data)} · ${r.inicio} às ${r.fim}</small>
          </div>
          <span class="agenda-hall">Reservado #${r.id}</span>
        </div>
      `).join("")
      : `<div class="empty-state">Nenhuma reserva em ${escapeHTML(cal.salao_nome)} neste mês. Todos os dias livres!</div>`;
  } catch (err) {
    toast(err.message, true);
  }
}

$("calSpaceSelect").addEventListener("change", loadSpaceCalendar);
$("calMonthSelect").addEventListener("change", loadSpaceCalendar);
$("calYearInput").addEventListener("change", loadSpaceCalendar);
$("bookingSearch").addEventListener("input", (e) => renderBookings(e.target.value));
$("clientSearch").addEventListener("input", (e) => renderClients(e.target.value));

// MODAIS
function openModal(title, html, onSubmit) {
  $("modalTitle").textContent = title;
  $("modalBody").innerHTML = html;
  $("modalBackdrop").classList.add("open");
  const form = $("modalBody").querySelector("form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = form.querySelector('[type="submit"]');
      if (btn) btn.disabled = true;
      try {
        await onSubmit(new FormData(form));
        $("modalBackdrop").classList.remove("open");
      } catch (err) {
        toast(err.message, true);
      } finally {
        if (btn) btn.disabled = false;
      }
    });
  }
}
document.addEventListener("click", (e) => {
  if (e.target.id === "closeModal" || e.target.id === "modalBackdrop" || e.target.classList.contains("cancel-modal")) {
    $("modalBackdrop").classList.remove("open");
  }
});

$("newClientButton").addEventListener("click", () => {
  openModal("Cadastrar cliente", `
    <form><div class="form-grid">
      <div class="form-field full"><label>Nome completo</label><input class="form-control" name="nome" required placeholder="Ex.: maria da silva (formata automático)"></div>
      <div class="form-field"><label>Celular com DDD</label><input class="form-control" name="contato" required placeholder="Ex.: 51980623155"></div>
      <div class="form-field"><label>CPF válido</label><input class="form-control" name="documento" required placeholder="000.000.000-00"></div>
    </div><div class="form-actions"><button type="button" class="secondary-button cancel-modal">Cancelar</button><button class="primary-button" type="submit">Salvar cliente</button></div></form>
  `, async (fd) => {
    const res = await api("/clientes", { method: "POST", body: JSON.stringify(Object.fromEntries(fd)) });
    toast(res.message);
    await loadAll();
    goTo("clientes");
  });
});

$("newHallButton").addEventListener("click", () => {
  openModal("Cadastrar novo espaço", `
    <form><div class="form-grid">
      <div class="form-field full"><label>Nome do espaço</label><input class="form-control" name="nome" required placeholder="Ex.: Espaço 4 — Garden"></div>
      <div class="form-field"><label>Capacidade máxima</label><input class="form-control" type="number" name="capacidade" min="1" required placeholder="Ex.: 90"></div>
      <div class="form-field"><label>Acréscimo (R$)</label><input class="form-control" type="number" name="acrescimo" min="0" step="0.01" value="0" required></div>
      <div class="form-field full"><label>Endereço</label><input class="form-control" name="endereco" placeholder="Rua / Avenida e bairro"></div>
      <div class="form-field full"><label>Diferencial</label><input class="form-control" name="diferencial" placeholder="Ex.: Área Kids, pista de dança..."></div>
      <div class="form-field full"><label>Estrutura</label><input class="form-control" name="estrutura" placeholder="Ex.: 3 banheiros, climatizado..."></div>
    </div><div class="form-actions"><button type="button" class="secondary-button cancel-modal">Cancelar</button><button class="primary-button" type="submit">Salvar espaço</button></div></form>
  `, async (fd) => {
    const res = await api("/saloes", { method: "POST", body: JSON.stringify(Object.fromEntries(fd)) });
    toast(res.message);
    await loadAll();
    goTo("saloes");
  });
});

function showBookingModal() {
  if (!state.halls.length || !state.clients.length) {
    toast("Cadastre ao menos um espaço e um cliente primeiro.", true);
    return;
  }
  const hallOptions = state.halls.map((h) => `<option value="${h.id}">${escapeHTML(h.nome)} — até ${h.capacidade} conv.</option>`).join("");
  const clientOptions = state.clients.map((c) => `<option value="${c.id}">${escapeHTML(c.nome)} (${escapeHTML(c.documento)})</option>`).join("");
  const comboOptions = `<option value="">Sem combo</option>` + state.combos.map((c) => `<option value="${c.id}">${escapeHTML(c.nome)} — ${money(c.preco)}</option>`).join("");
  const extraOptions = state.extras.map((e) => `<label class="check-option"><input type="checkbox" name="extras" value="${e.id}"> ${escapeHTML(e.nome)} (${money(e.preco)})</label>`).join("");

  openModal("Novo agendamento", `
    <form><div class="form-grid">
      <div class="form-field full"><label>Cliente</label><select class="form-control" name="cliente_id" required>${clientOptions}</select></div>
      <div class="form-field"><label>Espaço</label><select class="form-control" name="salao_id" required>${hallOptions}</select></div>
      <div class="form-field"><label>Data da festa</label><input class="form-control" type="date" name="data" min="${new Date().toISOString().slice(0, 10)}" required></div>
      <div class="form-field"><label>Horário de início</label><input class="form-control" type="time" name="inicio" required></div>
      <div class="form-field"><label>Horas extras (R$ 200/h)</label><input class="form-control" type="number" name="horas_extra" min="0" value="0"></div>
      <div class="form-field full"><label>Combo</label><select class="form-control" name="combo_id">${comboOptions}</select></div>
      <div class="form-field full"><label>Serviços adicionais</label><div class="extras-options">${extraOptions}</div></div>
      <div class="form-field full"><label>Observações</label><textarea class="form-control" name="obs" rows="2" placeholder="Tema da festa, detalhes..."></textarea></div>
    </div><div class="form-actions"><button type="button" class="secondary-button cancel-modal">Cancelar</button><button class="primary-button" type="submit">Confirmar agendamento</button></div></form>
  `, async (fd) => {
    const payload = {
      cliente_id: Number(fd.get("cliente_id")),
      salao_id: Number(fd.get("salao_id")),
      data: fd.get("data"),
      inicio: fd.get("inicio"),
      combo_id: fd.get("combo_id") ? Number(fd.get("combo_id")) : null,
      horas_extra: Number(fd.get("horas_extra") || 0),
      extras_ids: fd.getAll("extras").map(Number),
      obs: fd.get("obs") || "",
    };
    const res = await api("/festas", { method: "POST", body: JSON.stringify(payload) });
    toast(res.message);
    await loadAll();
    goTo("agendamentos");
  });
}

$("newBookingButton").addEventListener("click", showBookingModal);
$("quickNewBooking").addEventListener("click", showBookingModal);

$("newPaymentButton").addEventListener("click", () => {
  const pendentes = state.bookings.filter((b) => b.restante > 0);
  if (!pendentes.length) {
    toast("Não há festas com saldo pendente no momento.", true);
    return;
  }
  const options = pendentes.map((b) => `<option value="${b.id}">#${b.id} — ${escapeHTML(b.cliente_nome)} (${escapeHTML(b.salao_nome)}) — Falta ${money(b.restante)}</option>`).join("");
  openModal("Registrar pagamento", `
    <form><div class="form-grid">
      <div class="form-field full"><label>Festa</label><select class="form-control" name="festa_id" required>${options}</select></div>
      <div class="form-field"><label>Valor (R$)</label><input class="form-control" type="text" name="valor" required placeholder="Ex.: 500,00"></div>
      <div class="form-field"><label>Data do pagamento</label><input class="form-control" type="date" name="data" value="${new Date().toISOString().slice(0, 10)}" required></div>
      <div class="form-field full"><label>Tipo</label><select class="form-control" name="tipo"><option value="Sinal">Sinal</option><option value="Parcela">Parcela</option><option value="Quitação">Quitação</option></select></div>
    </div><div class="form-actions"><button type="button" class="secondary-button cancel-modal">Cancelar</button><button class="primary-button" type="submit">Salvar pagamento</button></div></form>
  `, async (fd) => {
    const res = await api("/pagamentos", {
      method: "POST",
      body: JSON.stringify({
        festa_id: Number(fd.get("festa_id")),
        valor: fd.get("valor"),
        data: fd.get("data"),
        tipo: fd.get("tipo"),
      }),
    });
    toast(res.message);
    await loadAll();
    goTo("pagamentos");
  });
});

(async function init() {
  try {
    const sess = await api("/sessao");
    if (sess.logado && sess.usuario) {
      aplicarUsuario(sess.usuario);
      await loadAll();
    }
  } catch (err) {
    console.error(err);
  }
})();
