# genrefy — Distribui musicas curtidas do Spotify em playlists por genero
# Copyright (C) 2026 Armando Netto <armandosln7@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import base64
import json
import logging
import math
import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from commands.check import run_check
from commands.genres import run_genres
from commands.info import run_info
from commands.reload import run_reload, plan_reload
from spotify_client import (
    clear_artist_cache,
    clear_sync_snapshot,
    create_auth_manager,
    create_spotify_client,
    enrich_artists_with_genres,
    extract_artists_from_tracks,
    get_saved_tracks,
    get_user_playlists,
    is_authenticated,
    load_aliases,
    load_artist_cache,
    load_overrides,
    load_sync_snapshot,
    restore_from_snapshot,
    save_aliases,
    save_artist_cache,
    save_overrides,
    save_sync_snapshot,
)

logging.basicConfig(level=logging.INFO)

_ASSETS = Path(__file__).parent / 'assets'

def _img_b64(filename: str) -> str:
    with open(_ASSETS / filename, 'rb') as f:
        return base64.b64encode(f.read()).decode()

_LOGO_B64 = _img_b64('logo-2.png')

st.set_page_config(
    page_title="Genrefy",
    page_icon=Image.open(_ASSETS / 'favicon.png'),
    layout="centered",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/icon?family=Material+Icons');

  /* Icone de playlist nos expanders via Material Icons */
  [data-testid="stExpander"] summary p::before {
    font-family: 'Material Icons';
    content: 'queue_music';
    margin-right: 6px;
    vertical-align: -4px;
    font-size: 1.1rem;
    color: #1DB954;
  }

  /* Botoes: pill shape verde Spotify */
  .stButton > button {
    background-color: #1DB954;
    color: #000000;
    border: none;
    border-radius: 500px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 10px 28px;
    white-space: nowrap;
    transition: background-color 0.15s ease, transform 0.1s ease;
  }
  .stButton > button:hover {
    background-color: #1ed760;
    transform: scale(1.03);
    border: none;
  }
  .stButton > button:active { transform: scale(0.98); }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    border-bottom: 1px solid #282828;
    justify-content: center;
    gap: 8px;
  }
  .stTabs [data-baseweb="tab-highlight"] { background-color: #1DB954; }
  .stTabs [data-baseweb="tab"] {
    color: #B3B3B3;
    font-weight: 700;
    letter-spacing: 1px;
    font-size: 0.85rem;
    text-transform: uppercase;
    padding: 12px 28px;
  }
  .stTabs [aria-selected="true"] { color: #FFFFFF; }

  /* Inputs */
  .stTextInput input {
    background-color: #282828 !important;
    border: 1px solid #404040 !important;
    color: #FFFFFF !important;
    border-radius: 4px !important;
  }
  .stTextInput input:focus { border-color: #FFFFFF !important; }

  /* Link button (login) */
  .stLinkButton a {
    background-color: #1DB954 !important;
    color: #000000 !important;
    border-radius: 500px !important;
    font-weight: 700 !important;
    padding: 12px 32px !important;
    white-space: nowrap !important;
  }

  /* Container centralizado -- sem scroll na pagina, somente as tabs scrollam */
  html, body { overflow: hidden !important; height: 100% !important; }
  [data-testid="stAppViewContainer"],
  section[data-testid="stMain"] {
    overflow: hidden !important;
    height: 100vh !important;
  }
  .block-container {
    padding-top: 2rem !important;
    padding-bottom: 0 !important;
    max-width: 860px !important;
    height: calc(100vh - 60px) !important;
    overflow-y: auto !important;
    display: flex !important;
    flex-direction: column !important;
  }
  /* Somente o conteudo interno da aba ativa faz scroll */
  [data-testid="stTabsContent"] {
    overflow-y: auto !important;
    flex: 1 !important;
    padding-bottom: 2rem;
    scrollbar-width: thin;
    scrollbar-color: #404040 transparent;
  }
  [data-testid="stTabsContent"]::-webkit-scrollbar { width: 4px; }
  [data-testid="stTabsContent"]::-webkit-scrollbar-track { background: transparent; }
  [data-testid="stTabsContent"]::-webkit-scrollbar-thumb {
    background: #404040;
    border-radius: 4px;
  }

  /* Icone de logout no banner */
  .logout-btn:hover {
    color: #FFFFFF !important;
    background: rgba(255,255,255,0.12) !important;
  }

  /* Centraliza conteudo das tabs */
  .stTabs h2, .stTabs h3 { text-align: center; }
  .stTabs [data-testid="stMarkdownContainer"] p { text-align: center; }
  .stTabs .stButton > button { display: block; margin: 0 auto; }
  .stTabs [data-testid="stTabsContent"] { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

components.html("""
<script>
  (function() {
    const TITLE = "Genrefy";
    function lock() {
      if (parent.document.title !== TITLE) parent.document.title = TITLE;
    }
    lock();
    new MutationObserver(lock).observe(
      parent.document.querySelector("head"),
      { subtree: true, childList: true, characterData: true }
    );
  })();
</script>
""", height=0)

st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:center;padding:8px 0 24px 0">
  <img src="data:image/png;base64,{_LOGO_B64}" style="height:64px;object-fit:contain">
</div>
""", unsafe_allow_html=True)


USER_CONFIG_PATH = Path('/app/user_config/config.json')


def load_playlists() -> list[dict]:
    if USER_CONFIG_PATH.exists():
        with open(USER_CONFIG_PATH, encoding='utf-8') as f:
            return json.load(f)['playlists']
    config_path = os.path.join(os.path.dirname(__file__), "config", "production.json")
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)['spotify']['playlists']


def save_playlists_to_volume(playlists: list[dict]) -> None:
    USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump({'playlists': playlists}, f, ensure_ascii=False, indent=2)


def _build_artist_map(user_id: str) -> dict | None:
    """Monta artist_map do cache com overrides manuais aplicados por cima."""
    cached = load_artist_cache(user_id)
    if not cached:
        return None
    artist_map = {a['id']: a.get('genres', []) for a in cached}
    artist_map.update(load_overrides(user_id))
    return artist_map or None


if "auth_manager" not in st.session_state:
    try:
        st.session_state.auth_manager = create_auth_manager()
        st.session_state.playlists = load_playlists()
        st.session_state.auth_error = None
    except Exception as e:
        st.session_state.auth_manager = None
        st.session_state.playlists = []
        st.session_state.auth_error = str(e)

if st.session_state.auth_error:
    st.error(
        "Falha ao inicializar. Verifique se o arquivo .env existe com "
        "SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET e SPOTIFY_REDIRECT_URI.\n\n"
        f"Detalhe: {st.session_state.auth_error}"
    )
    if st.button("Tentar novamente", key="retry_auth"):
        for _k in ("auth_manager", "auth_error", "playlists"):
            st.session_state.pop(_k, None)
        st.rerun()
    st.stop()

auth_manager = st.session_state.auth_manager

# Captura o código OAuth quando o Spotify redireciona de volta para o app
code = st.query_params.get("code")
if code and not is_authenticated(auth_manager):
    try:
        auth_manager.get_access_token(code, check_cache=False)
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Falha ao completar autenticação: {e}")
        if st.button("Tentar novamente", key="retry_oauth"):
            st.query_params.clear()
            st.rerun()
        st.stop()

# Se não autenticado, mostra o botão de login
if not is_authenticated(auth_manager):
    st.info("Conecte sua conta do Spotify para começar.")
    auth_url = auth_manager.get_authorize_url()
    st.link_button("Conectar ao Spotify", auth_url)
    st.stop()

# Cliente autenticado
if "sp" not in st.session_state:
    st.session_state.sp = create_spotify_client(auth_manager)

sp = st.session_state.sp
playlists = st.session_state.playlists

if not st.session_state.get('library_loaded'):
    # Fase 1: baixa as musicas curtidas com barra de progresso
    if not st.session_state.get('library_tracks'):
        _bar = st.empty()

        def _on_tracks_progress(done: int, total: int):
            _bar.progress(done / total, text=f'Baixando músicas curtidas: {done} / {total}')

        try:
            _tracks = get_saved_tracks(sp, on_progress=_on_tracks_progress)
            st.session_state.library_tracks = _tracks
        except Exception as _err:
            st.error(f'Erro ao baixar músicas: {_err}')
            if st.button('Tentar novamente'):
                st.rerun()
            st.stop()

        _bar.empty()

    # Fase 2: busca dados dos artistas — tenta cache antes de chamar a API
    with st.spinner("Carregando dados dos artistas..."):
        _user_id = sp.me().get('id', 'unknown')
        st.session_state.library_user_id = _user_id
        _cached = load_artist_cache(_user_id)

        if _cached is not None:
            _artists = _cached
        else:
            _tracks_in_state = st.session_state.library_tracks or []
            _artists = extract_artists_from_tracks(_tracks_in_state)
            if _artists:
                save_artist_cache(_user_id, _artists)

    st.session_state.library_genres = sorted({g for a in _artists for g in a.get('genres', [])})
    st.session_state.library_artists = sorted({a['name'] for a in _artists})
    st.session_state.library_loaded = True
    st.session_state.library_genres_ok = bool(st.session_state.library_genres)
    if not st.session_state.library_genres_ok:
        st.session_state.auto_enrich = True

if 'spotify_playlists' not in st.session_state:
    with st.spinner("Carregando suas playlists do Spotify..."):
        st.session_state.spotify_playlists = get_user_playlists(sp)

spotify_playlists = st.session_state.spotify_playlists
_playlist_name_map = {p['id']: p['name'] for p in spotify_playlists}

# Busca nomes das playlists do config que nao aparecem na lista do usuario
_missing_ids = [p['id'] for p in playlists if p.get('id') and p['id'] not in _playlist_name_map]
for _pid in _missing_ids:
    try:
        _playlist_name_map[_pid] = sp.playlist(_pid, fields='name')['name']
    except Exception:
        pass

def _playlist_name(pid: str, fallback: str = '') -> str:
    return _playlist_name_map.get(pid, fallback)

def do_logout():
    cache_path = os.getenv('SPOTIFY_TOKEN_CACHE', '.spotify_cache')
    if os.path.exists(cache_path):
        os.remove(cache_path)
    st.session_state.clear()
    st.rerun()

if st.query_params.get("action") == "logout":
    st.query_params.clear()
    do_logout()

user = sp.me()
avatar = user.get('images', [{}])[0].get('url', '') if user.get('images') else ''
avatar_html = f'<img src="{avatar}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;flex-shrink:0">' if avatar else ''

logout_icon = """<svg xmlns="http://www.w3.org/2000/svg" height="20" width="20" viewBox="0 0 24 24" fill="currentColor">
  <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/>
</svg>"""

st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            background:#1a3a24;border:1px solid #1DB954;border-radius:8px;
            padding:10px 16px;margin-bottom:16px">
  <div style="display:flex;align-items:center;gap:10px">
    {avatar_html}
    <span style="color:#FFFFFF;font-size:0.95rem">
      Conectado ao Spotify como <strong>{user['display_name']}</strong>
    </span>
  </div>
  <a href="?action=logout" title="Sair" class="logout-btn"
     style="color:#B3B3B3;text-decoration:none;display:flex;align-items:center;
            padding:7px;border-radius:50%;transition:color 0.15s,background 0.15s;
            background:rgba(255,255,255,0.05)">
    {logout_icon}
  </a>
</div>
""", unsafe_allow_html=True)

_genre_status_ph = st.empty()

if not st.session_state.get("library_genres_ok", True) and not st.session_state.get("auto_enrich"):
    _c1, _c2 = st.columns([5, 1])
    _c1.warning("Generos nao encontrados. Clique em Recarregar para tentar novamente.")
    if _c2.button("Recarregar", key="retry_genres"):
        clear_artist_cache(st.session_state.get("library_user_id", "unknown"))
        for _k in ("library_loaded", "library_genres_ok", "library_genres", "library_artists", "library_tracks"):
            st.session_state.pop(_k, None)
        st.rerun()

tab_sync, tab_check, tab_info, tab_genres = st.tabs(
    ["Sincronizar", "Artistas", "Buscar", "Exportar"]
)

# --- helpers de UX compartilhados ---
def _confirm_buttons(key_prefix):
    """Retorna (confirmar, cancelar) usando colunas centradas."""
    _, c1, c2, _ = st.columns([2, 3, 3, 2])
    confirmar = c1.button("Confirmar", type="primary", key=f"{key_prefix}_confirmar", use_container_width=True)
    cancelar  = c2.button("Cancelar",                  key=f"{key_prefix}_cancelar",  use_container_width=True)
    return confirmar, cancelar

# ── SINCRONIZAR ───────────────────────────────────────────────────────────────
with tab_sync:
    if 'config_playlists' not in st.session_state:
        st.session_state.config_playlists = [
            {
                'id': p.get('id', ''),
                'name': p.get('name', ''),
                'genres': list(p.get('genres', [])),
                'ngenres': list(p.get('ngenres', [])),
                'aoverride': list(p.get('aoverride', [])),
            }
            for p in load_playlists()
        ]

    playlist_options = _playlist_name_map

    def _flush_widgets():
        for i in range(len(st.session_state.config_playlists)):
            pid = st.session_state.get(f"cfg_{i}_id", st.session_state.config_playlists[i].get('id', ''))
            st.session_state.config_playlists[i]['id'] = pid
            st.session_state.config_playlists[i]['name'] = playlist_options.get(pid, pid)
            for field in ('genres', 'ngenres', 'aoverride'):
                val = st.session_state.get(f"cfg_{i}_{field}", st.session_state.config_playlists[i].get(field, []))
                if isinstance(val, list):
                    st.session_state.config_playlists[i][field] = val
                else:
                    st.session_state.config_playlists[i][field] = [v.strip() for v in val.split('\n') if v.strip()]

    if not st.session_state.get("reload_pending"):
        cfg = st.session_state.config_playlists
        opts = list(playlist_options.keys())

        col_list, col_cfg = st.columns([2, 5])

        with col_list:
            if cfg:
                sel = st.session_state.get("sel_playlist", 0)
                sel = min(sel, len(cfg) - 1)

                if 'playlist_covers' not in st.session_state:
                    st.session_state.playlist_covers = {}
                for j, p in enumerate(cfg):
                    pid = st.session_state.get(f"cfg_{j}_id") or p.get('id', '')
                    if pid and pid not in st.session_state.playlist_covers:
                        try:
                            imgs = sp.playlist(pid, fields='images').get('images', [])
                            st.session_state.playlist_covers[pid] = imgs[0]['url'] if imgs else ''
                        except Exception:
                            st.session_state.playlist_covers[pid] = ''

                for idx, p in enumerate(cfg):
                    pid = st.session_state.get(f"cfg_{idx}_id") or p.get('id', '')
                    name = _playlist_name(pid, '') or f"Playlist {idx + 1}"
                    cover = st.session_state.playlist_covers.get(pid, '')
                    is_selected = (idx == sel)
                    c_img, c_name = st.columns([1, 3])
                    with c_img:
                        if cover:
                            st.image(cover, width=40)
                    with c_name:
                        label = f"▶ {name}" if is_selected else name
                        if st.button(label, key=f"sel_pl_{idx}", use_container_width=True):
                            _flush_widgets()
                            st.session_state.sel_playlist = idx
                            st.rerun()

            if st.button("+ Adicionar", key="cfg_add"):
                _flush_widgets()
                st.session_state.config_playlists.append({
                    'id': '', 'name': '', 'genres': [], 'ngenres': [], 'aoverride': [],
                })
                st.session_state.sel_playlist = len(st.session_state.config_playlists) - 1
                st.rerun()

        with col_cfg:
            if not cfg:
                st.info("Nenhuma playlist ainda. Clique em **+ Adicionar** para criar a primeira.")
            else:
                i = st.session_state.get("sel_playlist", 0)
                i = min(i, len(cfg) - 1)
                playlist = cfg[i]
                current_id = st.session_state.get(f"cfg_{i}_id") or playlist.get('id', '')
                found = current_id in playlist_options
                idx = opts.index(current_id) if found else None

                st.selectbox(
                    "Playlist do Spotify",
                    options=opts,
                    format_func=lambda x, po=playlist_options: po.get(x, x),
                    index=idx,
                    placeholder="Selecione a playlist...",
                    key=f"cfg_{i}_id",
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.multiselect(
                        "Gêneros",
                        options=st.session_state.library_genres,
                        default=playlist.get('genres', []),
                        key=f"cfg_{i}_genres",
                        help="Gêneros que entram nesta playlist.",
                    )
                with col2:
                    st.multiselect(
                        "Excluir gêneros",
                        options=st.session_state.library_genres,
                        default=playlist.get('ngenres', []),
                        key=f"cfg_{i}_ngenres",
                        help="Gêneros excluídos com precedência absoluta.",
                    )
                with col3:
                    st.multiselect(
                        "Forçar artistas",
                        options=st.session_state.library_artists,
                        default=playlist.get('aoverride', []),
                        key=f"cfg_{i}_aoverride",
                        help="Artista entra independente do gênero.",
                    )

                b1, b2, b3, b4 = st.columns(4)

                if b1.button("Remover", key=f"cfg_remove_{i}"):
                    _flush_widgets()
                    st.session_state.config_playlists.pop(i)
                    for field in ('id', 'genres', 'ngenres', 'aoverride'):
                        st.session_state.pop(f"cfg_{i}_{field}", None)
                    st.rerun()

                if b2.button("Descartar", key="cfg_discard"):
                    for k in list(st.session_state.keys()):
                        if k.startswith('cfg_'):
                            del st.session_state[k]
                    st.session_state.pop('config_playlists', None)
                    st.rerun()

                if b3.button("Salvar", key="cfg_save"):
                    _flush_widgets()
                    save_playlists_to_volume(st.session_state.config_playlists)
                    st.session_state.playlists = list(st.session_state.config_playlists)
                    st.session_state['cfg_saved'] = True
                    st.toast("Configuração salva!")

                if st.session_state.pop('cfg_saved', False):
                    st.success("Configuração salva!")

                if b4.button("Sincronizar ▶", type="primary", key="cfg_sync"):
                    _flush_widgets()
                    save_playlists_to_volume(st.session_state.config_playlists)
                    st.session_state.playlists = list(st.session_state.config_playlists)
                    st.session_state.sync_selection = [st.session_state.config_playlists[i]]
                    st.session_state.reload_pending = True
                    st.rerun()

                if len(cfg) > 1:
                    _, _b_all, _ = st.columns([1, 4, 1])
                    if _b_all.button("Sincronizar todas ▶", key="cfg_sync_all", use_container_width=True):
                        _flush_widgets()
                        save_playlists_to_volume(st.session_state.config_playlists)
                        st.session_state.playlists = list(st.session_state.config_playlists)
                        st.session_state.sync_selection = list(st.session_state.config_playlists)
                        st.session_state.reload_pending = True
                        st.rerun()

        # Mapeamento de generos (aliases / sinonimos)
        with st.expander("Mapeamento de generos (sinonimos)", expanded=False):
            st.caption(
                "Quando uma playlist inclui o genero A e um artista tem o genero B, "
                "voce pode dizer que B e sinonimo de A. "
                "Exemplo: 'hip hop' como sinonimo de 'rap'."
            )
            _uid_al = st.session_state.get('library_user_id', 'unknown')
            _aliases_current = load_aliases(_uid_al)
            _alias_rows = [
                {"Genero da playlist": k, "Sinonimos (virgula)": ", ".join(v)}
                for k, v in _aliases_current.items()
            ]
            _alias_df = pd.DataFrame(
                _alias_rows if _alias_rows else [{"Genero da playlist": "", "Sinonimos (virgula)": ""}]
            )
            _alias_edited = st.data_editor(
                _alias_df,
                num_rows="dynamic",
                use_container_width=True,
                key="aliases_editor",
            )
            if st.button("Salvar mapeamento", key="btn_save_aliases"):
                _new_aliases = {}
                for _, _row in _alias_edited.iterrows():
                    _genre = str(_row["Genero da playlist"]).strip()
                    _syns = [s.strip() for s in str(_row["Sinonimos (virgula)"]).split(",") if s.strip()]
                    if _genre and _syns:
                        _new_aliases[_genre] = _syns
                save_aliases(_uid_al, _new_aliases)
                st.toast("Mapeamento de generos salvo!")

        # Undo: mostra botao se houver snapshot de sincronizacao anterior
        _uid_undo = st.session_state.get('library_user_id', 'unknown')
        _snapshot = load_sync_snapshot(_uid_undo)
        if _snapshot:
            _age_min = int((time.time() - _snapshot.get('timestamp', 0)) / 60)
            _age_txt = f" (ha {_age_min} min)" if _age_min > 0 else ""
            st.divider()
            if not st.session_state.get('undo_pending'):
                if st.button(f"Desfazer ultima sincronizacao{_age_txt}", key="undo_btn"):
                    st.session_state.undo_pending = True
                    st.rerun()
            else:
                st.warning(
                    "Vai restaurar cada playlist ao estado antes da ultima sincronizacao. "
                    "Essa operacao nao pode ser desfeita."
                )
                confirmar_undo, cancelar_undo = _confirm_buttons("undo")
                if cancelar_undo:
                    st.session_state.undo_pending = False
                    st.rerun()
                if confirmar_undo:
                    st.session_state.undo_pending = False
                    with st.status("Desfazendo sincronizacao...", expanded=True) as _undo_status:
                        try:
                            restore_from_snapshot(sp, _snapshot, progress_callback=_undo_status.write)
                            clear_sync_snapshot(_uid_undo)
                            _undo_status.update(label="Playlists restauradas!", state="complete", expanded=False)
                            st.success("Feito. Playlists voltaram ao estado anterior.")
                        except Exception as _exc:
                            logging.exception("Erro ao desfazer sincronizacao")
                            _undo_status.update(label="Erro ao restaurar", state="error")
                            st.error(f"Detalhe: {_exc}")

    else:
        selected = st.session_state.get("sync_selection", [])

        # Calcula o plano uma vez e armazena no session_state para nao recalcular a cada rerun
        if "sync_plan" not in st.session_state:
            _uid_plan = st.session_state.get('library_user_id', 'unknown')
            with st.spinner("Calculando preview..."):
                try:
                    st.session_state.sync_plan = plan_reload(
                        sp,
                        selected,
                        cached_tracks=st.session_state.get('library_tracks'),
                        artist_map=_build_artist_map(_uid_plan),
                        aliases=load_aliases(_uid_plan),
                    )
                except Exception as _exc:
                    st.error(f"Erro ao calcular preview: {_exc}")
                    if st.button("Cancelar", key="cancel_plan_err"):
                        st.session_state.reload_pending = False
                        st.rerun()
                    st.stop()

        sync_plan = st.session_state.sync_plan

        st.markdown("**Preview da sincronizacao:**")
        _df_rows = [
            {
                "Playlist": _n,
                "+Adicionadas": len(_p['add']),
                "-Removidas": len(_p['remove']),
                "=Mantidas": _p['keep'],
                "Total": _p['keep'] + len(_p['add']),
            }
            for _n, _p in sync_plan.items()
        ]
        st.dataframe(pd.DataFrame(_df_rows), use_container_width=True, hide_index=True)

        confirmar, cancelar = _confirm_buttons("reload")

        if cancelar:
            st.session_state.reload_pending = False
            st.session_state.pop('sync_plan', None)
            st.rerun()

        if confirmar:
            st.session_state.reload_pending = False
            _plan = st.session_state.pop('sync_plan', None)

            # Salva snapshot antes de modificar qualquer playlist
            _uid = st.session_state.get('library_user_id', 'unknown')
            if _plan:
                save_sync_snapshot(_uid, {_p['pid']: _p['current'] for _p in _plan.values()})

            with st.status("Sincronizando...", expanded=True) as status:
                try:
                    _, summary = run_reload(
                        sp,
                        selected,
                        progress_callback=status.write,
                        cached_tracks=st.session_state.get('library_tracks'),
                        artist_map=_build_artist_map(_uid),
                        plan=_plan,
                        aliases=load_aliases(_uid),
                    )
                    status.update(label="Sincronizacao concluida!", state="complete", expanded=False)
                except Exception as exc:
                    logging.exception("Erro durante a sincronizacao")
                    status.update(label="Erro durante a sincronizacao", state="error")
                    status.write(f"Algo deu errado ao sincronizar. Detalhe: {exc}")
                    summary = {}

            if summary:
                st.success("Concluido!")
                for nome, contagem in summary.items():
                    st.markdown(f"**{nome}**: {contagem} faixas")

# ── ARTISTAS ──────────────────────────────────────────────────────────────────
with tab_check:
    st.subheader("Artistas")
    st.write(
        "Verifica quais artistas das suas músicas curtidas não têm mapeamento "
        "em nenhuma playlist configurada."
    )

    if st.session_state.get("check_error"):
        st.error(f"Erro na última verificação: {st.session_state.check_error}")
        if st.button("Tentar novamente", key="retry_check"):
            st.session_state.pop("check_error", None)
            st.session_state.check_pending = True
            st.rerun()

    if not st.session_state.get("check_pending"):
        if st.button("Verificar Artistas"):
            st.session_state.check_pending = True
            st.rerun()
    else:
        st.info(
            "Vai buscar todas as suas músicas curtidas e cruzar os gêneros de cada artista "
            "com as playlists configuradas. Pode demorar alguns minutos."
        )
        confirmar, cancelar = _confirm_buttons("check")

        if cancelar:
            st.session_state.check_pending = False
            st.rerun()

        if confirmar:
            missing = None
            with st.status("Verificando artistas...", expanded=True) as status:
                try:
                    missing = run_check(
                        sp,
                        playlists,
                        cached_tracks=st.session_state.get('library_tracks'),
                    )
                    status.update(label="Verificação concluída!", state="complete", expanded=False)
                except Exception as exc:
                    logging.exception("Erro na verificacao de artistas")
                    status.update(label="Erro na verificação", state="error")
                    st.session_state.check_error = str(exc)
                finally:
                    st.session_state.check_pending = False

            if missing is not None:
                if not missing:
                    st.success("Todos os artistas têm gênero mapeado em pelo menos uma playlist.")
                else:
                    st.warning(f"{len(missing)} artista(s) sem mapeamento encontrado(s).")
                    df = pd.DataFrame([
                        {"": a.get("image", ""), "Nome": a["name"], "Gêneros": ", ".join(a["genres"])}
                        for a in missing
                    ])
                    st.dataframe(
                        df,
                        column_config={"": st.column_config.ImageColumn("", width="small")},
                        use_container_width=True,
                    )

# ── BUSCAR ────────────────────────────────────────────────────────────────────
with tab_info:
    st.write("Consulta os generos de um artista pelo ID ou URL do Spotify.")

    if st.session_state.get("buscar_error"):
        st.warning(st.session_state.buscar_error)
    elif st.session_state.get("buscar_result"):
        _r = st.session_state.buscar_result
        st.markdown(f"### {_r['name']}")
        if _r["genres"]:
            st.markdown(" · ".join(f"`{g}`" for g in _r["genres"]))
        else:
            st.warning("Nenhum genero encontrado para este artista.")
        st.caption(f"Campos da API: {_r.get('_raw_keys', [])}")

        _uid_ov = st.session_state.get('library_user_id', 'unknown')
        _overrides_all = load_overrides(_uid_ov)
        _artist_id_ov = _r.get('id', '')
        _active_override = _overrides_all.get(_artist_id_ov)

        with st.expander("Definir override de generos", expanded=_active_override is not None):
            if _active_override is not None:
                st.caption("Override ativo para este artista.")
            _ov_input = st.text_input(
                "Generos (separados por virgula)",
                value=", ".join(_active_override if _active_override is not None else _r.get("genres", [])),
                key="buscar_override_input",
            )
            _col_save, _col_del = st.columns(2)
            if _col_save.button("Salvar override", key="btn_save_override", use_container_width=True):
                _new_genres = [g.strip() for g in _ov_input.split(",") if g.strip()]
                _overrides_all[_artist_id_ov] = _new_genres
                save_overrides(_uid_ov, _overrides_all)
                st.toast(f"Override salvo para {_r['name']}.")
            if _active_override is not None and _col_del.button("Remover override", key="btn_del_override", use_container_width=True):
                _overrides_all.pop(_artist_id_ov, None)
                save_overrides(_uid_ov, _overrides_all)
                st.toast("Override removido.")
                st.rerun()

    artist_input = st.text_input(
        "Artist ID ou URL do Spotify",
        placeholder="Ex: 3TVXtAsR1Inumwj472S9r4 ou https://open.spotify.com/artist/...",
        key="buscar_input",
    )

    if st.button("Buscar Generos"):
        if not artist_input.strip():
            st.session_state.buscar_result = None
            st.session_state.buscar_error = "Informe um Artist ID ou URL do Spotify."
            st.rerun()
        else:
            with st.spinner("Buscando..."):
                try:
                    _r = run_info(sp, artist_input.strip())
                    st.session_state.buscar_result = _r
                    st.session_state.buscar_error = None
                except Exception as exc:
                    st.session_state.buscar_result = None
                    st.session_state.buscar_error = str(exc)
            st.rerun()

# ── EXPORTAR ──────────────────────────────────────────────────────────────────
with tab_genres:
    st.subheader("Exportar")
    st.write(
        "Gera um CSV com todos os artistas das suas músicas curtidas e seus gêneros, "
        "ordenados alfabeticamente."
    )

    if st.session_state.get("genres_error"):
        st.error(f"Erro na última exportação: {st.session_state.genres_error}")
        if st.button("Tentar novamente", key="retry_genres"):
            st.session_state.pop("genres_error", None)
            st.session_state.genres_pending = True
            st.rerun()

    if not st.session_state.get("genres_pending"):
        if st.button("Gerar CSV"):
            st.session_state.genres_pending = True
            st.rerun()
    else:
        st.info(
            "Vai buscar todas as suas músicas curtidas, identificar os gêneros de cada artista "
            "e gerar um CSV para download. Pode demorar alguns minutos."
        )
        confirmar, cancelar = _confirm_buttons("genres")

        if cancelar:
            st.session_state.genres_pending = False
            st.rerun()

        if confirmar:
            output_path = None
            with st.status("Gerando CSV...", expanded=True) as status:
                try:
                    output_path = run_genres(sp)
                    status.update(label="CSV gerado!", state="complete", expanded=False)
                except Exception as exc:
                    logging.exception("Erro ao gerar CSV")
                    status.update(label="Erro ao gerar CSV", state="error")
                    st.session_state.genres_error = str(exc)
                finally:
                    st.session_state.genres_pending = False

            if output_path:
                with open(output_path, encoding="utf-8") as f:
                    csv_bytes = f.read().encode("utf-8")
                st.success("CSV gerado com sucesso!")
                st.download_button(
                    label="Baixar CSV",
                    data=csv_bytes,
                    file_name="artists_genres.csv",
                    mime="text/csv",
                )

# ── ENRIQUECIMENTO AUTOMATICO DE GENEROS ──────────────────────────────────────
if st.session_state.get("auto_enrich"):
    st.session_state.pop("auto_enrich")
    _uid = st.session_state.get("library_user_id", "unknown")
    _raw = load_artist_cache(_uid) or []
    if _raw:
        with _genre_status_ph.container():
            _mb_bar = st.progress(0, text="Iniciando busca de generos via MusicBrainz...")

        _mb_start = time.time()

        def _on_auto_enrich(done: int, total: int):
            elapsed = time.time() - _mb_start
            if done > 0:
                eta_s = int((elapsed / done) * (total - done))
                eta_txt = f"~{eta_s // 60} min" if eta_s >= 60 else f"~{eta_s}s"
            else:
                eta_txt = "..."
            _mb_bar.progress(
                done / total,
                text=f"MusicBrainz: {done}/{total} artistas · {eta_txt} restantes"
            )

        _enriched = enrich_artists_with_genres(_raw, on_progress=_on_auto_enrich)
        _mb_bar.progress(1.0, text=f"Generos encontrados para {len(_enriched)} artistas.")
        save_artist_cache(_uid, _enriched)
        st.session_state.library_genres = sorted({g for a in _enriched for g in a.get("genres", [])})
        st.session_state.library_artists = sorted({a["name"] for a in _enriched})
        st.session_state.library_genres_ok = bool(st.session_state.library_genres)
        st.rerun()
