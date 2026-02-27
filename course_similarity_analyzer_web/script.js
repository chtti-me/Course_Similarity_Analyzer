/**
 * Course Similarity Analyzer - 前端
 * ① 僅管理員 ②③④ 一般使用者可檢視；②④ 管理員可修改
 * 設定：Data/config.json（SUPABASE_URL, SUPABASE_ANON_KEY, API_BASE_URL）
 */

(function () {
  "use strict";

  let config = {
    SUPABASE_URL: "",
    SUPABASE_ANON_KEY: "",
    API_BASE_URL: "http://localhost:8000",
  };
  let supabaseClient = null;
  let userRole = null;

  // ---------- 載入設定 ----------
  async function loadConfig() {
    try {
      const r = await fetch("Data/config.json");
      const data = await r.json();
      config = { ...config, ...data };
    } catch (e) {
      console.warn("無法載入 Data/config.json，使用預設", e);
    }
    if (!config.SUPABASE_URL || !config.SUPABASE_ANON_KEY) {
      console.error("請在 Data/config.json 設定 SUPABASE_URL 與 SUPABASE_ANON_KEY");
      return;
    }
    supabaseClient = window.supabase.createClient(config.SUPABASE_URL, config.SUPABASE_ANON_KEY);
  }

  // ---------- 登入 / 角色 ----------
  async function getProfile() {
    const { data: { user } } = await supabaseClient.auth.getUser();
    if (!user) return null;
    const { data } = await supabaseClient.from("profiles").select("role").eq("id", user.id).single();
    return data ? data.role : "user";
  }

  async function refreshAuth() {
    const { data: { session } } = await supabaseClient.auth.getSession();
    const infoEl = document.getElementById("userInfo");
    const loginBtn = document.getElementById("btnLogin");
    const logoutBtn = document.getElementById("btnLogout");
    if (session) {
      userRole = await getProfile();
      infoEl.textContent = session.user.email + (userRole === "admin" ? " (管理員)" : "");
      loginBtn.hidden = true;
      logoutBtn.hidden = false;
    } else {
      userRole = null;
      infoEl.textContent = "";
      loginBtn.hidden = false;
      logoutBtn.hidden = true;
    }
    applyRoleVisibility();
  }

  function isAdmin() {
    return userRole === "admin";
  }

  /** 依角色隱藏「僅管理員」區塊 */
  function applyRoleVisibility() {
    document.querySelectorAll("[data-admin-only]").forEach(function (el) {
      if (isAdmin()) {
        el.classList.remove("hidden-by-role");
      } else {
        el.classList.add("hidden-by-role");
      }
    });
  }

  // ---------- 分頁切換 ----------
  function showPanel(panelId) {
    document.querySelectorAll(".panel").forEach(function (p) {
      p.hidden = true;
    });
    document.querySelectorAll(".tab").forEach(function (t) {
      t.classList.remove("active");
    });
    const panel = document.getElementById("panel-" + panelId);
    const tab = document.querySelector('.tab[data-tab="' + panelId + '"]');
    if (panel) panel.hidden = false;
    if (tab) tab.classList.add("active");
    if (panelId === "sync") renderSyncLog();
    if (panelId === "planning") renderPlanningList();
    if (panelId === "browse") renderBrowseTable();
  }

  // ---------- ① 同步紀錄 ----------
  async function renderSyncLog() {
    const el = document.getElementById("syncLog");
    el.textContent = "載入中…";
    const { data, error } = await supabaseClient.from("sync_log").select("*").order("run_at", { ascending: false }).limit(5);
    if (error) {
      el.textContent = "無法載入：" + error.message;
      return;
    }
    if (!data || data.length === 0) {
      el.textContent = "尚無同步紀錄。請在後端執行 sync_cli.py 並設定排程。";
      return;
    }
    el.innerHTML = data.map(function (row) {
      return "<div><strong>" + new Date(row.run_at).toLocaleString("zh-TW") + "</strong> " + (row.status || "") + " " + (row.message || "") + " 寫入 " + (row.courses_upserted || 0) + " 筆</div>";
    }).join("");
  }

  // ---------- ② 規劃中課程 ----------
  async function renderPlanningList() {
    const el = document.getElementById("planningList");
    el.innerHTML = "載入中…";
    const { data, error } = await supabaseClient
      .from("courses")
      .select("id,title,campus,instructor,start_date,audience,level,updated_at")
      .eq("status", "planning")
      .order("updated_at", { ascending: false });
    if (error) {
      el.innerHTML = "<p>無法載入：" + error.message + "</p>";
      return;
    }
    // 規劃中課程：顯示主要欄位（無班代號）
    let html =
      "<table><thead><tr><th>班名</th><th>校區</th><th>導師</th><th>開班日期</th><th>對象</th><th>難易度</th><th>更新時間</th>" +
      (isAdmin() ? "<th>操作</th>" : "") +
      "</tr></thead><tbody>";
    (data || []).forEach(function (row) {
      html +=
        "<tr><td>" +
        escapeHtml(row.title || "") +
        "</td><td>" +
        escapeHtml(row.campus || "") +
        "</td><td>" +
        escapeHtml(row.instructor || "") +
        "</td><td>" +
        escapeHtml(row.start_date || "") +
        "</td><td>" +
        escapeHtml(row.audience || "") +
        "</td><td>" +
        escapeHtml(row.level || "") +
        "</td><td>" +
        (row.updated_at ? new Date(row.updated_at).toLocaleString("zh-TW") : "") +
        "</td>";
      if (isAdmin()) {
        html +=
          '<td><button type="button" class="btn btn-ghost btn-edit-planning" data-id="' +
          escapeHtml(row.id) +
          '">編輯</button> <button type="button" class="btn btn-danger btn-delete-planning" data-id="' +
          escapeHtml(row.id) +
          '">刪除</button></td>';
      }
      html += "</tr>";
    });
    html += "</tbody></table>";
    el.innerHTML = html;
    el.querySelectorAll(".btn-edit-planning").forEach(function (btn) {
      btn.addEventListener("click", function () { openPlanningForm(btn.getAttribute("data-id")).catch(console.error); });
    });
    el.querySelectorAll(".btn-delete-planning").forEach(function (btn) {
      btn.addEventListener("click", function () { deletePlanning(btn.getAttribute("data-id")); });
    });
  }

  async function openPlanningForm(id) {
    const dialog = document.getElementById("planningFormDialog");
    document.getElementById("planningFormTitle").textContent = id ? "編輯規劃中課程" : "新增規劃中課程";
    document.getElementById("planningId").value = id || "";
    document.getElementById("planningTitle").value = "";
    document.getElementById("planningCampus").value = "";
    document.getElementById("planningInstructor").value = "";
    document.getElementById("planningStartDate").value = "";
    document.getElementById("planningAudience").value = "";
    document.getElementById("planningLevel").value = "";
    document.getElementById("planningDescription").value = "";
    if (id) {
      const { data: row } = await supabaseClient
        .from("courses")
        .select("title,campus,instructor,start_date,audience,level,description")
        .eq("id", id)
        .single();
      if (row) {
        document.getElementById("planningTitle").value = row.title || "";
        document.getElementById("planningCampus").value = row.campus || "";
        document.getElementById("planningInstructor").value = row.instructor || "";
        document.getElementById("planningStartDate").value = row.start_date || "";
        document.getElementById("planningAudience").value = row.audience || "";
        document.getElementById("planningLevel").value = row.level || "";
        document.getElementById("planningDescription").value = row.description || "";
      }
    }
    dialog.showModal();
  }

  document.getElementById("planningForm").addEventListener("submit", async function (e) {
    e.preventDefault();
    const id = document.getElementById("planningId").value.trim();
    const title = document.getElementById("planningTitle").value.trim();
    const campus = document.getElementById("planningCampus").value.trim();
    const instructor = document.getElementById("planningInstructor").value.trim();
    const startDate = document.getElementById("planningStartDate").value;
    const audience = document.getElementById("planningAudience").value.trim();
    const level = document.getElementById("planningLevel").value.trim();
    const description = document.getElementById("planningDescription").value.trim();
    if (!title) return;
    if (!campus) {
      alert("請選擇校區");
      return;
    }
    const now = new Date().toISOString();
    
    // 先呼叫後端 API 生成 embedding
    let embedding = null;
    let embedding_dim = null;
    try {
      const embRes = await fetch(config.API_BASE_URL + "/api/generate-embedding", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title,
          description: description,
          audience: audience,
        }),
      });
      if (embRes.ok) {
        const embData = await embRes.json();
        embedding = embData.embedding;
        embedding_dim = embData.embedding_dim;
      } else {
        console.warn("生成 embedding 失敗，但繼續儲存課程資料");
      }
    } catch (err) {
      console.warn("無法連線至 embedding API，但繼續儲存課程資料", err);
    }
    
    if (id) {
      const updateData = {
        title: title,
        campus: campus || null,
        instructor: instructor || null,
        start_date: startDate || null,
        audience: audience || null,
        level: level || null,
        description: description || null,
        updated_at: now,
      };
      if (embedding) {
        updateData.embedding = embedding;
        updateData.embedding_dim = embedding_dim;
      }
      const { error } = await supabaseClient.from("courses").update(updateData).eq("id", id);
      if (error) alert("更新失敗：" + error.message);
    } else {
      const payload = {
        id: "manual:" + Math.random().toString(36).slice(2),
        source: "manual",
        status: "planning",
        title: title,
        campus: campus || null,
        instructor: instructor || null,
        start_date: startDate || null,
        audience: audience || null,
        level: level || null,
        description: description || null,
        content_hash: "manual-" + now,
        created_at: now,
        updated_at: now,
      };
      if (embedding) {
        payload.embedding = embedding;
        payload.embedding_dim = embedding_dim;
      }
      const { error } = await supabaseClient.from("courses").insert(payload);
      if (error) alert("新增失敗：" + error.message);
    }
    document.getElementById("planningFormDialog").close();
    renderPlanningList();
  });

  async function deletePlanning(id) {
    if (!confirm("確定刪除此筆規劃中課程？")) return;
    const { error } = await supabaseClient.from("courses").delete().eq("id", id);
    if (error) alert("刪除失敗：" + error.message);
    else renderPlanningList();
  }

  // ---------- ③ 相似度查詢 ----------
  document.getElementById("btnSearchSimilarity").addEventListener("click", async function () {
    const query = document.getElementById("similarityQuery").value.trim();
    const level = document.getElementById("similarityLevel").value.trim();
    const daysBack = parseInt(document.getElementById("daysBack").value, 10);
    const daysForward = parseInt(document.getElementById("daysForward").value, 10);
    const minSimilarity = parseFloat(document.getElementById("minSimilarity").value) / 100; // 轉換為 0-1 範圍
    const topK = parseInt(document.getElementById("topK").value, 10) || 10;
    const el = document.getElementById("similarityResults");
    el.innerHTML = "查詢中…";
    try {
      const r = await fetch(config.API_BASE_URL + "/api/similarity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query,
          level: level || null,
          n_days_back: daysBack,
          n_days_forward: daysForward,
          top_k: topK,
          min_similarity: minSimilarity,
        }),
      });
      const data = await r.json();
      if (!r.ok) {
        el.innerHTML = "<p>查詢失敗：" + (data.detail || r.statusText) + "</p>";
        return;
      }
      const results = data.results || [];
      if (results.length === 0) {
        el.innerHTML = "<p>無相似課程。</p>";
        return;
      }
      el.innerHTML = results.map(function (row) {
        const statusLabel = row.status === "planning" ? " <span style='color: #ff9800; font-weight: bold;'>[規劃中]</span>" : "";
        const campusLabel = row.campus ? " <span style='color: #666;'>[" + escapeHtml(row.campus) + "]</span>" : "";
        const dateLabel = row.start_date ? " <span style='color: #666;'>" + escapeHtml(row.start_date) + "</span>" : "";
        const levelLabel = row.level ? " <span style='color: #666;'>" + escapeHtml(row.level) + "</span>" : "";
        return '<div class="item">' + escapeHtml(row.title || "") + statusLabel + campusLabel + " <span class='similarity'>相似度 " + (row.similarity != null ? (Math.round(row.similarity * 100) + "%") : "-") + "</span>" + dateLabel + levelLabel + "</div>";
      }).join("");
    } catch (err) {
      el.innerHTML = "<p>無法連線至相似度 API（" + config.API_BASE_URL + "），請確認後端 api_server.py 已啟動。</p>";
    }
  });

  document.getElementById("daysBack").addEventListener("input", function () {
    document.getElementById("daysBackVal").textContent = this.value;
  });
  document.getElementById("daysForward").addEventListener("input", function () {
    document.getElementById("daysForwardVal").textContent = this.value;
  });
  document.getElementById("minSimilarity").addEventListener("input", function () {
    document.getElementById("minSimilarityVal").textContent = this.value;
  });

  // ---------- ④ 資料庫瀏覽 ----------
  async function renderBrowseTable() {
    const el = document.getElementById("browseTable");
    el.innerHTML = "載入中…";
    const { data, error } = await supabaseClient.from("courses").select("id,class_code,title,campus,instructor,start_date,audience,level").order("start_date", { ascending: true });
    if (error) {
      el.innerHTML = "<p>無法載入：" + error.message + "</p>";
      return;
    }
    // 欄位順序：班代號、班名、校區、導師、開班日期、對象、難易度
    let html = "<table><thead><tr><th>班代號</th><th>班名</th><th>校區</th><th>導師</th><th>開班日期</th><th>對象</th><th>難易度</th>" + (isAdmin() ? "<th>操作</th>" : "") + "</tr></thead><tbody>";
    (data || []).forEach(function (row) {
      html += "<tr><td>" + escapeHtml(row.class_code || "") + "</td><td>" + escapeHtml(row.title || "") + "</td><td>" + escapeHtml(row.campus || "") + "</td><td>" + escapeHtml(row.instructor || "") + "</td><td>" + escapeHtml(row.start_date || "") + "</td><td>" + escapeHtml(row.audience || "") + "</td><td>" + escapeHtml(row.level || "") + "</td>";
      if (isAdmin()) {
        html += '<td><button type="button" class="btn btn-danger btn-delete-course" data-id="' + escapeHtml(row.id) + '">刪除</button></td>';
      }
      html += "</tr>";
    });
    html += "</tbody></table>";
    el.innerHTML = html;
    el.querySelectorAll(".btn-delete-course").forEach(function (btn) {
      btn.addEventListener("click", async function () {
        if (!confirm("確定刪除此課程？")) return;
        const { error } = await supabaseClient.from("courses").delete().eq("id", btn.getAttribute("data-id"));
        if (error) alert("刪除失敗：" + error.message);
        else renderBrowseTable();
      });
    });
  }

  function escapeHtml(s) {
    if (s == null) return "";
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  // ---------- 登入彈窗 ----------
  document.getElementById("btnLogin").addEventListener("click", function () {
    document.getElementById("loginDialog").showModal();
  });
  document.getElementById("btnCancelLogin").addEventListener("click", function () {
    document.getElementById("loginDialog").close();
  });
  document.getElementById("loginDialog").addEventListener("submit", async function (e) {
    e.preventDefault();
    var email = document.getElementById("loginEmail").value.trim();
    var password = document.getElementById("loginPassword").value;
    var err = (await supabaseClient.auth.signInWithPassword({ email: email, password: password })).error;
    if (err) alert("登入失敗：" + err.message);
    else {
      document.getElementById("loginDialog").close();
      refreshAuth();
    }
  });
  document.getElementById("btnLogout").addEventListener("click", async function () {
    await supabaseClient.auth.signOut();
    refreshAuth();
    showPanel("similarity");
  });

  // ---------- 新增規劃中課程按鈕 ----------
  document.getElementById("btnAddPlanning").addEventListener("click", function () {
    openPlanningForm(null);
  });
  document.getElementById("btnCancelPlanning").addEventListener("click", function () {
    document.getElementById("planningFormDialog").close();
  });

  // ---------- 分頁按鈕 ----------
  document.getElementById("mainTabs").addEventListener("click", function (e) {
    var t = e.target.closest(".tab");
    if (t && t.dataset.tab) showPanel(t.dataset.tab);
  });

  // ---------- 啟動 ----------
  (async function init() {
    await loadConfig();
    if (!supabaseClient) return;
    await refreshAuth();
    showPanel("similarity");
  })();
})();
