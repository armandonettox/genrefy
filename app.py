import json
import logging
import os

import streamlit as st

from commands.check import run_check
from commands.genres import run_genres
from commands.info import run_info
from commands.reload import run_reload
from spotify_client import create_auth_manager, create_spotify_client, is_authenticated

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="genrefy",
    page_icon="🎵",
    layout="centered",
)

st.markdown("""
<style>
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
  .stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid #282828; gap: 4px; }
  .stTabs [data-baseweb="tab-highlight"] { background-color: #1DB954; }
  .stTabs [data-baseweb="tab"] { color: #B3B3B3; font-weight: 700; letter-spacing: 0.5px; }
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

  /* Container centralizado com padding generoso */
  .block-container {
    padding-top: 3rem !important;
    padding-bottom: 3rem !important;
    max-width: 860px !important;
  }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="display:flex;align-items:center;justify-content:center;gap:12px;padding:8px 0 24px 0">
  <svg xmlns="http://www.w3.org/2000/svg" width="44" height="44" viewBox="0 0 24 24" fill="#1DB954">
    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
  </svg>
  <span style="font-size:2.2rem;font-weight:900;color:#FFFFFF;letter-spacing:-1px">genrefy</span>
</div>
""", unsafe_allow_html=True)


def load_playlists() -> list[dict]:
    config_path = os.path.join(os.path.dirname(__file__), "config", "production.json")
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    return data["spotify"]["playlists"]


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

def do_logout():
    cache_path = os.getenv('SPOTIFY_TOKEN_CACHE', '.spotify_cache')
    if os.path.exists(cache_path):
        os.remove(cache_path)
    for key in ['sp', 'auth_manager', 'playlists', 'auth_error']:
        st.session_state.pop(key, None)
    st.rerun()


user = sp.me()
avatar = user.get('images', [{}])[0].get('url', '') if user.get('images') else ''
avatar_html = f'<img src="{avatar}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;flex-shrink:0">' if avatar else ''

st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            background:#1a3a24;border:1px solid #1DB954;border-radius:8px;
            padding:10px 16px;margin-bottom:8px">
  <div style="display:flex;align-items:center;gap:10px">
    {avatar_html}
    <span style="color:#FFFFFF;font-size:0.95rem">
      Conectado ao Spotify como <strong>{user['display_name']}</strong>
    </span>
  </div>
</div>
""", unsafe_allow_html=True)

if st.button("Sair", key="logout"):
    do_logout()

tab_reload, tab_check, tab_info, tab_genres = st.tabs(
    ["Reload", "Check", "Info", "Genres"]
)

with tab_reload:
    st.subheader("Reload")
    st.write(
        "Busca todas as músicas curtidas, decora com os gêneros dos artistas "
        "e repopula cada playlist configurada de acordo com os filtros de gênero."
    )

    if st.button("Executar Reload"):
        log_area = st.empty()
        log_lines: list[str] = []

        def on_progress(msg: str) -> None:
            log_lines.append(msg)
            log_area.text("\n".join(log_lines))

        with st.spinner("Executando reload..."):
            try:
                run_reload(sp, playlists, progress_callback=on_progress)
                st.success("Reload concluído com sucesso.")
            except Exception as exc:
                st.error(f"Erro durante o reload: {exc}")

with tab_check:
    st.subheader("Check")
    st.write("Verifica quais artistas das suas músicas curtidas não têm mapeamento em nenhuma playlist.")

    if st.button("Verificar Artistas Sem Mapeamento"):
        with st.spinner("Verificando..."):
            try:
                missing = run_check(sp, playlists)
                if not missing:
                    st.success("Todos os artistas têm gênero mapeado em pelo menos uma playlist.")
                else:
                    st.warning(f"{len(missing)} artista(s) sem mapeamento encontrado(s).")
                    import pandas as pd
                    df = pd.DataFrame([
                        {"Nome": a["name"], "Gêneros": ", ".join(a["genres"])}
                        for a in missing
                    ])
                    st.dataframe(df, use_container_width=True)
            except Exception as exc:
                st.error(f"Erro ao verificar artistas: {exc}")

with tab_info:
    st.subheader("Info")
    st.write("Consulta os gêneros de um artista pelo ID ou URL do Spotify.")

    artist_input = st.text_input(
        "Artist ID ou URL do Spotify",
        placeholder="Ex: 3TVXtAsR1Inumwj472S9r4 ou https://open.spotify.com/artist/...",
    )

    if st.button("Buscar Gêneros"):
        if not artist_input.strip():
            st.warning("Informe um Artist ID ou URL do Spotify.")
        else:
            with st.spinner("Buscando..."):
                try:
                    result = run_info(sp, artist_input.strip())
                    st.write(f"**Artista:** {result['name']}")
                    if result["genres"]:
                        st.write("**Gêneros:**")
                        for genre in result["genres"]:
                            st.write(f"- {genre}")
                    else:
                        st.info("Nenhum gênero encontrado para este artista.")
                except Exception as exc:
                    st.error(f"Erro ao buscar artista: {exc}")

with tab_genres:
    st.subheader("Genres")
    st.write(
        "Gera um CSV com todos os artistas das suas músicas curtidas e seus gêneros, "
        "ordenados alfabeticamente."
    )

    if st.button("Gerar CSV"):
        with st.spinner("Gerando CSV..."):
            try:
                output_path = run_genres(sp)
                with open(output_path, encoding="utf-8") as f:
                    csv_bytes = f.read().encode("utf-8")
                st.success(f"CSV gerado: {output_path}")
                st.download_button(
                    label="Baixar CSV",
                    data=csv_bytes,
                    file_name="output.csv",
                    mime="text/csv",
                )
            except Exception as exc:
                st.error(f"Erro ao gerar CSV: {exc}")
