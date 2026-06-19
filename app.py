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
import os
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from commands.check import run_check
from commands.genres import run_genres
from commands.info import run_info
from commands.reload import run_reload
from spotify_client import (
    create_auth_manager,
    create_spotify_client,
    get_artists_for_tracks,
    get_saved_tracks,
    get_user_playlists,
    is_authenticated,
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
    overflow: hidden !important;
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

    # Fase 2: busca dados dos artistas em lotes de 50
    _bar2 = st.empty()

    def _on_artists_progress(done: int, total: int):
        _bar2.progress(done / total, text=f'Carregando artistas: {done} / {total}')

    try:
        _artists = get_artists_for_tracks(
            sp, st.session_state.library_tracks, on_progress=_on_artists_progress
        )
        st.session_state.library_genres = sorted({g for a in _artists for g in a['genres']})
        st.session_state.library_artists = sorted({a['name'] for a in _artists})
        st.session_state.library_loaded = True
    except Exception as _lib_err:
        st.session_state.pop('library_loaded', None)
        st.error(f'Erro ao carregar artistas: {_lib_err}')
        if st.button('Tentar novamente'):
            st.rerun()
        st.stop()

    _bar2.empty()

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
    for key in ['sp', 'auth_manager', 'playlists', 'auth_error',
                'library_loaded', 'library_genres', 'library_artists', 'library_tracks']:
        st.session_state.pop(key, None)
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

tab_sync, tab_check, tab_info, tab_genres = st.tabs(
    ["Sincronizar", "Artistas", "Buscar", "Exportar"]
)

# --- helpers de UX compartilhados ---
def _confirm_buttons(key_prefix):
    """Retorna (confirmar, cancelar) usando colunas centradas."""
    _, c1, c2, _ = st.columns([3, 1, 1, 3])
    confirmar = c1.button("Confirmar", type="primary", key=f"{key_prefix}_confirmar")
    cancelar  = c2.button("Cancelar",                  key=f"{key_prefix}_cancelar")
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
            if not cfg:
                st.caption("Nenhuma playlist configurada.")
            else:
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
                st.info("Adicione uma playlist para começar.")
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
                        "Excluir",
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
                    st.toast("Configuração salva!")

                if b4.button("Sincronizar ▶", type="primary", key="cfg_sync"):
                    _flush_widgets()
                    save_playlists_to_volume(st.session_state.config_playlists)
                    st.session_state.playlists = list(st.session_state.config_playlists)
                    st.session_state.sync_selection = [st.session_state.config_playlists[i]]
                    st.session_state.reload_pending = True
                    st.rerun()

    else:
        selected = st.session_state.get("sync_selection", [])
        p = selected[0] if selected else {}
        name = _playlist_name(p.get('id', ''), p.get('name', ''))

        st.markdown(f"**Sincronizar:** {name}")
        st.warning("Todas as faixas dessa playlist serão removidas e readicionadas.")

        confirmar, cancelar = _confirm_buttons("reload")

        if cancelar:
            st.session_state.reload_pending = False
            st.rerun()

        if confirmar:
            st.session_state.reload_pending = False
            with st.status("Sincronizando...", expanded=True) as status:
                try:
                    _, summary = run_reload(
                        sp,
                        selected,
                        progress_callback=status.write,
                        cached_tracks=st.session_state.get('library_tracks'),
                    )
                    status.update(label="Sincronização concluída!", state="complete", expanded=False)
                except Exception as exc:
                    status.update(label="Erro durante a sincronização", state="error")
                    st.error(f"Detalhe: {exc}")
                    summary = {}

            if summary:
                st.success("Concluído!")
                for nome, contagem in summary.items():
                    st.markdown(f"**{nome}**: {contagem} faixas")

# ── ARTISTAS ──────────────────────────────────────────────────────────────────
with tab_check:
    st.subheader("Artistas")
    st.write(
        "Verifica quais artistas das suas músicas curtidas não têm mapeamento "
        "em nenhuma playlist configurada."
    )

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
            st.session_state.check_pending = False
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
                    status.update(label="Erro na verificação", state="error")
                    st.error(f"Detalhe: {exc}")

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
    st.subheader("Buscar")
    st.write("Consulta os gêneros de um artista pelo ID ou URL do Spotify.")

    artist_input = st.text_input(
        "Artist ID ou URL do Spotify",
        placeholder="Ex: 3TVXtAsR1Inumwj472S9r4 ou https://open.spotify.com/artist/...",
    )

    if not st.session_state.get("info_pending"):
        if st.button("Buscar Gêneros"):
            if not artist_input.strip():
                st.warning("Informe um Artist ID ou URL do Spotify.")
            else:
                st.session_state.info_pending = True
                st.session_state.info_artist = artist_input.strip()
                st.rerun()
    else:
        artista_id = st.session_state.info_artist
        st.info(f"Vai buscar os gêneros do artista: `{artista_id}`")
        confirmar, cancelar = _confirm_buttons("info")

        if cancelar:
            st.session_state.info_pending = False
            st.rerun()

        if confirmar:
            st.session_state.info_pending = False
            result = None
            with st.status("Buscando artista...", expanded=True) as status:
                try:
                    result = run_info(sp, artista_id)
                    status.update(label=f"Artista encontrado!", state="complete", expanded=False)
                except Exception as exc:
                    status.update(label="Erro ao buscar artista", state="error")
                    st.error(f"Detalhe: {exc}")

            if result:
                st.markdown(f"### {result['name']}")
                if result["genres"]:
                    st.markdown(" · ".join(f"`{g}`" for g in result["genres"]))
                else:
                    st.info("Nenhum gênero encontrado para este artista.")

# ── EXPORTAR ──────────────────────────────────────────────────────────────────
with tab_genres:
    st.subheader("Exportar")
    st.write(
        "Gera um CSV com todos os artistas das suas músicas curtidas e seus gêneros, "
        "ordenados alfabeticamente."
    )

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
            st.session_state.genres_pending = False
            output_path = None
            with st.status("Gerando CSV...", expanded=True) as status:
                try:
                    output_path = run_genres(sp)
                    status.update(label="CSV gerado!", state="complete", expanded=False)
                except Exception as exc:
                    status.update(label="Erro ao gerar CSV", state="error")
                    st.error(f"Detalhe: {exc}")

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

