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
    layout="wide",
)

st.markdown("""
<style>
  .stApp { background-color: #F8F9FA; color: #171717; }
  h1, h2, h3 { color: #1E3A6B; }
  .stButton > button { background-color: #1E3A6B; color: #F8F9FA; border: none; }
  .stButton > button:hover { background-color: #5B9BD5; }
  .stTabs [data-baseweb="tab-highlight"] { background-color: #00B4A6; }
  .stTabs [data-baseweb="tab"] { color: #1E3A6B; }
</style>
""", unsafe_allow_html=True)

st.title("🎵 genrefy")


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

user = sp.me()
st.success(f"Conectado ao Spotify como **{user['display_name']}**")

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
