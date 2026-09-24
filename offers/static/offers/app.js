(() => {
  const root = document.getElementById("sheet");
  if (!root) return;

  const tbody = document.querySelector("#grid tbody");
  const status = document.getElementById("status");
  const modal = document.getElementById("search-modal");
  const searchQ = document.getElementById("search-q");
  const searchList = document.getElementById("search-list");
  let lines = JSON.parse(document.getElementById("offer-lines").textContent);
  let activeIndex = 0;

  function fmt(n) {
    if (n === "" || n == null) return "";
    const x = Number(n);
    if (Number.isNaN(x)) return "";
    return x.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function paintMetrics(m) {
    if (!m) return;
    document.getElementById("m-wartosc").textContent = fmt(m.wartosc);
    document.getElementById("m-koszt").textContent = fmt(m.koszt);
    document.getElementById("m-zysk").textContent = fmt(m.zysk);
    document.getElementById("m-marza").textContent = fmt(m.marza);
  }

  function render() {
    const photos = document.getElementById("with-photos").checked;
    tbody.innerHTML = "";
    lines.forEach((line, i) => {
      const tr = document.createElement("tr");
      tr.className = "item";
      const photo = document.createElement("td");
      photo.dataset.label = "Zdjęcie";
      if (photos && line.zdjecie) {
        const img = document.createElement("img");
        img.className = "photo";
        img.src = line.zdjecie;
        img.alt = "";
        photo.appendChild(img);
      } else {
        const box = document.createElement("div");
        box.className = "photo" + (photos && line.combi ? " on" : "");
        photo.appendChild(box);
      }
      const opis = document.createElement("td");
      opis.dataset.label = "Opis";
      const opisEl = document.createElement("div");
      opisEl.className = "opis";
      opisEl.tabIndex = 0;
      opisEl.textContent = line.opis || "";
      opisEl.title = "Dwuklik — szukaj produktu";
      opisEl.addEventListener("dblclick", () => openSearch(i));
      opisEl.addEventListener("click", () => {
        if (window.matchMedia("(pointer: coarse)").matches) openSearch(i);
      });
      opis.appendChild(opisEl);

      function cell(field, readonly, label) {
        const td = document.createElement("td");
        td.dataset.label = label;
        const input = document.createElement("input");
        if (["cena", "netto", "wartosc"].includes(field)) input.value = fmt(line[field]);
        else if (field === "rabat") input.value = line.rabat || "";
        else if (field === "ilosc") input.value = line.ilosc || "";
        else input.value = line[field] || "";
        input.readOnly = !!readonly;
        if (!readonly) {
          input.addEventListener("change", () => {
            line[field] = input.value.replace(",", ".");
            line.edited = field;
            save();
          });
        }
        td.appendChild(input);
        return td;
      }

      tr.append(
        photo,
        opis,
        cell("cena", true, "Cena katalogowa netto"),
        cell("rabat", false, "Rabat %"),
        cell("netto", true, "Cena netto dla Ciebie"),
        cell("ilosc", false, "Ilość"),
        cell("wartosc", true, "Wartość netto")
      );
      tbody.appendChild(tr);

      const mr = document.createElement("tr");
      mr.className = "margin-row";
      const td = document.createElement("td");
      td.colSpan = 7;
      const wrap = document.createElement("div");
      wrap.className = "margin-line";
      wrap.innerHTML = "";
      const koszt = document.createElement("span");
      koszt.textContent = `Koszt ${fmt(line.koszt) || "—"} zł`;
      wrap.appendChild(koszt);
      const label = document.createElement("label");
      label.textContent = "Marża % ";
      const marza = document.createElement("input");
      marza.value = line.marza || "";
      marza.addEventListener("change", () => {
        line.marza = marza.value.replace(",", ".");
        line.edited = "marza";
        save();
      });
      label.appendChild(marza);
      wrap.appendChild(label);
      const zyskSzt = document.createElement("span");
      zyskSzt.textContent = `Zysk/szt. ${fmt(line.zysk_szt) || "—"} zł`;
      const zysk = document.createElement("span");
      zysk.textContent = `Zysk ${fmt(line.zysk) || "—"} zł`;
      wrap.append(zyskSzt, zysk);
      td.appendChild(wrap);
      mr.appendChild(td);
      tbody.appendChild(mr);
    });
  }

  function headerPayload() {
    return {
      nazwa: document.getElementById("nazwa").value,
      platnik_id: document.getElementById("platnik-id").value,
      platnik_nazwa: document.getElementById("platnik-nazwa").value,
      platnik_adres: document.getElementById("platnik-adres").value,
      platnik_nip: document.getElementById("platnik-nip").value,
      odbiorca_id: document.getElementById("odbiorca-id").value,
      odbiorca_nazwa: document.getElementById("odbiorca-nazwa").value,
      odbiorca_adres: document.getElementById("odbiorca-adres").value,
      with_photos: document.getElementById("with-photos").checked,
      show_codes: document.getElementById("show-codes").checked,
      koszt_transportu: document.getElementById("transport").value,
    };
  }

  async function save(extra = {}) {
    status.textContent = "Zapis…";
    const body = {
      ...headerPayload(),
      lines: lines.map((l) => ({
        id: l.id,
        combi: l.combi,
        rabat: l.rabat,
        marza: l.marza,
        ilosc: l.ilosc,
        edited: l.edited || "rabat",
      })),
      ...extra,
    };
    const res = await fetch(root.dataset.saveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": root.dataset.csrf,
      },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    lines = data.lines;
    paintMetrics(data.metrics);
    render();
    status.textContent = "Zapisano";
  }

  function openSearch(index) {
    activeIndex = index;
    modal.hidden = false;
    searchList.innerHTML = "";
    searchQ.value = "";
    searchQ.focus();
  }

  async function runSearch() {
    const q = searchQ.value.trim();
    const res = await fetch(root.dataset.searchUrl + "?q=" + encodeURIComponent(q));
    const data = await res.json();
    searchList.innerHTML = "";
    data.results.forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      searchList.appendChild(opt);
    });
    if (!data.results.length) {
      const opt = document.createElement("option");
      opt.disabled = true;
      opt.textContent = "Brak wyników";
      searchList.appendChild(opt);
    }
  }

  function insertSelected() {
    const value = searchList.value;
    if (!value) return;
    lines[activeIndex].combi = value;
    modal.hidden = true;
    save();
  }

  function bindClientBox(section, prefix) {
    const q = section.querySelector(".client-q");
    const list = section.querySelector(".client-list");
    const idField = section.querySelector(".client-id");
    async function search() {
      const res = await fetch(root.dataset.clientsUrl + "?q=" + encodeURIComponent(q.value));
      const data = await res.json();
      list.innerHTML = "";
      data.results.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = String(c.id);
        opt.textContent = c.nip ? `${c.nazwa} (NIP ${c.nip})` : c.nazwa;
        opt.dataset.nazwa = c.nazwa;
        opt.dataset.adres = c.adres;
        opt.dataset.nip = c.nip;
        list.appendChild(opt);
      });
    }
    q.addEventListener("input", () => {
      window.clearTimeout(q._t);
      q._t = window.setTimeout(search, 200);
    });
    q.addEventListener("focus", search);
    list.addEventListener("change", () => {
      const opt = list.selectedOptions[0];
      if (!opt) return;
      idField.value = opt.value;
      document.getElementById(`${prefix}-nazwa`).value = opt.dataset.nazwa || "";
      document.getElementById(`${prefix}-adres`).value = opt.dataset.adres || "";
      const nip = document.getElementById(`${prefix}-nip`);
      if (nip) nip.value = opt.dataset.nip || "";
      save();
    });
  }

  bindClientBox(document.querySelector('[data-role="platnik"]'), "platnik");
  bindClientBox(document.querySelector('[data-role="odbiorca"]'), "odbiorca");

  document.getElementById("copy-platnik").addEventListener("click", () => {
    document.getElementById("odbiorca-id").value = document.getElementById("platnik-id").value;
    document.getElementById("odbiorca-nazwa").value = document.getElementById("platnik-nazwa").value;
    document.getElementById("odbiorca-adres").value = document.getElementById("platnik-adres").value;
    save();
  });

  document.getElementById("btn-search").addEventListener("click", runSearch);
  searchQ.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      runSearch();
    }
  });
  searchList.addEventListener("dblclick", insertSelected);
  document.getElementById("btn-insert").addEventListener("click", insertSelected);
  document.getElementById("btn-cancel").addEventListener("click", () => {
    modal.hidden = true;
  });
  ["nazwa", "platnik-nazwa", "platnik-adres", "platnik-nip", "odbiorca-nazwa", "odbiorca-adres"].forEach((id) => {
    document.getElementById(id).addEventListener("change", () => save());
  });
  document.getElementById("with-photos").addEventListener("change", () => save());
  document.getElementById("show-codes").addEventListener("change", () => save());
  document.getElementById("transport").addEventListener("change", () => save());
  document.getElementById("menu-toggle").addEventListener("click", () => {
    const bar = document.getElementById("toolbar");
    const open = bar.classList.toggle("is-open");
    document.getElementById("menu-toggle").setAttribute("aria-expanded", open ? "true" : "false");
  });
  document.getElementById("toggle-clients").addEventListener("click", () => {
    const wrap = document.getElementById("parties-wrap");
    wrap.open = !wrap.open;
  });
  document.getElementById("btn-add").addEventListener("click", () => {
    const n = window.prompt("Ile wierszy dodać do tabeli?", "5");
    if (!n) return;
    save({ add_rows: Number(n) });
  });
  document.getElementById("btn-clear").addEventListener("click", () => {
    if (window.confirm("Potwierdź usunięcie. Operacji nie można cofnąć.")) save({ clear: true });
  });
  document.getElementById("btn-pdf").addEventListener("click", () => {
    window.open(root.dataset.printUrl, "_blank");
  });
  document.getElementById("btn-xlsx").addEventListener("click", async () => {
    await save();
    window.location = root.dataset.excelUrl;
  });

  render();
})();
