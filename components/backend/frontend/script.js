// Simple frontend controller. Adjust API_BASE if your backend runs elsewhere.
const API_BASE = "http://127.0.0.1:8000";

const qs = s => document.querySelector(s);
const qsa = s => document.querySelectorAll(s);

let currentRole = null; // "admin" or "staff"
let currentEmail = null;
let currentDept = null;

function showEl(el){ el.classList.remove("hidden"); }
function hideEl(el){ el.classList.add("hidden"); }
function setText(sel, txt){ const el = qs(sel); if(el) el.textContent = txt; }

window.addEventListener("load", async () => {
  // restore saved session if present
  const savedRole = localStorage.getItem("physio_role");
  const savedEmail = localStorage.getItem("physio_email");
  if (savedRole && savedEmail) {
    currentRole = savedRole;
    currentEmail = savedEmail;
    // attempt to show profile immediately (non-blocking)
    try { await onLoginSuccess(); } catch(e){ /* ignore */ }
  }

  // role buttons
  qs("#btn-admin").addEventListener("click", ()=> enterRole("admin"));
  qs("#btn-staff").addEventListener("click", ()=> enterRole("staff"));

  // tabs
  qs("#tab-login").addEventListener("click", ()=> { tabSwitch("login"); });
  qs("#tab-register").addEventListener("click", ()=> { tabSwitch("register"); });

  // back button from auth
  qs("#back-from-auth").addEventListener("click", ()=> { resetToRoleSelect(); });

  // cancel registration
  qs("#reg-cancel").addEventListener("click", ()=> tabSwitch("login"));
  qs("#reg-staff-cancel").addEventListener("click", ()=> tabSwitch("login"));

  // login submit
  qs("#login-submit").addEventListener("click", async (e) => {
    e.preventDefault();
    const email = qs("#login-email").value.trim();
    const password = qs("#login-password").value;
    if(!email || !password){ setText("#login-msg","Enter email and password"); return; }
    setText("#login-msg","Logging in...");
    try{
      const res = await fetch(API_BASE + "/auth/login", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ type: currentRole, email, password })
      });
      const json = await res.json().catch(()=>({}));
      if(res.ok){
        currentEmail = email;
        // persist session
        localStorage.setItem("physio_role", currentRole);
        localStorage.setItem("physio_email", currentEmail);
        setText("#login-msg","Login successful");
        await onLoginSuccess();
      }
      else setText("#login-msg", json.detail || "Login failed");
    }catch(err){
      console.error(err);
      setText("#login-msg","Backend unreachable");
    }
  });

  // admin register
  qs("#reg-admin-submit").addEventListener("click", async (e)=>{
    e.preventDefault();
    const name = qs("#reg-admin-name").value.trim();
    const email = qs("#reg-admin-email").value.trim();
    const password = qs("#reg-admin-password").value;
    if(!name || !email || !password){ setText("#reg-admin-msg","Fill all fields"); return; }
    setText("#reg-admin-msg","Registering...");
    try{
      const res = await fetch(API_BASE + "/auth/register", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ type: "admin", name, email, password })
      });
      const j = await res.json().catch(()=>({}));
      if(res.ok){ setText("#reg-admin-msg","Registered — please login"); tabSwitch("login"); }
      else setText("#reg-admin-msg", j.detail || "Registration failed");
    }catch(err){ setText("#reg-admin-msg","Backend unreachable"); }
  });

  // staff register
  qs("#reg-staff-submit").addEventListener("click", async (e)=>{
    e.preventDefault();
    const name = qs("#reg-staff-name").value.trim();
    const dept = qs("#reg-staff-dept").value.trim();
    const email = qs("#reg-staff-email").value.trim();
    const password = qs("#reg-staff-password").value;
    if(!name || !dept || !email || !password){ setText("#reg-staff-msg","Fill all fields"); return; }
    setText("#reg-staff-msg","Registering...");
    try{
      const res = await fetch(API_BASE + "/auth/register", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ type: "staff", name, department: dept, email, password })
      });
      const j = await res.json().catch(()=>({}));
      if(res.ok){ setText("#reg-staff-msg","Registered — please login"); tabSwitch("login"); }
      else setText("#reg-staff-msg", j.detail || "Registration failed");
    }catch(err){ setText("#reg-staff-msg","Backend unreachable"); }
  });

  // admin UI actions
  qs("#dept-add").addEventListener("click", async ()=> {
    const name = qs("#dept-new").value.trim(); if(!name) return;
    await postJson("/departments", { name }); loadDepts(); qs("#dept-new").value="";
  });
  qs("#role-add").addEventListener("click", async ()=> {
    const name = qs("#role-new").value.trim(); if(!name) return;
    await postJson("/roles", { name }); loadRoles(); qs("#role-new").value="";
  });
  qs("#staff-refresh").addEventListener("click", loadStaff);
  qs("#items-refresh").addEventListener("click", loadItems);
  qs("#show-depleted").addEventListener("click", loadDepleted);
  qs("#btn-import").addEventListener("click", importCsv);
  qs("#btn-export").addEventListener("click", exportCsv);

  // admin logout
  qs("#admin-logout").addEventListener("click", ()=> {
    currentEmail=null; currentRole=null;
    localStorage.removeItem("physio_role");
    localStorage.removeItem("physio_email");
    hideEl(qs("#admin-dashboard")); showEl(qs("#role-select"));
    // restore header title
    const header = qs("header h1"); if(header) header.textContent = "PhysioTracker";
    document.title = "PhysioTracker";
  });

  // staff actions
  qs("#s-item-add").addEventListener("click", async ()=> {
    const name = qs("#s-item-name").value.trim();
    const type = qs("#s-item-type").value.trim();
    const amount = parseInt(qs("#s-item-amount").value||"0",10);
    if(!name || !type || !amount){ setText("#staff-msg","Provide name,type,amount"); return; }
    const payload = { department: currentDept, type, name, amount_needed: amount };
    const res = await postJson("/items", payload);
    if(res.ok){ setText("#staff-msg","Item added"); qs("#s-item-name").value=""; qs("#s-item-type").value=""; qs("#s-item-amount").value=""; loadStaffItems(); loadItems(); }
    else setText("#staff-msg", res.msg || "Error");
  });
  qs("#s-remove").addEventListener("click", async ()=> {
    const id = parseInt(qs("#s-remove-id").value||"0",10);
    if(!id){ setText("#staff-msg","Enter item ID"); return; }
    const res = await delJson(`/items/${id}`);
    if(res.ok){ setText("#staff-msg","Removed"); loadStaffItems(); loadItems(); } else setText("#staff-msg", res.msg || "Error");
  });
  qs("#s-refill").addEventListener("click", async ()=> {
    const id = parseInt(qs("#s-refill-id").value||"0",10);
    if(!id){ setText("#staff-msg","Enter item ID"); return; }
    const form = new FormData(); form.append("user_email", currentEmail);
    try{
      const r = await fetch(API_BASE + `/items/${id}/refill`, { method:"POST", body: form });
      if(r.ok){ setText("#staff-msg","Refilled"); loadStaffItems(); loadItems(); } else { const j=await r.json().catch(()=>({})); setText("#staff-msg",j.detail||"Error"); }
    }catch(e){ setText("#staff-msg","Backend unreachable"); }
  });
  qs("#staff-logout").addEventListener("click", ()=> {
    currentEmail=null; currentDept=null; currentRole=null;
    localStorage.removeItem("physio_role");
    localStorage.removeItem("physio_email");
    hideEl(qs("#staff-dashboard")); showEl(qs("#role-select"));
    const header = qs("header h1"); if(header) header.textContent = "PhysioTracker";
    document.title = "PhysioTracker";
  });

  // reservation UI listeners
  qs("#staff-reserve-open").addEventListener("click", async () => {
    // populate select then show form
    await populateReserveSelect();
    hideEl(qs("#staff-dashboard"));
    showEl(qs("#staff-reserve-form"));
    setText("#staff-reserve-msg", "");
  });
  qs("#staff-reserve-cancel").addEventListener("click", () => {
    hideEl(qs("#staff-reserve-form"));
    showEl(qs("#staff-dashboard"));
    setText("#staff-reserve-msg", "");
  });
  qs("#staff-reserve-submit").addEventListener("click", async (e) => {
    e.preventDefault();
    const sel = qs("#staff-reserve-select");
    const itemId = parseInt(sel.value || "0", 10);
    const daily = parseInt(qs("#staff-reserve-daily").value || "0", 10);
    const targetRaw = qs("#staff-reserve-target").value.trim();
    const target = targetRaw === "" ? null : parseInt(targetRaw, 10);
    if (!itemId) { setText("#staff-reserve-msg","Select an item"); return; }
    // build URL with query params accepted by API
    const url = API_BASE + `/reservations?item_id=${encodeURIComponent(itemId)}&user_email=${encodeURIComponent(currentEmail)}`
                + (daily>0 ? `&daily_usage=${encodeURIComponent(daily)}` : "")
                + (target !== null ? `&target_amount=${encodeURIComponent(target)}` : "");
    try {
      const r = await fetch(url, { method: "POST" });
      const j = await r.json().catch(()=>({}));
      if (r.ok) {
        setText("#staff-reserve-msg","Reservation created");
        // optionally show reservation summary
        setText("#staff-reserve-status", `Reserved item id ${itemId}`);
        // refresh items/reservations lists
        await loadStaffItems();
        await loadItems();
        // close form after short delay
        setTimeout(()=>{ hideEl(qs("#staff-reserve-form")); showEl(qs("#staff-dashboard")); setText("#staff-reserve-msg",""); }, 900);
      } else {
        setText("#staff-reserve-msg", j.detail || "Reservation failed");
      }
    } catch (e) {
      setText("#staff-reserve-msg","Backend unreachable");
    }
  });

});

// populate reservation select with items in staff's department
async function populateReserveSelect(){
  const sel = qs("#staff-reserve-select");
  sel.innerHTML = "";
  if(!currentDept){
    setText("#staff-reserve-msg","No department found");
    return;
  }
  try{
    const r = await fetch(API_BASE + `/items?department=${encodeURIComponent(currentDept)}`);
    if(!r.ok){ setText("#staff-reserve-msg","Failed to load items"); return; }
    const items = await r.json();
    if(!items.length){
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "(no items in your department)";
      sel.appendChild(opt);
      return;
    }
    items.forEach(it => {
      const opt = document.createElement("option");
      opt.value = it.id;
      opt.textContent = `ID:${it.id} — ${it.name} (${it.current_amount}/${it.amount_needed})`;
      sel.appendChild(opt);
    });
  }catch(e){
    setText("#staff-reserve-msg","Backend unreachable");
  }
}

// --- helpers and UI flows ---
function enterRole(role){
  currentRole = role;
  hideEl(qs("#role-select"));
  showEl(qs("#auth-screen"));
  tabSwitch("login");
  if(role === "admin"){
    hideEl(qs("#form-register-staff")); showEl(qs("#form-register-admin"));
  } else {
    hideEl(qs("#form-register-admin")); showEl(qs("#form-register-staff"));
  }
  setText("#login-title", `${role.charAt(0).toUpperCase()+role.slice(1)} Login`);
}

function tabSwitch(which){
  if(which === "login"){
    qs("#tab-login").classList.add("active"); qs("#tab-register").classList.remove("active");
    showEl(qs("#form-login"));
    hideEl(qs("#form-register-admin")); hideEl(qs("#form-register-staff"));
  } else {
    qs("#tab-register").classList.add("active"); qs("#tab-login").classList.remove("active");
    hideEl(qs("#form-login"));
    if(currentRole === "admin"){ showEl(qs("#form-register-admin")); hideEl(qs("#form-register-staff")); }
    else { showEl(qs("#form-register-staff")); hideEl(qs("#form-register-admin")); }
  }
  setText("#login-msg",""); setText("#reg-admin-msg",""); setText("#reg-staff-msg","");
}

function resetToRoleSelect(){
  currentRole = null;
  hideEl(qs("#auth-screen"));
  showEl(qs("#role-select"));
  tabSwitch("login");
}

// on successful login, show appropriate dashboard and fetch initial data
async function onLoginSuccess(){
  hideEl(qs("#auth-screen"));
  if(currentRole === "admin"){
    // fetch profile to get admin name
    try{
      const r = await fetch(API_BASE + `/auth/profile?type=admin&email=${encodeURIComponent(currentEmail)}`);
      if(r.ok){
        const profile = await r.json();
        setText("#admin-email", currentEmail);
        const header = qs("header h1");
        if(header) header.textContent = profile.name;
        document.title = `${profile.name} — Admin`;
      } else {
        setText("#admin-email", currentEmail);
      }
    }catch(e){
      setText("#admin-email", currentEmail);
    }

    showEl(qs("#admin-dashboard"));
    await Promise.all([ loadDepts(), loadRoles(), loadStaff(), loadItems() ]);
  } else {
    // staff: fetch profile to get staff name and department
    try{
      const r = await fetch(API_BASE + `/auth/profile?type=staff&email=${encodeURIComponent(currentEmail)}`);
      if(r.ok){
        const profile = await r.json();
        currentDept = profile.department;
        setText("#staff-email", profile.name);
        const header = qs("header h1");
        if(header) header.textContent = profile.name;
        document.title = `${profile.name} — Staff`;
        setText("#staff-dept", currentDept || "—");
      } else {
        setText("#staff-email", currentEmail);
      }
    }catch(e){
      setText("#staff-email", currentEmail);
    }

    showEl(qs("#staff-dashboard"));
    await loadStaffItems();
  }
}

// loaders
async function loadDepts(){
  const r = await fetch(API_BASE + "/departments");
  const list = qs("#dept-list"); list.innerHTML = "";
  if(r.ok){ const data = await r.json(); data.forEach(d=>{ const li = document.createElement("li"); li.textContent = d; list.appendChild(li); }); }
}
async function loadRoles(){
  const r = await fetch(API_BASE + "/roles");
  const list = qs("#role-list"); list.innerHTML = "";
  if(r.ok){ const data = await r.json(); data.forEach(rn=>{ const li = document.createElement("li"); li.textContent = rn; list.appendChild(li); }); }
}
async function loadStaff(){
  const r = await fetch(API_BASE + "/staff");
  const list = qs("#staff-list"); list.innerHTML = "";
  const sel = qs("#staff-select"); if(sel) sel.innerHTML = "";
  staffMap.clear();
  if(r.ok){ const data = await r.json(); Object.entries(data).forEach(([email,u])=>{ const li = document.createElement("li"); li.textContent = `${u.name} — ${email} (${u.department})`; list.appendChild(li); if(sel){ const opt = document.createElement("option"); opt.value = email; opt.textContent = `${u.name} — ${email}`; sel.appendChild(opt); } staffMap.set(email, u); }); }
}
async function loadItems(){
  const r = await fetch(API_BASE + "/items?admin=true");
  const list = qs("#items-list"); list.innerHTML = "";
  if(r.ok){ const data = await r.json(); data.forEach(it=>{ const li = document.createElement("li"); li.textContent = `ID:${it.id} | ${it.department} | ${it.name} — ${it.current_amount}/${it.amount_needed}`; list.appendChild(li); }); }
}
async function loadDepleted(){
  const r = await fetch(API_BASE + "/items/depleted");
  const list = qs("#depleted-list"); list.innerHTML = "";
  if(r.ok){ const data = await r.json(); data.forEach(it=>{ const li = document.createElement("li"); li.textContent = `ID:${it.id} | ${it.department} | ${it.name}`; list.appendChild(li); }); }
}
async function loadStaffItems(){
  const list = qs("#s-items-list"); list.innerHTML = "";
  if(!currentDept){ setText("#staff-msg","No department found"); return; }
  const r = await fetch(API_BASE + `/items?department=${encodeURIComponent(currentDept)}`);
  if(r.ok){ const data = await r.json(); data.forEach(it=>{ const li = document.createElement("li"); li.textContent = `ID:${it.id} | ${it.name} — ${it.current_amount}/${it.amount_needed}`; const useBtn = document.createElement("button"); useBtn.textContent="Use 1"; useBtn.className="btn"; useBtn.style.marginLeft="8px"; useBtn.onclick = ()=> useItem(it.id,1); li.appendChild(useBtn); list.appendChild(li); }); }
}

// POST helper
async function postJson(path, payload){
  try{
    const r = await fetch(API_BASE + path, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload) });
    const j = await r.json().catch(()=>({}));
    return { ok: r.ok, status: r.status, data: j, msg: j.detail || j.message };
  }catch(e){ return { ok:false, msg: e.message }; }
}
async function delJson(path){
  try{
    const r = await fetch(API_BASE + path, { method:"DELETE" });
    const j = await r.json().catch(()=>({}));
    return { ok: r.ok, status: r.status, data: j, msg: j.detail || j.message };
  }catch(e){ return { ok:false, msg: e.message }; }
}

// staff use item
async function useItem(itemId, amount){
  const form = new FormData();
  form.append("user_email", currentEmail);
  form.append("amount", amount);
  try{
    const r = await fetch(API_BASE + `/items/${itemId}/use`, { method:"POST", body: form });
    if(r.ok){ setText("#staff-msg","Used item"); loadStaffItems(); loadItems(); } else { const j=await r.json().catch(()=>({})); setText("#staff-msg", j.detail || "Error"); }
  }catch(e){ setText("#staff-msg","Backend unreachable"); }
}

// import/export
async function importCsv(){
  const fileInput = qs("#import-file"); const kind = qs("#import-kind").value;
  if(!fileInput.files.length){ setText("#admin-msg","Select CSV file"); return; }
  const f = fileInput.files[0];
  const fd = new FormData(); fd.append("kind", kind); fd.append("file", f);
  try{
    const r = await fetch(API_BASE + "/items/import", { method:"POST", body: fd }); // items router handles import endpoint
    const j = await r.json().catch(()=>({}));
    if(r.ok){ setText("#admin-msg","Import successful"); loadDepts(); loadRoles(); loadStaff(); loadItems(); fileInput.value=""; }
    else setText("#admin-msg", j.detail || "Import failed");
  }catch(e){ setText("#admin-msg","Backend unreachable"); }
}
async function exportCsv(){
  const kind = qs("#export-kind").value;
  const url = API_BASE + `/items/export?kind=${encodeURIComponent(kind)}`;
  try{
    window.open(url, "_blank");
    setText("#admin-msg", `Export started for: ${kind}`);
  }catch(e){
    setText("#admin-msg","Export failed: cannot open download");
  }
}