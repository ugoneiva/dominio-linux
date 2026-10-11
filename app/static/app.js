/* Copyright (C) 2026 JLW Security. SPDX-License-Identifier: GPL-3.0-or-later */
const $ = selector => document.querySelector(selector);
const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
const shapes = {
  grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  users:'<circle cx="9" cy="7" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M16 4a3 3 0 0 1 0 6M21 20v-2a6 6 0 0 0-4-5"/>',
  group:'<circle cx="12" cy="7" r="3"/><path d="M6 21v-2a6 6 0 0 1 12 0v2M4 7a3 3 0 0 0 0 6M20 7a3 3 0 0 1 0 6M2 21v-2a5 5 0 0 1 2-4M22 21v-2a5 5 0 0 0-2-4"/>',
  tree:'<rect x="9" y="2" width="6" height="5" rx="1"/><rect x="2" y="17" width="6" height="5" rx="1"/><rect x="16" y="17" width="6" height="5" rx="1"/><path d="M12 7v5M5 17v-5h14v5"/>',
  monitor:'<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 22h8M12 17v5"/>',
  shield:'<path d="m12 2 8 3v6c0 5-4 8-8 11-4-3-8-6-8-11V5l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c5 5 5 13 0 18-5-5-5-13 0-18Z"/>',
  folder:'<path d="M3 7V5a2 2 0 0 1 2-2h5l3 3h6a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/>',
  server:'<rect x="3" y="3" width="18" height="7" rx="2"/><rect x="3" y="14" width="18" height="7" rx="2"/><path d="M7 6.5h.1M7 17.5h.1M12 6.5h5M12 17.5h5"/>',
  link:'<path d="m9 15 6-6M7 13l-2 2a4 4 0 0 0 6 6l3-3M17 11l2-2a4 4 0 0 0-6-6l-3 3"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  layers:'<path d="m12 3 10 5-10 5L2 8l10-5ZM2 12l10 5 10-5M2 16l10 5 10-5"/>',
  logout:'<path d="M9 3H4v18h5M10 12h12m-4-4 4 4-4 4"/>',
  search:'<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
  edit:'<path d="m16 3 5 5-12 12-6 1 1-6L16 3ZM13 6l5 5"/>',
  trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
  plus:'<path d="M12 4v16M4 12h16"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M3 16v5h18v-5"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${shapes[name] || shapes.grid}</svg>`;
document.querySelectorAll('[data-icon]').forEach(element => { element.innerHTML = icon(element.dataset.icon); });
const modules = {
  users: {title:'Usuários', singular:'usuário', description:'Identidades, contas e acesso das pessoas ao domínio.', icon:'users', columns:['PESSOA / LOGIN','UNIDADE ORGANIZACIONAL','E-MAIL','ESTADO']},
  groups: {title:'Grupos', singular:'grupo', description:'Organize equipes e prepare o acesso aos recursos do domínio.', icon:'group', columns:['GRUPO','UNIDADE ORGANIZACIONAL','MEMBROS','DESCRIÇÃO']},
  ous: {title:'Unidades organizacionais', singular:'unidade organizacional', description:'Estruture o domínio por equipes, locais e tipos de equipamento.', icon:'tree', columns:['UNIDADE','UNIDADE SUPERIOR','DESCRIÇÃO']},
  computers: {title:'Computadores', singular:'computador', description:'Servidores e workstations Windows e Linux, sob um domínio Linux.', icon:'monitor', columns:['COMPUTADOR','SISTEMA OPERACIONAL','FUNÇÃO','UNIDADE','ESTADO']},
  policies: {title:'Políticas', singular:'política', description:'Prepare políticas para os sistemas que fazem parte do domínio.', icon:'shield', columns:['POLÍTICA','PLATAFORMA','UNIDADE','ESTADO']},
  dns: {title:'DNS', singular:'registro DNS', description:'Organize os nomes e destinos dos serviços na rede local.', icon:'globe', columns:['NOME','TIPO','DESTINO / CONTEÚDO','TTL']},
  shares: {title:'Compartilhamentos', singular:'compartilhamento', description:'Prepare pastas de rede e o acesso das equipes aos arquivos.', icon:'folder', columns:['COMPARTILHAMENTO','SERVIDOR','CAMINHO','GRUPOS','ESTADO']},
};
const titles = {overview:'Visão geral', setup:'Criar domínio Linux', integration:'Integração Samba', audit:'Histórico de alterações', roadmap:'Etapas do projeto', ...Object.fromEntries(Object.entries(modules).map(([key,value]) => [key,value.title]))};
let context;
let distributions = [];
const distributionLabel = identifier => distributions.find(profile => profile.id === identifier)?.label || identifier;
let currentPage;
let items = [];
let editorKind;
let editing;
let lookups = {ous:[],users:[],groups:[]};
let navigation = 0;
let toastTimer;

function toast(message, error = false) {
  $('#toast').textContent = message;
  $('#toast').classList.toggle('error', error);
  $('#toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, error ? 9000 : 4500);
}

async function api(path, options = {}) {
  const headers = {...options.headers};
  if (options.body && !(options.body instanceof Blob)) headers['Content-Type'] = 'application/json';
  if (context?.csrf) headers['X-CSRF-Token'] = context.csrf;
  const response = await fetch(path, {...options, headers});
  if (response.status === 401) { location.replace('/'); throw new Error('Sua sessão expirou.'); }
  if (!response.ok) {
    const data = await response.json().catch(() => ({detail:'Não foi possível concluir a operação.'}));
    const message = Array.isArray(data.detail) ? data.detail.map(entry => `${entry.field}: ${entry.message}`).join(' · ') : data.detail;
    throw new Error(message || 'Não foi possível concluir a operação.');
  }
  return response.headers.get('content-type')?.includes('application/json') ? response.json() : response.blob();
}

function badge(value, kind = 'neutral') { return `<span class="pill ${kind}">${escape(value)}</span>`; }
function stateBadge(item) { return badge(item.enabled === false ? 'Desativado' : 'Ativo', item.enabled === false ? 'neutral' : 'good'); }
function date(value, options = {}) { return new Date(value).toLocaleString('pt-BR', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',...options}); }
function heading(title, description, actions = '') { return `<div class="page-heading"><div><span class="eyebrow">ADMINISTRAÇÃO EM LINUX</span><h1>${escape(title)}</h1><p>${escape(description)}</p></div><div class="page-heading-actions">${actions}</div></div>`; }
function notice(text, warning = false) { return `<div class="notice ${warning ? 'warning' : ''}">${icon('info')}<div>${text}</div></div>`; }
function modeNotice() {
  return context.mode === 'ldaps'
    ? notice(`<strong>Domínio Samba conectado · somente leitura.</strong> Objetos consultados em ${escape(context.connection.host)}. Alterações reais serão habilitadas em uma próxima etapa.`)
    : notice('<strong>Laboratório local.</strong> Os dados são exemplos fictícios. Seus cadastros são salvos neste projeto e não alteram um domínio real.');
}
function empty(title, description, action = '') { return `<div class="empty-state">${icon('layers')}<h3>${escape(title)}</h3><p>${escape(description)}</p>${action}</div>`; }

async function refreshContext() {
  context = await api('/api/session');
  if (!distributions.length) distributions = (await api('/api/distributions')).items;
  const domain = context.mode === 'ldaps' ? {fqdn: context.connection.base_dn.split(',').map(part => part.slice(3)).join('.')} : await api('/api/domain');
  $('#domain-name').textContent = domain.fqdn;
  $('#domain-mode').textContent = context.mode === 'ldaps' ? 'Samba conectado · leitura' : 'Laboratório local';
  $('#mode-badge').textContent = context.mode === 'ldaps' ? 'LDAPS · leitura' : 'Laboratório';
}

async function navigate() {
  const tick = ++navigation;
  const candidate = location.hash.slice(1) || 'overview';
  currentPage = titles[candidate] ? candidate : 'overview';
  const page = currentPage;
  document.querySelectorAll('[data-page]').forEach(element => element.classList.toggle('active', element.dataset.page === currentPage));
  $('#breadcrumb').textContent = titles[currentPage];
  document.title = `${titles[currentPage]} · Domínio Linux`;
  $('#sidebar').classList.remove('open');
  $('#content').innerHTML = '<div class="loading">Carregando…</div>';
  try {
    await refreshContext();
    const renderers = {overview: renderOverview, setup: renderSetup, integration: renderIntegration, audit: renderAudit, roadmap: renderRoadmap};
    const result = modules[page] ? await renderModule(page) : await renderers[page]();
    if (tick !== navigation) return;
    if (typeof result === 'object') {
      items = result.items;
      $('#content').innerHTML = result.markup;
    } else {
      items = [];
      $('#content').innerHTML = result;
    }
    bindPage();
  } catch (failure) {
    if (tick !== navigation) return;
    $('#content').innerHTML = heading(titles[currentPage], 'A operação precisa de atenção.') + notice(escape(failure.message), true);
  }
}

async function renderOverview() {
  const data = await api('/api/overview');
  const stats = [['users','Usuários','users'],['groups','Grupos','group'],['computers','Computadores','monitor'],['policies','Políticas','shield']].map(([key,label,glyph]) => `<a class="stat-card" href="#${key}"><div class="stat-top"><span>${label}</span><span class="stat-icon">${icon(glyph)}</span></div><div class="stat-value">${data.counts[key] ?? 0}</div><div class="stat-foot">${context.mode === 'ldaps' ? 'Consultados no domínio Samba' : 'Objetos do laboratório'}</div></a>`).join('');
  const activities = data.audit.map(row => `<div class="activity-row"><span class="activity-icon">${icon('clock')}</span><div class="activity-content"><strong>${escape(row.operation)} · ${escape(row.actor)}</strong><small>${escape(row.target.split('/')[0])} · ${escape(row.mode)}</small></div><time>${escape(date(row.created_at))}</time></div>`).join('');
  return heading('Tudo começa no seu domínio.', 'Pessoas, máquinas e políticas. Um ponto de administração para sua infraestrutura.', `<a href="#setup" class="button primary">${icon('plus')} Criar domínio Linux</a>`) + modeNotice() + `<div class="stats">${stats}</div>
  <section class="hero"><div><span class="eyebrow">LINUX NA BASE. TODA A REDE CONECTADA.</span><h2>Crie o domínio. Simplifique a rotina.</h2><p>Prepare seu controlador Samba em Linux, organize as identidades e conecte servidores e estações de diferentes sistemas.</p><a href="#setup" class="button">Configurar primeiro controlador ${icon('arrow')}</a></div><div class="hero-visual"><div class="hero-server">${icon('server')} Controlador Linux</div><div class="hero-line"></div><div class="hero-clients"><span>Windows</span><span>Linux</span></div></div></section>
  <div class="dashboard-grid"><section class="panel"><div class="panel-header"><h2>Serviços do domínio</h2>${badge('Aguardando diagnóstico')}</div><div class="panel-body">${data.services.map(service => `<div class="service-row"><span class="service-name">${icon('server')}${escape(service.name)}</span>${badge(service.status)}</div>`).join('')}<div class="panel-caption">Estado operacional ainda não consultado. A presença de objetos no diretório não comprova a saúde dos serviços.</div></div></section><section class="panel"><div class="panel-header"><h2>Atividade recente no painel</h2><a href="#audit">Ver histórico →</a></div><div class="panel-body">${activities || '<p class="section-note">Nenhuma alteração registrada.</p>'}</div></section></div>
  <section class="panel"><div class="panel-header"><h2>${context.mode === 'ldaps' ? 'Domínio conectado' : 'Plano do laboratório'}</h2>${badge(context.mode === 'ldaps' ? 'Samba · leitura' : 'Não provisionado','neutral')}</div><div class="panel-body domain-info">${[['Domínio DNS',data.domain.fqdn],['Controlador',data.domain.hostname],['Base da plataforma',distributionLabel(data.domain.distribution)],['Máquinas membros','Windows e Linux']].map(([label,value]) => `<div><span class="info-label">${escape(label)}</span><span class="info-value">${escape(value)}</span></div>`).join('')}</div></section>`;
}

async function renderModule(kind) {
  const module = modules[kind];
  const data = await api(`/api/records/${kind}`);
  const records = data.items;
  let markup = heading(module.title, module.description, context.mode === 'laboratorio' ? `<button class="button primary" data-action="new">${icon('plus')} Adicionar ${escape(module.singular)}</button>` : badge('Consulta real · leitura','good')) + modeNotice();
  if (kind === 'policies') markup += `<div class="catalogue">${badge('Windows · Registro','blue')}${badge('Linux · sudo','good')}${badge('Linux · OpenSSH','good')}</div>` + notice(context.mode === 'laboratorio' ? '<strong>Rascunhos de políticas.</strong> O editor salva configurações e permite exportá-las em JSON. Publicação no SYSVOL e verificação da aplicação ainda estão em desenvolvimento.' : '<strong>Metadados de GPO.</strong> A consulta apresenta os objetos do diretório. O conteúdo do SYSVOL e os vínculos efetivos ainda não são consultados.');
  if (kind === 'shares') markup += notice('<strong>Planejamento de compartilhamentos.</strong> Salve caminhos e grupos de acesso. Esta versão não cria pastas, compartilhamentos ou ACLs em servidores reais.');
  if (kind === 'computers') markup += notice(context.mode === 'laboratorio' ? 'Cadastrar um equipamento no laboratório não o ingressa no domínio. Ingresso assistido e renomeação remota fazem parte da próxima etapa.' : 'As contas consultadas não permitem confirmar o sistema instalado, a função de servidor/estação ou a disponibilidade atual da máquina.');
  return {items:records, markup: markup + `<section class="panel"><div class="table-toolbar"><div class="search-field">${icon('search')}<input id="filter" type="search" placeholder="Pesquisar ${escape(module.title.toLowerCase())}…" aria-label="Pesquisar objetos"></div><span class="table-count" id="table-count">${records.length} objetos</span></div><div class="table-scroll"><table><thead><tr>${module.columns.map(column => `<th>${column}</th>`).join('')}<th></th></tr></thead><tbody id="record-rows">${rows(kind, records)}</tbody></table></div><div class="table-foot"><span id="visible-count">${records.length} objetos apresentados</span><span>${context.mode === 'ldaps' ? 'Fonte: Samba LDAPS' : 'Fonte: laboratório local'}</span></div></section>`};
}

function rows(kind, records) {
  if (!records.length) return `<tr><td colspan="${modules[kind].columns.length + 1}">${empty('Nenhum objeto encontrado', 'Adicione um objeto ou ajuste a pesquisa.')}</td></tr>`;
  return records.map(item => {
    const person = `<div class="table-person"><span class="avatar">${escape(item.name.slice(0,2).toUpperCase())}</span><div><strong>${escape(item.name)}</strong>${item.account ? `<small>${escape(item.account)}</small>` : ''}</div></div>`;
    const ou = item.ou ? escape(item.ou) : '<span class="muted">Raiz do domínio</span>';
    const cells = {
      users:[person,ou,escape(item.email || '—'),stateBadge(item)],
      groups:[person,ou,badge(`${item.members?.length || 0} membros`),escape(item.description || '—')],
      ous:[person,ou,escape(item.description || '—')],
      computers:[person,badge(item.os || 'Não informado', item.os?.includes('Windows') ? 'blue' : 'neutral'),escape(item.role === 'server' ? 'Servidor' : item.role === 'workstation' ? 'Workstation' : item.role || 'Não informado'),ou,stateBadge(item)],
      policies:[person,badge(item.platform || 'Não informado', item.platform === 'Linux' ? 'good' : 'blue'),context.mode === 'ldaps' ? '<span class="muted">Vínculos não consultados</span>' : ou,badge(context.mode === 'ldaps' ? 'Metadados' : 'Rascunho','warning')],
      dns:[`<strong>${escape(item.name)}</strong>`,badge(item.record_type),`<span class="row-meta">${escape(item.value)}</span>`,`${escape(item.ttl)} s`],
      shares:[person,escape(item.os || 'A definir'),`<code>${escape(item.value || 'A definir')}</code>`,badge(`${item.members?.length || 0} grupos`),badge('Rascunho','warning')],
    }[kind];
    const actions = context.mode === 'laboratorio' ? `<button class="icon-button" data-action="edit" data-id="${escape(item.id)}" aria-label="Editar ${escape(item.name)}" title="Editar">${icon('edit')}</button><button class="icon-button" data-action="delete" data-id="${escape(item.id)}" aria-label="Excluir ${escape(item.name)}" title="Excluir">${icon('trash')}</button>` : '';
    const exportButton = kind === 'policies' ? `<button class="icon-button" data-action="export" data-id="${escape(item.id)}" aria-label="Exportar JSON de ${escape(item.name)}" title="Exportar JSON">${icon('download')}</button>` : '';
    return `<tr>${cells.map(cell => `<td>${cell}</td>`).join('')}<td><div class="row-actions">${exportButton}${actions}</div></td></tr>`;
  }).join('');
}

function inputField(name, label, value = '', options = {}) {
  const attrs = `${options.required ? 'required' : ''} ${options.type === 'number' ? `min="${options.min ?? 0}" max="${options.max ?? 65535}"` : `maxlength="${options.maxLength || 200}"`}`;
  return `<div class="field ${options.full ? 'full-width' : ''}"><label for="f-${name}">${escape(label)}</label><input id="f-${name}" name="${name}" type="${options.type || 'text'}" value="${escape(value)}" ${attrs} ${options.suggestions ? `list="choices-${name}"` : ''} ${options.placeholder ? `placeholder="${escape(options.placeholder)}"` : ''}>${options.suggestions ? `<datalist id="choices-${name}">${options.suggestions.map(value => `<option value="${escape(value)}"></option>`).join('')}</datalist>` : ''}${options.hint ? `<small>${escape(options.hint)}</small>` : ''}</div>`;
}
function selectField(name, label, values, selected = '', multiple = false) {
  const selectedValues = Array.isArray(selected) ? selected : [selected];
  return `<div class="field"><label for="f-${name}">${escape(label)}</label><select id="f-${name}" name="${name}" ${multiple ? 'multiple' : ''} ${name === 'distribution' ? 'aria-describedby="distribution-info"' : ''}>${values.map(option => { const [value,text] = Array.isArray(option) ? option : [option,option]; return `<option value="${escape(value)}" ${selectedValues.includes(value) ? 'selected' : ''}>${escape(text)}</option>`; }).join('')}</select>${multiple ? '<small>Use Ctrl ou Command para selecionar vários itens.</small>' : ''}</div>`;
}
function textareaField(name, label, value = '') { return `<div class="field full-width"><label for="f-${name}">${escape(label)}</label><textarea id="f-${name}" name="${name}" maxlength="${name === 'ca_pem' ? 20000 : 1000}">${escape(value)}</textarea></div>`; }

async function openEditor(kind, item = null) {
  editorKind = kind;
  editing = item;
  const results = await Promise.all(['ous','users','groups'].map(async category => [category,(await api(`/api/records/${category}`)).items]));
  lookups = Object.fromEntries(results);
  const value = item || {};
  const ouChoices = [['','Raiz do domínio'],...lookups.ous.filter(ou => ou.id !== value.id).map(ou => [ou.name,ou.name])];
  let fields = inputField('name', kind === 'users' ? 'Nome completo' : 'Nome', value.name, {required:true,maxLength:100});
  if (kind === 'users' || kind === 'groups') fields += inputField('account','Nome de login', value.account, {required:kind === 'users',maxLength:64,placeholder:'nome.sobrenome'});
  if (kind === 'users') fields += inputField('email','E-mail',value.email,{type:'email'});
  if (!['dns','shares'].includes(kind)) fields += selectField('ou',kind === 'ous' ? 'Unidade superior' : 'Unidade organizacional',ouChoices,value.ou || '');
  if (kind === 'computers') fields += inputField('os','Sistema operacional',value.os || 'Debian 13',{maxLength:100,suggestions:[...distributions.map(profile => profile.label),'Windows 11','Windows Server 2025'],hint:'Selecione uma sugestão ou informe outra versão.'}) + selectField('role','Função',[['workstation','Workstation'],['server','Servidor']],value.role || 'workstation');
  if (kind === 'groups') fields += selectField('members','Usuários membros',lookups.users.map(user => [user.id,`${user.name} (${user.account})`]),value.members || [],true);
  if (kind === 'dns') fields += selectField('record_type','Tipo de registro',['A','AAAA','CNAME','TXT','MX','PTR'],value.record_type || 'A') + inputField('value','Destino ou conteúdo',value.value,{required:true,maxLength:1000}) + inputField('ttl','TTL em segundos',value.ttl || 3600,{type:'number',min:60,max:86400}) + inputField('priority','Prioridade (MX)',value.priority ?? 10,{type:'number'});
  if (kind === 'shares') fields += inputField('os','Servidor de arquivos Linux',value.os || '',{placeholder:'srv-arq-01',maxLength:100}) + inputField('value','Caminho da pasta',value.value || '',{placeholder:'/srv/compartilhamentos/equipe',maxLength:1000}) + selectField('members','Grupos com acesso',lookups.groups.map(group => [group.id,group.name]),value.members || [],true) + selectField('access','Permissão planejada',['read','modify','full'].map((key,index) => [key,['Leitura','Modificar','Controle total'][index]]),value.settings?.access || 'modify');
  if (kind === 'policies') fields += selectField('policy_type','Tipo de política',[['registry','Windows · Registro'],['linux-ssh','Linux · OpenSSH'],['linux-sudo','Linux · sudo']],value.policy_type || 'registry') + '<div class="full-width" id="policy-fields"></div>';
  if (kind !== 'dns') fields += textareaField('description','Descrição',value.description || '');
  if (['users','computers','policies'].includes(kind)) fields += `<div class="checkbox-field full-width"><input id="f-enabled" name="enabled" type="checkbox" ${value.enabled !== false ? 'checked' : ''}><label for="f-enabled">${kind === 'policies' ? 'Política habilitada no rascunho' : 'Objeto ativo no laboratório'}</label></div>`;
  $('#editor-title').textContent = `${item ? 'Editar' : 'Adicionar'} ${modules[kind].singular}`;
  $('#editor-fields').innerHTML = `<div class="two-cols">${fields}</div>`;
  if (kind === 'policies') {
    policyFields(value.policy_type || 'registry', value.settings || {});
    $('#f-policy_type').addEventListener('change', event => policyFields(event.target.value, {}));
  }
  $('#editor-dialog').showModal();
}

function policyFields(type, settings) {
  let fields;
  if (type === 'registry') fields = inputField('keyname','Chave do Registro',settings.keyname || 'Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System',{required:true,maxLength:1000}) + inputField('valuename','Nome do valor',settings.valuename || 'InactivityTimeoutSecs',{required:true}) + selectField('registry_class','Aplicação',[['MACHINE','Computador'],['USER','Usuário']],settings.class || 'MACHINE') + selectField('registry_type','Tipo do valor',['REG_DWORD','REG_SZ'],settings.type || 'REG_DWORD') + inputField('registry_data','Valor',settings.data ?? settings.timeout_seconds ?? '600',{required:true,hint:'Para REG_DWORD, informe um inteiro entre 0 e 4294967295.'});
  if (type === 'linux-ssh') fields = selectField('ssh_root','Login direto de root',[['no','Bloqueado'],['prohibit-password','Somente chave'],['yes','Permitido']],settings.PermitRootLogin || 'no') + selectField('ssh_password','Autenticação por senha',[['no','Desativada'],['yes','Ativada']],settings.PasswordAuthentication || 'no') + inputField('ssh_port','Porta SSH',settings.Port || 22,{type:'number',min:1});
  if (type === 'linux-sudo') fields = inputField('sudo_group','Grupo autorizado',settings.group || '',{required:true,placeholder:'equipe-ti'}) + textareaField('sudo_commands','Comandos permitidos',settings.commands || '/usr/bin/systemctl status') + selectField('sudo_nopasswd','Exigir senha',[['false','Sim'],['true','Não']],String(settings.nopasswd || false));
  $('#policy-fields').innerHTML = `<div class="notice warning">${icon('info')}<div>Estas configurações são um rascunho. O painel ainda não publica nem aplica a política nas máquinas.</div></div><div class="two-cols">${fields}</div>`;
}

$('#editor-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = new FormData(event.target);
  const value = Object.fromEntries(form);
  const body = {name:value.name, description:value.description || '', ou:value.ou || ''};
  const fields = ['account','email','os','role','record_type','value','policy_type'];
  for (const field of fields) if (value[field] !== undefined) body[field] = value[field];
  if (['users','computers','policies'].includes(editorKind)) body.enabled = form.has('enabled');
  if (['groups','shares'].includes(editorKind)) body.members = form.getAll('members');
  if (editorKind === 'dns') { body.ttl = Number(value.ttl); body.priority = Number(value.priority); }
  if (editorKind === 'shares') body.settings = {access:value.access};
  if (editorKind === 'policies') {
    body.platform = value.policy_type === 'registry' ? 'Windows' : 'Linux';
    if (value.policy_type === 'registry') {
      const data = value.registry_type === 'REG_DWORD' ? Number(value.registry_data) : value.registry_data;
      if (value.registry_type === 'REG_DWORD' && (!Number.isInteger(data) || data < 0 || data > 4294967295)) { toast('Informe um inteiro válido para REG_DWORD.',true); return; }
      body.settings = {keyname:value.keyname,valuename:value.valuename,class:value.registry_class,type:value.registry_type,data};
    }
    if (value.policy_type === 'linux-ssh') body.settings = {PermitRootLogin:value.ssh_root,PasswordAuthentication:value.ssh_password,Port:Number(value.ssh_port)};
    if (value.policy_type === 'linux-sudo') body.settings = {group:value.sudo_group,commands:value.sudo_commands,nopasswd:value.sudo_nopasswd === 'true'};
  }
  const button = event.target.querySelector('[type=submit]');
  button.disabled = true;
  try {
    await api(`/api/records/${editorKind}${editing ? `/${encodeURIComponent(editing.id)}` : ''}`, {method:editing ? 'PUT' : 'POST',body:JSON.stringify(body)});
    $('#editor-dialog').close();
    toast('Cadastro salvo no laboratório e registrado no histórico.');
    await navigate();
  } catch (failure) { toast(failure.message,true); } finally { button.disabled = false; }
});
document.querySelectorAll('.close-dialog').forEach(button => button.addEventListener('click', () => $('#editor-dialog').close()));

function confirmDelete(item) {
  $('#confirm-description').textContent = `${item.name} será removido do laboratório local.`;
  $('#confirm-dialog').showModal();
  return new Promise(resolve => {
    const dialog = $('#confirm-dialog');
    const confirm = $('#confirm-delete');
    const cancel = $('#confirm-cancel');
    const finish = value => { confirm.onclick = null; cancel.onclick = null; dialog.removeEventListener('cancel', dismiss); dialog.close(); resolve(value); };
    const dismiss = event => { event.preventDefault(); finish(false); };
    confirm.onclick = () => finish(true);
    cancel.onclick = () => finish(false);
    dialog.addEventListener('cancel',dismiss);
  });
}

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
}

async function renderSetup() {
  const value = await api('/api/domain');
  return heading('Criar seu domínio em Linux', 'Configure o primeiro controlador Samba e prepare a rede para seus membros.') + notice('<strong>Criação em uma VM dedicada.</strong> Escolha a distribuição do controlador. O assistente informa a disponibilidade do instalador e gera um plano específico para a VM.') + `<div class="setup-layout"><section class="panel"><form id="setup-form"><div class="form-section"><h2><span class="section-number">1</span>Identidade do domínio</h2><div class="two-cols">${inputField('label','Nome do ambiente',value.label,{required:true,maxLength:80})}${inputField('fqdn','Domínio DNS',value.fqdn,{required:true,hint:'Use um subdomínio sob seu controle. Para laboratório, utilize .test.'})}${inputField('netbios','Nome curto (NetBIOS)',value.netbios,{required:true,maxLength:15})}${inputField('hostname','Nome do controlador Linux',value.hostname,{required:true,maxLength:15})}</div></div><div class="form-section"><h2><span class="section-number">2</span>Rede e serviços</h2><div class="two-cols">${inputField('address','IPv4 estático do controlador',value.address,{required:true})}${inputField('subnet','Sub-rede (CIDR)',value.subnet,{required:true})}${inputField('forwarder','Encaminhador DNS',value.forwarder,{required:true})}${inputField('ntp_server','Fonte de horário',value.ntp_server,{required:true})}${selectField('distribution','Sistema do controlador',distributions.map(profile => [profile.id,profile.label]),value.distribution)}<div id="distribution-info" class="distribution-info full-width" aria-live="polite">${distributionInfo(value.distribution)}</div></div><p class="section-note">A senha Administrator será solicitada diretamente na VM durante a instalação. O endereço estático precisa estar configurado na interface antes de executar o pacote.</p></div><div class="form-actions"><button type="submit" class="button primary">${icon('layers')} Gerar plano</button><button type="button" class="button secondary" id="save-domain" ${context.mode === 'ldaps' ? 'disabled' : ''}>Salvar configuração local</button></div></form></section><aside class="panel"><div class="panel-header"><h2>O que vamos preparar</h2>${badge('Primeiro DC')}</div><div class="panel-body"><ol class="steps"><li><strong>Controlador em Linux</strong><p>Samba AD DC em uma VM dedicada.</p></li><li><strong>Identidade e autenticação</strong><p>Diretório e Kerberos para usuários e máquinas.</p></li><li><strong>DNS e horário</strong><p>Serviços necessários ao funcionamento do domínio.</p></li><li><strong>Membros Windows e Linux</strong><p>Servidores e workstations conectados ao domínio.</p></li></ol><div class="panel-caption">O pacote inicial ainda precisa de execução e validação operacional em VM. Segundo DC, firewall, certificados e ingresso assistido serão entregas seguintes.</div></div></aside></div><div id="plan-result" class="plan-result"></div>`;
}

function setupValue() { return Object.fromEntries(new FormData($('#setup-form'))); }
function distributionInfo(identifier) {
  const profile = distributions.find(item => item.id === identifier);
  if (!profile) return '';
  return `<div class="distribution-heading"><strong>${escape(profile.label)}</strong>${badge(profile.status,profile.installer_available ? 'blue' : 'warning')}</div><p>${escape(profile.note)}</p><span class="muted">${escape(profile.family)} · Controlador Samba em Linux</span>`;
}

function planMarkup(result) {
  return `<section class="panel"><div class="panel-header"><h2>Plano de criação · ${escape(result.manifest.fqdn)}</h2>${badge('Não executado','warning')}</div><div class="panel-body"><p class="section-note">${escape(result.target)}. ${escape(result.execution)}</p><ol class="steps">${result.steps.map(step => `<li><strong>${escape(step.title)}</strong><p>${escape(step.detail)}</p></li>`).join('')}</ol><div class="two-cols"><div><h3>Requisitos da VM</h3><ul class="simple-list">${result.requirements.map(item => `<li>${escape(item)}</li>`).join('')}</ul></div><div><h3>Alterações previstas</h3><ul class="simple-list">${result.changes.map(item => `<li>${escape(item)}</li>`).join('')}</ul></div></div><p class="section-note">${result.installer_available ? 'O pacote contém o instalador inicial, o manifesto e as instruções de execução.' : 'O pacote contém o manifesto e o plano. O instalador desta distribuição está pendente de integração.'} O download não executa alterações na VM.</p><button id="download-package" class="button primary">${icon('download')} ${result.installer_available ? 'Baixar pacote de instalação' : 'Baixar plano desta distribuição'}</button></div></section>`;
}

async function renderIntegration() {
  return heading('Conectar ao seu Samba', 'Consulte um domínio hospedado em Linux por uma conexão LDAPS validada.') + notice('<strong>Integração inicial de leitura.</strong> Usuários, grupos, OUs, computadores e metadados de GPO podem ser consultados. A senha fica somente na memória da sessão e é descartada ao desconectar ou expirar.') + `<div class="integration-layout"><section class="panel integration-card">${context.mode === 'ldaps' ? `<span class="eyebrow">DOMÍNIO CONECTADO</span><h2>${escape(context.connection.host)}</h2><p>${escape(context.connection.base_dn)}</p><div class="status-line"><span>Modo de acesso</span>${badge('Somente leitura','good')}</div><div class="status-line"><span>Transporte</span>${badge('LDAPS · certificado validado','good')}</div><button id="disconnect" class="button secondary">Desconectar e voltar ao laboratório</button>` : `<form id="integration-form"><h2>Dados do controlador Linux</h2><div class="two-cols">${inputField('host','Hostname do controlador','',{required:true,placeholder:'dc01.corp.empresa.com.br'})}${inputField('port','Porta LDAPS',636,{type:'number',min:1})}</div>${inputField('base_dn','DN do domínio','',{required:true,placeholder:'DC=corp,DC=empresa,DC=com,DC=br',maxLength:500})}${inputField('bind_dn','Conta para consulta','',{required:true,placeholder:'consulta@corp.empresa.com.br',maxLength:500})}${inputField('password','Senha da conta','',{required:true,type:'password',maxLength:256})}${textareaField('ca_pem','Certificado da CA (PEM, se necessário)')}<p class="section-note">Se a CA já for confiável no sistema, deixe o campo vazio. Use uma conta com os direitos de leitura necessários.</p><button type="submit" class="button primary">${icon('link')} Conectar ao domínio</button></form>`}</section><aside class="panel integration-card"><span class="eyebrow">INTEGRAÇÃO COM LINUX</span><h2>Um painel para seu domínio Samba.</h2><p>Os controladores continuam em Linux. Servidores e estações Windows participam como membros.</p><h3>Disponível nesta integração</h3><ul class="simple-list"><li>Consulta paginada de usuários, grupos e OUs</li><li>Contas de computadores do domínio</li><li>Metadados de políticas existentes</li><li>Validação da cadeia do certificado LDAPS</li></ul><h3>Próxima etapa</h3><ul class="simple-list"><li>Operações reais com direitos delegados</li><li>DNS e SYSVOL</li><li>Publicação de políticas</li><li>Servidores de arquivos e ACLs</li></ul></aside></div>`;
}

async function renderAudit() {
  const data = await api('/api/audit');
  return heading('Histórico de alterações', 'Quem fez, o que mudou e em qual contexto a operação aconteceu.') + notice('Este histórico registra ações no painel e no laboratório. Eventos internos do Samba e tentativas de autenticação do domínio serão integrados em uma etapa posterior.') + `<section class="panel"><div class="table-scroll"><table><thead><tr><th>QUANDO</th><th>RESPONSÁVEL</th><th>OPERAÇÃO</th><th>OBJETO</th><th>CONTEXTO</th><th>ALTERAÇÃO</th></tr></thead><tbody>${data.items.map(row => `<tr><td>${escape(date(row.created_at))}</td><td>${escape(row.actor)}</td><td>${escape(row.operation)}</td><td><span class="row-meta">${escape(row.target)}</span></td><td>${badge(row.mode, row.mode === 'ldaps' ? 'good' : 'neutral')}</td><td><details class="audit-details"><summary>Ver detalhes</summary><pre>${escape(JSON.stringify({antes:JSON.parse(row.before_json),depois:JSON.parse(row.after_json)},null,2))}</pre></details></td></tr>`).join('') || `<tr><td colspan="6">${empty('Histórico vazio','As alterações aparecerão aqui.')}</td></tr>`}</tbody></table></div><div class="table-foot"><span>Últimas ${data.items.length} operações</span><span>Registro local · ainda sem armazenamento externo imutável</span></div></section>`;
}

async function renderRoadmap() {
  const phases = [
    {label:'Disponível · 0.1',status:'good',title:'Fundação da plataforma',description:'Interface e fluxo inicial de criação do domínio Linux.',items:['Login e sessões locais','Cadastros persistidos no laboratório','Planos para Debian, Ubuntu e Enterprise Linux','Instaladores iniciais Debian e Ubuntu','Consulta Samba por LDAPS','Histórico de alterações']},
    {label:'Próxima etapa',status:'warning',title:'Domínio real e operação',description:'Conectar as operações do painel ao controlador e aos membros.',items:['Execução do pacote em VM dedicada','Criação real de usuários, grupos e OUs','Senhas e administração delegada','DNS e acompanhamento dos serviços','Ingresso assistido de Windows e Linux']},
    {label:'Planejado',status:'neutral',title:'Políticas e permissões',description:'Evoluir a administração diária com suporte definido por sistema.',items:['Publicação de GPOs no SYSVOL','Editor ADMX/ADML e políticas Linux','Compartilhamentos e ACLs','Renomeação e tarefas nas estações','Segundo DC, backups e recuperação']},
  ];
  return heading('Etapas do projeto', 'Uma plataforma para criar e administrar domínios em Linux, com evolução visível.') + notice('O projeto está na primeira versão. Os módulos de laboratório funcionam localmente; integração de escrita e implantação em VM ainda precisam ser concluídas. MFA e perfis administrativos também fazem parte da preparação para produção.') + `<div class="feature-grid">${phases.map(phase => `<section class="feature-card">${badge(phase.label,phase.status)}<h3>${escape(phase.title)}</h3><p>${escape(phase.description)}</p><ul>${phase.items.map(item => `<li>${escape(item)}</li>`).join('')}</ul></section>`).join('')}</div>`;
}

function bindPage() {
  const filter = $('#filter');
  if (filter) filter.addEventListener('input', event => {
    const query = event.target.value.toLocaleLowerCase('pt-BR');
    const filtered = items.filter(item => [item.name,item.account,item.email,item.ou,item.os,item.value,item.description].join(' ').toLocaleLowerCase('pt-BR').includes(query));
    $('#record-rows').innerHTML = rows(currentPage,filtered);
    $('#visible-count').textContent = `${filtered.length} de ${items.length} objetos apresentados`;
  });
  const setup = $('#setup-form');
  if (setup) {
    setup.addEventListener('input', () => { $('#plan-result').innerHTML = ''; });
    $('#f-distribution').addEventListener('change', event => {
      $('#distribution-info').innerHTML = distributionInfo(event.target.value);
      $('#plan-result').innerHTML = '';
    });
    setup.addEventListener('submit',async event => {
      event.preventDefault();
      const button = event.target.querySelector('[type=submit]'); button.disabled = true;
      try {
        const submitted = JSON.stringify(setupValue());
        const result = await api('/api/domain/plan',{method:'POST',body:submitted});
        if (!setup.isConnected) return;
        if (submitted !== JSON.stringify(setupValue())) {
          toast('A configuração mudou durante a geração. Gere o plano novamente.');
          return;
        }
        $('#plan-result').innerHTML = planMarkup(result);
        $('#download-package').addEventListener('click',async event => {
          const button = event.currentTarget; button.disabled = true;
          try { const blob = await api('/api/domain/package',{method:'POST',body:JSON.stringify(result.manifest)}); download(blob,`dominio-linux-${result.manifest.netbios.toLowerCase()}-${result.manifest.distribution}.zip`); toast(result.installer_available ? 'Pacote gerado. Consulte as instruções antes de executar na VM.' : 'Plano gerado. O instalador desta distribuição ainda está em integração.'); } catch (failure) { toast(failure.message,true); } finally { button.disabled = false; }
        });
        $('#plan-result').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
      } catch (failure) { toast(failure.message,true); } finally { button.disabled = false; }
    });
    $('#save-domain').addEventListener('click', async event => {
      if (!setup.reportValidity()) return;
      const button = event.currentTarget; button.disabled = true;
      try { await api('/api/domain',{method:'PUT',body:JSON.stringify(setupValue())}); await refreshContext(); toast('Configuração do plano salva. O domínio ainda não foi criado.'); } catch (failure) { toast(failure.message,true); } finally { button.disabled = false; }
    });
  }
  const integration = $('#integration-form');
  if (integration) integration.addEventListener('submit',async event => {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(integration)); body.port = Number(body.port);
    const button = event.target.querySelector('[type=submit]'); button.disabled = true;
    try { await api('/api/integration/connect',{method:'POST',body:JSON.stringify(body)}); integration.reset(); await navigate(); toast('Conectado ao Samba por LDAPS. Consulta de leitura disponível.'); } catch (failure) { toast(failure.message,true); } finally { button.disabled = false; }
  });
  $('#disconnect')?.addEventListener('click',async () => {
    try { await api('/api/integration/disconnect',{method:'POST'}); await navigate(); toast('Desconectado. O laboratório local está disponível.'); } catch (failure) { toast(failure.message,true); }
  });
}

$('#content').addEventListener('click',async event => {
  const button = event.target.closest('[data-action]');
  if (!button || button.disabled) return;
  const action = button.dataset.action;
  const item = items.find(item => item.id === button.dataset.id);
  button.disabled = true;
  try {
    if (action === 'new') await openEditor(currentPage);
    if (action === 'edit' && item) await openEditor(currentPage,item);
    if (action === 'delete' && item && await confirmDelete(item)) { await api(`/api/records/${currentPage}/${encodeURIComponent(item.id)}`,{method:'DELETE'}); toast('Objeto excluído do laboratório.'); await navigate(); }
    if (action === 'export' && item) download(new Blob([JSON.stringify({state:context.mode === 'ldaps' ? 'metadata-only' : 'draft-not-published',policy:item},null,2)],{type:'application/json'}),'politica-dominio-linux.json');
  } catch (failure) { toast(failure.message,true); } finally { button.disabled = false; }
});
$('#logout').addEventListener('click',async () => {
  try { await api('/api/logout',{method:'POST'}); location.replace('/'); } catch (failure) { toast(failure.message,true); }
});
$('#menu-toggle').addEventListener('click',() => $('#sidebar').classList.toggle('open'));
window.addEventListener('hashchange',navigate);
await navigate();
